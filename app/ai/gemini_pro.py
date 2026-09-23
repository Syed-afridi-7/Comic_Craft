"""Gemini 1.5 Pro narrative expansion and character dialogue generator."""

import json
import logging
from typing import Any, Dict, List

from app.ai.gemini_client import configure_gemini
from app.config import get_settings
from app.schemas import PanelStory

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "You are an expert comic book scriptwriter and dialogue specialist. "
    "Your role is to expand a 5-panel comic storyline outline into rich, immersive narrative prose, "
    "ambient captions, and authentic character dialogue matching the requested character name and tone. "
    "For each panel, produce: "
    "1. 'panel': integer (1 to 5 matching the panel sequence). "
    "2. 'caption': 1 evocative sentence describing the ambient sound, atmosphere, or setting. "
    "3. 'narration': 1-2 compelling sentences of narrative storytelling describing action and emotional weight. "
    "4. 'dialogue': Character dialogue formatted in comic speech format, e.g. '{character_name}: \"...\"'. "
    "Return ONLY a valid JSON array containing exactly 5 panel objects with keys: "
    "'panel', 'caption', 'narration', and 'dialogue'."
)


def _get_mock_story(
    outline: List[Dict[str, Any]],
    character_name: str = "Hero",
    tone: str = "Dramatic",
) -> List[Dict[str, Any]]:
    """Generate a dynamic, tone-rich 5-panel fallback story script.

    Args:
        outline: Outline panels (if available).
        character_name: Protagonist name.
        tone: Story narrative tone.

    Returns:
        List of 5 panel story dictionaries conforming to PanelStory.
    """
    char_str = character_name.strip() if character_name else "Hero"
    tone_str = tone.strip() if tone else "Dramatic"

    templates = [
        {
            "caption": "An uneasy quiet settles across the landscape as winds whisper of imminent change.",
            "narration": f"In this {tone_str.lower()} journey, {char_str} steps into the unknown, eyes scanning the horizon for signs of destiny.",
            "dialogue": f"{char_str}: 'Every journey begins with a choice. I won't turn back now.'",
        },
        {
            "caption": "A sudden hum of mystical resonance shivers through the stillness.",
            "narration": f"An unexpected discovery unfolds before {char_str}, revealing secrets that challenge everything once assumed.",
            "dialogue": f"{char_str}: 'The rumors were true... the power here is waking up.'",
        },
        {
            "caption": "Dark tension fractures the air as impending danger closes in!",
            "narration": f"Adversity strikes with ferocious intensity, forcing {char_str} into a desperate test of endurance and courage.",
            "dialogue": f"{char_str}: 'You thought you could corner me? Think again!'",
        },
        {
            "caption": "A blinding flash erupts across the heavens with thunderous power!",
            "narration": f"Summoning every ounce of will, {char_str} executes a decisive maneuver that turns the tide of the clash.",
            "dialogue": f"{char_str}: 'This ends here and now! Take everything I've got!'",
        },
        {
            "caption": "Golden twilight cascades gently as the dust of battle begins to settle.",
            "narration": f"Peace returns to the quiet realm, leaving {char_str} stronger, wiser, and prepared for tomorrow's dawn.",
            "dialogue": f"{char_str}: 'The storm has broken. Our world is safe for another day.'",
        },
    ]

    mock_panels: List[Dict[str, Any]] = []
    for idx in range(1, 6):
        item = templates[idx - 1]

        caption = item["caption"]
        narration = item["narration"]
        dialogue = item["dialogue"]

        # If outline provides context for this panel, weave in scene details
        if outline and len(outline) >= idx:
            outline_panel = outline[idx - 1]
            scene_desc = outline_panel.get("scene_description", "").strip()
            title = outline_panel.get("title", "").strip()
            if scene_desc:
                narration = f"{narration} {scene_desc}"
            if title:
                caption = f"[{title}] {caption}"

        story_panel = PanelStory(
            panel=idx,
            caption=caption,
            narration=narration,
            dialogue=dialogue,
        )
        mock_panels.append(story_panel.model_dump())

    return mock_panels


DEFAULT_PRO_MODELS = [
    "gemini-pro-latest",
    "gemini-3.1-pro-preview",
    "gemini-2.5-pro",
    "gemini-1.5-pro",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest",
]


def generate_story(
    outline: List[Dict[str, Any]],
    character_name: str = "Hero",
    tone: str = "Dramatic",
) -> List[Dict[str, Any]]:
    """Generate narrative captions, storytelling, and character dialogue for a 5-panel comic using Gemini Pro.

    Falls back safely to contextual mock narrative if offline, in test mode,
    without API keys, or if all model candidates fail.

    Args:
        outline: 5-panel outline list from gemini_flash.generate_outline.
        character_name: Name of the protagonist.
        tone: Narrative tone or mood.

    Returns:
        List of 5 panel story dictionaries adhering to PanelStory schema.
    """
    settings = get_settings()

    if settings.DEV_MOCK_AI:
        logger.info("DEV_MOCK_AI enabled; using mock story.")
        return _get_mock_story(outline, character_name, tone)

    genai = configure_gemini()
    if genai is None:
        logger.info("Gemini client unavailable; falling back to mock story.")
        return _get_mock_story(outline, character_name, tone)

    preferred_model = getattr(settings, "GEMINI_MODEL_PRO", "gemini-pro-latest")
    raw_candidates = [preferred_model] + DEFAULT_PRO_MODELS
    candidate_models = list(dict.fromkeys(raw_candidates))

    outline_summary = json.dumps(outline, indent=2) if outline else "No outline provided."
    user_content = (
        f"Protagonist: {character_name}\n"
        f"Story Tone: {tone}\n"
        f"Comic Outline:\n{outline_summary}\n\n"
        "Write the caption, narration, and character dialogue for each of the 5 panels. "
        "Dialogue must explicitly show speech in comic format (e.g. \"Hero: '...' \"). "
        "Return a JSON array containing exactly 5 panel objects."
    )

    for model_name in candidate_models:
        try:
            logger.info("Attempting Gemini Pro narrative story generation with model: %s", model_name)
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_INSTRUCTION,
                generation_config={"response_mime_type": "application/json"},
            )

            response = model.generate_content(user_content)
            raw_text = response.text.strip()

            # Handle markdown blocks if present
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()

            parsed = json.loads(raw_text)

            # Extract array if nested under a key
            if isinstance(parsed, list):
                raw_panels = parsed
            elif isinstance(parsed, dict):
                raw_panels = []
                for candidate_key in ("panels", "story", "storyboard", "data", "layout"):
                    if candidate_key in parsed and isinstance(parsed[candidate_key], list):
                        raw_panels = parsed[candidate_key]
                        break
            else:
                raw_panels = []

            if len(raw_panels) != 5:
                raise ValueError(f"Expected exactly 5 panels from Gemini Pro, received {len(raw_panels)}")

            validated_panels: List[Dict[str, Any]] = []
            for item in raw_panels:
                story_model = PanelStory(
                    panel=int(item.get("panel")),
                    caption=str(item.get("caption", "")).strip(),
                    narration=str(item.get("narration", "")).strip(),
                    dialogue=str(item.get("dialogue", "")).strip(),
                )
                if not story_model.caption or not story_model.narration or not story_model.dialogue:
                    raise ValueError("PanelStory fields must not be empty.")
                validated_panels.append(story_model.model_dump())

            logger.info("Successfully generated 5-panel narrative story using Gemini model %s.", model_name)
            return validated_panels

        except Exception as exc:
            logger.warning(
                "Gemini model '%s' story generation encountered an error: %s. Trying next candidate...",
                model_name,
                exc,
            )
            continue

    logger.warning("All Gemini Pro candidate models failed. Falling back to mock story.")
    return _get_mock_story(outline, character_name, tone)
