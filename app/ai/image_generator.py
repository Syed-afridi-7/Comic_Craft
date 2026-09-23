"""Comic panel artwork synthesis and parallel generation coordinator."""

import asyncio
import io
import logging
import secrets
import textwrap
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image, ImageDraw, ImageFont
import requests

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Hugging Face Serverless Inference API endpoints
DEFAULT_HF_ENDPOINTS = [
    "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5",
    "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell",
    "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0",
]
HF_API_URL = DEFAULT_HF_ENDPOINTS[0]

# Cooldown timestamp to prevent repeated network delays when Hugging Face API errors or is slow
_HF_COOLDOWN_UNTIL = 0.0

# Canvas dimensions
CANVAS_WIDTH = 768
CANVAS_HEIGHT = 512

# Style palettes for Pillow fallback generator
STYLE_PALETTES: Dict[str, Dict[str, Any]] = {
    "Classic Comic Book": {
        "bg": (24, 30, 48),             # Deep comic blue
        "border": (250, 204, 21),        # Golden comic yellow
        "inner_border": (239, 68, 68),   # Bold comic red
        "badge_bg": (239, 68, 68),       # Comic red
        "badge_text": (255, 255, 255),   # White
        "card_bg": (33, 42, 66),         # Comic panel container
        "card_border": (59, 130, 246),   # Sky blue
        "tag_bg": (250, 204, 21),        # Golden yellow
        "tag_text": (17, 24, 39),        # Charcoal
        "title_text": (250, 204, 21),    # Yellow
        "text": (241, 245, 249),         # Crisp white
        "accent": (56, 189, 248),        # Cyan
    },
    "Anime": {
        "bg": (32, 24, 64),              # Twilight purple
        "border": (244, 114, 182),       # Neon sakura pink
        "inner_border": (168, 85, 247),  # Lavender
        "badge_bg": (236, 72, 153),      # Vivid pink
        "badge_text": (255, 255, 255),   # White
        "card_bg": (48, 38, 92),         # Deep indigo
        "card_border": (192, 132, 252),  # Bright lavender
        "tag_bg": (168, 85, 247),        # Purple
        "tag_text": (255, 255, 255),     # White
        "title_text": (244, 114, 182),   # Sakura pink
        "text": (253, 242, 248),         # Soft white
        "accent": (244, 114, 182),       # Pink
    },
    "Pixel Art": {
        "bg": (15, 23, 42),              # 8-bit dark midnight
        "border": (52, 211, 153),        # Emerald green
        "inner_border": (14, 165, 233),  # Cyan
        "badge_bg": (16, 185, 129),      # Retro arcade green
        "badge_text": (0, 0, 0),         # Black
        "card_bg": (30, 41, 59),         # Dark slate
        "card_border": (52, 211, 153),   # Emerald green
        "tag_bg": (14, 165, 233),        # Cyan
        "tag_text": (255, 255, 255),     # White
        "title_text": (52, 211, 153),    # Green
        "text": (209, 250, 229),         # Soft mint
        "accent": (52, 211, 153),        # Mint
    },
    "Realistic": {
        "bg": (24, 24, 27),              # Neutral dark zinc
        "border": (212, 212, 216),       # Silver
        "inner_border": (113, 113, 122), # Charcoal
        "badge_bg": (82, 82, 91),        # Zinc badge
        "badge_text": (255, 255, 255),   # White
        "card_bg": (39, 39, 42),         # Card surface
        "card_border": (161, 161, 170),  # Steel border
        "tag_bg": (113, 113, 122),       # Slate gray
        "tag_text": (255, 255, 255),     # White
        "title_text": (244, 244, 245),   # Off-white
        "text": (228, 228, 231),         # Light gray
        "accent": (212, 212, 216),       # Silver
    },
    "Graphic Novel Noir": {
        "bg": (10, 10, 10),              # Stark black
        "border": (255, 255, 255),       # Pure white
        "inner_border": (220, 38, 38),   # Sinister crimson
        "badge_bg": (220, 38, 38),       # Crimson
        "badge_text": (255, 255, 255),   # White
        "card_bg": (26, 26, 26),         # Deep gray
        "card_border": (153, 27, 27),    # Dark crimson
        "tag_bg": (220, 38, 38),         # Crimson
        "tag_text": (255, 255, 255),     # White
        "title_text": (255, 255, 255),   # White
        "text": (245, 245, 245),         # Crisp white
        "accent": (220, 38, 38),         # Crimson
    },
}


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Load a system font or fall back gracefully to PIL default font."""
    font_candidates = [
        "arialbd.ttf" if bold else "arial.ttf",
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "Arial.ttf",
        "arial.ttf",
    ]
    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _get_palette(art_style: str) -> Dict[str, Any]:
    """Retrieve style palette with case-insensitive and partial match fallback."""
    cleaned = (art_style or "").strip().lower()
    for key, palette in STYLE_PALETTES.items():
        if key.lower() == cleaned or key.lower() in cleaned or cleaned in key.lower():
            return palette
    return STYLE_PALETTES["Classic Comic Book"]


def _generate_fallback_image(
    prompt: str,
    panel_number: int,
    art_style: str,
    output_path: Path,
) -> None:
    """Synthesize a high-quality stylized comic panel placeholder using Pillow.

    Renders double comic borders, panel badge, art style pill, stylized container,
    and cleanly wrapped prompt text matching the specified visual style palette.
    """
    palette = _get_palette(art_style)
    width, height = CANVAS_WIDTH, CANVAS_HEIGHT

    # Create canvas
    img = Image.new("RGB", (width, height), color=palette["bg"])
    draw = ImageDraw.Draw(img)

    # 1. Subtle comic halftone / dot pattern
    dot_color = tuple(min(255, c + 14) for c in palette["bg"])
    for x in range(32, width - 32, 24):
        for y in range(32, height - 32, 24):
            draw.rectangle([x, y, x + 2, y + 2], fill=dot_color)

    # 2. Double comic border
    # Outer border
    draw.rectangle(
        [10, 10, width - 11, height - 11],
        outline=palette["border"],
        width=4,
    )
    # Inner border
    draw.rectangle(
        [18, 18, width - 19, height - 19],
        outline=palette["inner_border"],
        width=2,
    )

    # 3. Panel badge (Top-left)
    badge_font = _get_font(size=18, bold=True)
    badge_text = f"PANEL {panel_number}"
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    badge_w = max(110, text_w + 28)
    badge_box = [30, 26, 30 + badge_w, 62]
    draw.rounded_rectangle(badge_box, radius=6, fill=palette["badge_bg"])
    # Center text in badge
    bx = badge_box[0] + (badge_w - text_w) // 2
    by = badge_box[1] + (36 - text_h) // 2 - bbox[1]
    draw.text((bx, by), badge_text, font=badge_font, fill=palette["badge_text"])

    # 4. Art style tag (Top-right)
    tag_font = _get_font(size=14, bold=True)
    tag_text = art_style.upper()
    t_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
    tag_tw = t_bbox[2] - t_bbox[0]
    tag_th = t_bbox[3] - t_bbox[1]
    tag_w = tag_tw + 24
    tag_box = [width - 30 - tag_w, 26, width - 30, 62]
    draw.rounded_rectangle(tag_box, radius=6, fill=palette["tag_bg"])
    tx = tag_box[0] + (tag_w - tag_tw) // 2
    ty = tag_box[1] + (36 - tag_th) // 2 - t_bbox[1]
    draw.text((tx, ty), tag_text, font=tag_font, fill=palette["tag_text"])

    # 5. Central Panel Illustration Container
    card_box = [30, 78, width - 30, height - 30]
    draw.rounded_rectangle(
        card_box,
        radius=10,
        fill=palette["card_bg"],
        outline=palette["card_border"],
        width=2,
    )

    # Decorative header in container
    header_font = _get_font(size=16, bold=True)
    header_text = "ILLUSTRATION CONCEPT"
    draw.text((50, 96), header_text, font=header_font, fill=palette["title_text"])

    # Accent divider
    draw.line(
        [(50, 122), (width - 50, 122)],
        fill=palette["accent"],
        width=2,
    )

    # 6. Rounded caption container for prompt text
    caption_box = [50, 138, width - 50, height - 48]
    draw.rounded_rectangle(
        caption_box,
        radius=8,
        fill=palette["bg"],
        outline=palette["border"],
        width=1,
    )

    # Visual prompt tag
    label_font = _get_font(size=13, bold=True)
    draw.text((68, 154), "DIFFUSION PROMPT:", font=label_font, fill=palette["accent"])

    # Clean text wrapping
    text_font = _get_font(size=15, bold=False)
    clean_prompt = " ".join(prompt.split()) if prompt else "Dynamic comic scene illustration"
    wrapped_lines = textwrap.wrap(clean_prompt, width=64)

    # Render wrapped lines
    y_offset = 184
    max_lines = 8
    for line in wrapped_lines[:max_lines]:
        draw.text((68, y_offset), line, font=text_font, fill=palette["text"])
        y_offset += 24

    if len(wrapped_lines) > max_lines:
        draw.text((68, y_offset), "...", font=text_font, fill=palette["text"])

    # ComicCraft watermark branding at bottom of card
    footer_font = _get_font(size=11, bold=False)
    draw.text(
        (68, height - 74),
        "ComicCraft Studio • Stable Diffusion Synthesis Engine (Pillow Fallback)",
        font=footer_font,
        fill=palette["card_border"],
    )

    # Ensure output directory exists and save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="PNG")
    logger.debug("Synthesized fallback panel image to %s", output_path)


def generate_image(
    prompt: str,
    panel_number: int = 1,
    art_style: str = "Classic Comic Book",
    filename: Optional[str] = None,
) -> str:
    """Generate or synthesize an artwork image for a comic panel.

    Attempts generation via Hugging Face Serverless Inference API (when HF_API_KEY
    is set and DEV_MOCK_AI is False). Falls back reliably to Pillow stylized comic
    panel generator on API failure, timeout, or mock mode.

    Args:
        prompt: Scene visual prompt.
        panel_number: Panel sequence number (1-5).
        art_style: Chosen art style aesthetic.
        filename: Optional explicit filename.

    Returns:
        Absolute disk path to the saved PNG image as string.
    """
    settings = get_settings()

    # Determine filename and destination path
    if filename:
        clean_filename = filename if filename.lower().endswith(".png") else f"{filename}.png"
    else:
        unique_hex = secrets.token_hex(4)
        clean_filename = f"panel_{int(time.time())}_{panel_number}_{unique_hex}.png"

    output_path = settings.PANELS_DIR / clean_filename

    global _HF_COOLDOWN_UNTIL

    # Attempt Hugging Face Inference API if configured, mock mode is off, and not in cooldown
    if settings.HF_API_KEY and not settings.DEV_MOCK_AI and time.time() >= _HF_COOLDOWN_UNTIL:
        enhanced_prompt = (
            f"comic book panel illustration, {art_style} style, vivid detailed colors, "
            f"clean lineart, graphic novel art, high quality: {prompt}"
        )
        headers = {
            "Authorization": f"Bearer {settings.HF_API_KEY}",
            "Accept": "image/png",
        }
        payload = {"inputs": enhanced_prompt}

        endpoint_url = getattr(settings, "HF_API_URL", HF_API_URL)
        try:
            logger.info("Calling Hugging Face endpoint %s for panel %s...", endpoint_url, panel_number)
            response = requests.post(
                endpoint_url,
                headers=headers,
                json=payload,
                timeout=(2.0, 4.0),
            )

            if response.status_code == 200 and response.content:
                try:
                    img = Image.open(io.BytesIO(response.content))
                    # Ensure canvas size matches 768x512
                    if img.size != (CANVAS_WIDTH, CANVAS_HEIGHT):
                        img = img.resize(
                            (CANVAS_WIDTH, CANVAS_HEIGHT),
                            Image.Resampling.LANCZOS,
                        )
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    img.save(output_path, format="PNG")
                    logger.info("Successfully generated panel image via HF API: %s", output_path)
                    return str(output_path)
                except Exception as parse_err:
                    logger.warning(
                        "Failed to decode HF API response bytes as valid image (%s).",
                        parse_err,
                    )
            else:
                logger.warning(
                    "HF API call to %s failed with status %s. Setting cooldown.",
                    endpoint_url,
                    response.status_code,
                )
                _HF_COOLDOWN_UNTIL = time.time() + 180.0
        except Exception as api_err:
            logger.warning(
                "Error contacting Hugging Face endpoint %s (%s). Setting cooldown.",
                endpoint_url,
                api_err,
            )
            _HF_COOLDOWN_UNTIL = time.time() + 180.0

    # Fallback to Pillow procedural stylized comic panel generator
    _generate_fallback_image(
        prompt=prompt,
        panel_number=panel_number,
        art_style=art_style,
        output_path=output_path,
    )
    return str(output_path)


async def generate_all_panels(
    outline: List[Union[Dict[str, Any], Any]],
    art_style: str = "Classic Comic Book",
) -> List[str]:
    """Concurrently generate panel illustrations for all panels in the outline.

    Executes image generation in parallel using asyncio.to_thread worker pool.

    Args:
        outline: List of 5 outline dictionaries or Pydantic PanelOutline models.
        art_style: Visual art style name.

    Returns:
        List of 5 generated image file paths in panel sequence order.
    """
    tasks = []
    for idx, panel in enumerate(outline, start=1):
        if isinstance(panel, dict):
            prompt = (
                panel.get("image_prompt")
                or panel.get("prompt")
                or panel.get("scene_description")
                or panel.get("title")
                or f"Comic Panel {idx}"
            )
            panel_num = panel.get("panel", idx)
        else:
            prompt = (
                getattr(panel, "image_prompt", None)
                or getattr(panel, "prompt", None)
                or getattr(panel, "scene_description", None)
                or getattr(panel, "title", None)
                or f"Comic Panel {idx}"
            )
            panel_num = getattr(panel, "panel", idx)

        tasks.append(
            asyncio.to_thread(
                generate_image,
                prompt=prompt,
                panel_number=panel_num,
                art_style=art_style,
            )
        )

    results = await asyncio.gather(*tasks)
    return list(results)
