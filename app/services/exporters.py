"""Multi-page comic PDF exporter service for ComicCraft.

Compiles generated panels, artwork, narrative text, dialogue, and metadata
into a publication-quality multi-page PDF document using FPDF2.
"""

import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fpdf import FPDF
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)


def _to_dict(item: Any) -> Dict[str, Any]:
    """Convert a dictionary or Pydantic model into a dictionary."""
    if hasattr(item, "model_dump") and callable(getattr(item, "model_dump")):
        return item.model_dump()
    if hasattr(item, "dict") and callable(getattr(item, "dict")):
        return item.dict()
    if isinstance(item, dict):
        return dict(item)
    return {}


def _clean_text(text: Any) -> str:
    """Sanitize text to safe Latin-1 encodable characters for standard FPDF fonts.

    Replaces smart quotes, dashes, ellipses, non-breaking spaces, and unicode symbols
    to guarantee that standard Latin-1 fonts never trigger FPDF UnicodeEncodeError.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # Standardize newline characters
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Character mapping dictionary for common non-Latin-1 typography
    replacements = {
        # Single smart quotes and apostrophes
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u2032": "'",
        "\u2035": "'",
        "`": "'",
        # Double smart quotes
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u2033": '"',
        "\u2036": '"',
        "«": '"',
        "»": '"',
        # Dashes & hyphens
        "\u2014": " -- ",
        "\u2013": " - ",
        "\u2015": " -- ",
        "\u2212": "-",
        # Ellipsis
        "\u2026": "...",
        # Spaces
        "\u00a0": " ",
        "\u2000": " ",
        "\u2001": " ",
        "\u2002": " ",
        "\u2003": " ",
        "\u2004": " ",
        "\u2005": " ",
        "\u2006": " ",
        "\u2007": " ",
        "\u2008": " ",
        "\u2009": " ",
        "\u200a": " ",
        "\u202f": " ",
        "\u200b": "",
        "\u200c": "",
        "\u200d": "",
        "\ufeff": "",
        # Bullets & geometric shapes
        "\u2022": "*",
        "\u25cf": "*",
        "\u25cb": "*",
        "\u25a0": "*",
        "\u25aa": "*",
        "\u25ab": "*",
        # Trademark & copyright symbols
        "\u2122": "(TM)",
        "\u00a9": "(C)",
        "\u00ae": "(R)",
    }

    for orig, repl in replacements.items():
        text = text.replace(orig, repl)

    # Encode remaining unencodable codepoints into safe Latin-1 fallback
    return text.encode("latin-1", errors="replace").decode("latin-1")


class ComicPDF(FPDF):
    """Custom FPDF document tailored for ComicCraft multi-page comic layouts."""

    def footer(self) -> None:
        """Render a stylized comic footer with page numbers on each page."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 150, 165)
        # {nb} will be dynamically substituted with total page count by FPDF2
        self.cell(
            0,
            10,
            f"ComicCraft  -  Page {self.page_no()} of {{nb}}",
            align="C",
        )


def save_pdf(
    layout: List[Union[Dict[str, Any], Any]],
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Compile comic panels and metadata into a publication-quality multi-page PDF.

    Args:
        layout: List of panel dictionaries or ComicPanel Pydantic models.
        metadata: Story metadata containing title, character_name, setting, tone, art_style.

    Returns:
        Web-accessible relative URL path to the generated PDF (/static/exports/{filename}).
    """
    settings = get_settings()
    settings.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Normalize metadata values with sensible defaults
    meta = dict(metadata or {})
    title = str(
        meta.get("title")
        or meta.get("story_title")
        or "ComicCraft Graphic Novel"
    ).strip()
    character_name = str(
        meta.get("character_name")
        or meta.get("hero")
        or "Hero"
    ).strip()
    setting = str(meta.get("setting") or "Enchanted Realm").strip()
    tone = str(meta.get("tone") or "Dramatic").strip()
    art_style = str(
        meta.get("art_style")
        or meta.get("style")
        or "Classic Comic Book"
    ).strip()

    # Convert layout elements to standard dictionaries
    clean_layout: List[Dict[str, Any]] = [_to_dict(item) for item in (layout or [])]

    pdf = ComicPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(left=15, top=15, right=15)
    pdf.set_auto_page_break(auto=True, margin=15)

    # -------------------------------------------------------------
    # 1. COVER PAGE
    # -------------------------------------------------------------
    pdf.add_page()

    # Header Banner Container
    pdf.set_fill_color(24, 30, 48)     # Dark comic navy
    pdf.set_draw_color(250, 204, 21)   # Golden comic border
    pdf.set_line_width(0.8)
    pdf.rect(x=15, y=15, w=180, h=46, style="FD")

    # ComicCraft Branding Tag
    pdf.set_xy(15, 19)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(250, 204, 21)
    pdf.cell(180, 6, "COMICCRAFT  *  AI GRAPHIC NOVEL", align="C")

    # Comic Title in Bold Large Font
    pdf.set_xy(20, 26)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(255, 255, 255)
    pdf.multi_cell(170, 9, _clean_text(title), align="C")

    curr_y = 66.0

    # Cover Preview Image (if first panel image exists on disk)
    first_panel_img = None
    if clean_layout:
        raw_img = clean_layout[0].get("image_path")
        if raw_img and Path(raw_img).is_file():
            first_panel_img = str(raw_img)

    if first_panel_img:
        try:
            img_w = 140.0
            img_h = 90.0
            with Image.open(first_panel_img) as pil_im:
                pw, ph = pil_im.size
                if pw > 0 and ph > 0:
                    aspect = ph / pw
                    img_h = min(img_w * aspect, 94.0)
                    img_w = img_h / aspect
            img_x = (210.0 - img_w) / 2.0
            pdf.image(first_panel_img, x=img_x, y=curr_y, w=img_w, h=img_h)

            # Frame around teaser art
            pdf.set_draw_color(51, 65, 85)
            pdf.set_line_width(0.4)
            pdf.rect(x=img_x, y=curr_y, w=img_w, h=img_h, style="D")
            curr_y += img_h + 8.0
        except Exception as img_exc:
            logger.warning("Could not embed cover preview image %s: %s", first_panel_img, img_exc)
            curr_y += 6.0
    else:
        curr_y += 6.0

    # Metadata Block
    pdf.set_fill_color(248, 250, 252)  # Light slate background
    pdf.set_draw_color(203, 213, 225)  # Slate border
    pdf.set_line_width(0.4)
    meta_box_h = 56.0
    pdf.rect(x=15, y=curr_y, w=180, h=meta_box_h, style="FD")

    # Section title
    pdf.set_xy(22, curr_y + 4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(166, 6, "STORY SPECIFICATIONS & METADATA", align="L")

    # Separator line
    pdf.set_draw_color(226, 232, 240)
    pdf.line(22, curr_y + 12, 188, curr_y + 12)

    # Row 1: Protagonist & Setting
    pdf.set_xy(22, curr_y + 16)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(28, 6, "Protagonist:")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(56, 6, _clean_text(character_name)[:26])

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(24, 6, "Setting:")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(58, 6, _clean_text(setting)[:28])

    # Row 2: Narrative Tone & Art Style
    pdf.set_xy(22, curr_y + 26)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(28, 6, "Tone:")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(56, 6, _clean_text(tone)[:26])

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(24, 6, "Art Style:")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(58, 6, _clean_text(art_style)[:28])

    # Row 3: Length & Format
    pdf.set_xy(22, curr_y + 36)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(28, 6, "Panels:")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(56, 6, f"{len(clean_layout)} Sequential Panels")

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(24, 6, "Edition:")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(58, 6, "ComicCraft Digital Issue")

    # Cover page bottom note
    pdf.set_xy(15, 262)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(180, 6, "Crafted autonomously with ComicCraft AI Engine", align="C")

    # -------------------------------------------------------------
    # 2. PANEL PAGES (One page per panel)
    # -------------------------------------------------------------
    for idx, panel in enumerate(clean_layout):
        pdf.add_page()
        panel_num = panel.get("panel") or (idx + 1)
        panel_title = str(panel.get("title") or "").strip()
        scene_desc = str(panel.get("scene_description") or "").strip()
        caption = str(panel.get("caption") or "").strip()
        narration = str(panel.get("narration") or "").strip()
        dialogue = str(panel.get("dialogue") or "").strip()
        image_path_str = str(panel.get("image_path") or "").strip()

        # Panel Header Bar
        pdf.set_fill_color(24, 30, 48)     # Dark comic navy
        pdf.set_draw_color(250, 204, 21)   # Gold border
        pdf.set_line_width(0.6)
        pdf.rect(x=15, y=15, w=180, h=11, style="FD")

        header_text = (
            f"Panel {panel_num}: {_clean_text(panel_title)}"
            if panel_title
            else f"Panel {panel_num}"
        )
        pdf.set_xy(18, 16.5)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(250, 204, 21)
        pdf.cell(174, 8, header_text, align="L")

        curr_y = 29.0

        # Centered Panel Artwork Image
        img_rendered = False
        if image_path_str and Path(image_path_str).is_file():
            try:
                with Image.open(image_path_str) as pil_im:
                    pw, ph = pil_im.size
                if pw > 0 and ph > 0:
                    aspect = ph / pw
                    # Scale to w=160mm, cap max height to prevent overflow
                    img_w = 160.0
                    img_h = img_w * aspect
                    if img_h > 108.0:
                        img_h = 108.0
                        img_w = img_h / aspect
                    img_x = (210.0 - img_w) / 2.0
                    pdf.image(image_path_str, x=img_x, y=curr_y, w=img_w, h=img_h)

                    # Border frame around artwork
                    pdf.set_draw_color(15, 23, 42)
                    pdf.set_line_width(0.5)
                    pdf.rect(x=img_x, y=curr_y, w=img_w, h=img_h, style="D")
                    curr_y += img_h + 4.0
                    img_rendered = True
            except Exception as img_err:
                logger.warning("Error embedding panel %d image: %s", panel_num, img_err)

        if not img_rendered:
            # Fallback placeholder artwork container
            box_w = 160.0
            box_h = 75.0
            box_x = (210.0 - box_w) / 2.0
            pdf.set_fill_color(241, 245, 249)
            pdf.set_draw_color(203, 213, 225)
            pdf.set_line_width(0.5)
            pdf.rect(x=box_x, y=curr_y, w=box_w, h=box_h, style="FD")

            pdf.set_xy(box_x, curr_y + 30)
            pdf.set_font("Helvetica", "I", 11)
            pdf.set_text_color(148, 163, 184)
            pdf.cell(box_w, 8, f"[ Panel {panel_num} Artwork Placeholder ]", align="C")
            curr_y += box_h + 4.0

        # Scene description paragraph in italics (10pt)
        if scene_desc:
            pdf.set_xy(15, curr_y)
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(75, 85, 99)
            pdf.multi_cell(180, 5, _clean_text(f"Scene: {scene_desc}"), align="L")
            curr_y = pdf.get_y() + 2.5

        # Ambient caption box
        if caption:
            pdf.set_xy(15, curr_y)
            pdf.set_fill_color(254, 243, 199)  # Soft amber parchment
            pdf.set_draw_color(245, 158, 11)   # Amber border
            pdf.set_line_width(0.3)
            pdf.set_font("Helvetica", "I", 9.5)
            pdf.set_text_color(120, 53, 15)
            caption_text = f"CAPTION: {_clean_text(caption)}"
            pdf.multi_cell(180, 5.2, caption_text, border=1, fill=True, align="L")
            curr_y = pdf.get_y() + 2.5

        # Narration text box
        if narration:
            pdf.set_xy(15, curr_y)
            pdf.set_fill_color(241, 245, 249)  # Light slate tint
            pdf.set_draw_color(148, 163, 184)  # Slate border
            pdf.set_line_width(0.3)
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(30, 41, 59)
            narration_text = f"NARRATION: {_clean_text(narration)}"
            pdf.multi_cell(180, 5.2, narration_text, border=1, fill=True, align="L")
            curr_y = pdf.get_y() + 2.5

        # Character dialogue box styled with speech label
        if dialogue:
            pdf.set_xy(15, curr_y)
            pdf.set_fill_color(239, 246, 255)  # Soft blue tint
            pdf.set_draw_color(59, 130, 246)   # Blue accent border
            pdf.set_line_width(0.4)
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(30, 58, 138)
            dialogue_text = f"SPEECH: {_clean_text(dialogue)}"
            pdf.multi_cell(180, 5.2, dialogue_text, border=1, fill=True, align="L")
            curr_y = pdf.get_y() + 2.5

    # -------------------------------------------------------------
    # 3. SAVE TO DISK AND RETURN RELATIVE URL
    # -------------------------------------------------------------
    timestamp = int(time.time())
    unique_hex = uuid.uuid4().hex[:8]
    filename = f"comic_{timestamp}_{unique_hex}.pdf"
    pdf_path = settings.EXPORTS_DIR / filename

    pdf.output(str(pdf_path))
    logger.info("Exported comic PDF to %s", pdf_path)

    return f"/static/exports/{filename}"
