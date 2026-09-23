"""Gemini 1.5 Flash outline generator with resilient mock fallback."""

import json
import logging
from typing import Any, Dict, List

from app.ai.gemini_client import configure_gemini
from app.config import get_settings
from app.schemas import PanelOutline

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "You are an expert comic book storyboard artist and scriptwriter. "
    "Your goal is to generate a structured 5-panel comic storyline outline based on the user's premise. "
    "You must follow the classic narrative arc: "
    "Panel 1: Setup - introduce the protagonist and the setting; "
    "Panel 2: Inciting Incident / Discovery - introduce the quest, mystery, or conflict catalyst; "
    "Panel 3: Escalation / Conflict - rising stakes, confrontation, or challenge; "
    "Panel 4: Climax / Decisive Action - the pivotal moment or heroic clash; "
    "Panel 5: Resolution & Aftermath - calm, reflection, or triumph. "
    "Return ONLY a valid JSON array containing exactly 5 panel objects. "
    "Each panel object must have the following keys: "
    "'panel' (int 1 to 5), 'title' (string), 'scene_description' (string), and 'image_prompt' (string). "
    "The 'image_prompt' must be a detailed visual prompt describing the scene, protagonist, and environment, explicitly incorporating the requested art style."
)


def _generate_mock_outline(
    user_prompt: str,
    character_name: str = "Hero",
    setting: str = "Enchanted Forest",
    tone: str = "Dramatic",
    art_style: str = "Classic Comic Book",
) -> List[Dict[str, Any]]:
    """Generate a dynamic, theme-rich 5-panel fallback outline.

    Args:
        user_prompt: User storyline premise.
        character_name: Name of the main character.
        setting: Story setting/world.
        tone: Narrative tone/mood.
        art_style: Visual art style for illustrations.

    Returns:
        List of 5 panel outline dictionaries.
    """
    clean_premise = user_prompt.strip() if user_prompt else "A fateful adventure unfolds."
    char_str = character_name.strip() if character_name else "Hero"
    setting_str = setting.strip() if setting else "Enchanted Forest"
    tone_str = tone.strip() if tone else "Dramatic"
    style_str = art_style.strip() if art_style else "Classic Comic Book"

    return [
        {
            "panel": 1,
            "title": f"The Beginning at {setting_str}",
            "scene_description": (
                f"In this {tone_str.lower()} tale inspired by '{clean_premise}', "
                f"{char_str} arrives at {setting_str}, surveying the vast landscape and preparing for what lies ahead."
            ),
            "image_prompt": (
                f"{style_str} illustration of {char_str} standing resolutely at {setting_str}, "
                f"establishing wide cinematic shot, {tone_str.lower()} atmosphere, dynamic composition, comic art."
            ),
        },
        {
            "panel": 2,
            "title": f"Discovery in {setting_str}",
            "scene_description": (
                f"While exploring deeper into {setting_str}, {char_str} uncovers an unexpected omen and strange glowing artifact, "
                f"sparking an inciting turning point in the adventure."
            ),
            "image_prompt": (
                f"{style_str} illustration of {char_str} reaching toward a mysterious glowing artifact in {setting_str}, "
                f"mystical lighting, close-up expressive angle, {tone_str.lower()} mood, detailed comic line art."
            ),
        },
        {
            "panel": 3,
            "title": "Peril and Confrontation",
            "scene_description": (
                f"Tension escalates as shadowy hostile forces surge across {setting_str}, "
                f"confronting {char_str} in a dangerous standoff."
            ),
            "image_prompt": (
                f"{style_str} illustration of {char_str} in dynamic battle stance confronting encroaching shadowy adversaries in {setting_str}, "
                f"dramatic foreshortening, high contrast ink shadows, intense {tone_str.lower()} tension."
            ),
        },
        {
            "panel": 4,
            "title": "The Decisive Clash",
            "scene_description": (
                f"{char_str} channels all their resolve and unleashes a decisive strike, "
                f"turning the tide of conflict across {setting_str}."
            ),
            "image_prompt": (
                f"{style_str} illustration of {char_str} unleashing a radiant power burst to repel the danger in {setting_str}, "
                f"full-page climax impact, speed lines, vivid colors, epic {tone_str.lower()} comic action."
            ),
        },
        {
            "panel": 5,
            "title": "Triumph and Aftermath",
            "scene_description": (
                f"With the trial resolved, {char_str} gazes into the horizon over {setting_str}, "
                f"reflecting on the journey with new strength and hope."
            ),
            "image_prompt": (
                f"{style_str} illustration of {char_str} standing triumphant amidst the peaceful aftermath at {setting_str}, "
                f"golden hour lighting, cinematic resolution shot, inspiring {tone_str.lower()} mood, high quality comic book panel."
            ),
        },
    ]


DEFAULT_FLASH_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
]


def generate_outline(
    user_prompt: str,
    character_name: str = "Hero",
    setting: str = "Enchanted Forest",
    tone: str = "Dramatic",
    art_style: str = "Classic Comic Book",
) -> List[Dict[str, Any]]:
    """Generate a structured 5-panel comic storyline outline using Gemini Flash.

    Falls back safely to a deterministic, dynamic mock outline if offline, in test mode,
    without API keys, or if all model candidates fail.

    Args:
        user_prompt: Core story idea or premise.
        character_name: Protagonist name.
        setting: Story setting / backdrop.
        tone: Narrative tone.
        art_style: Target visual art style.

    Returns:
        List of 5 panel dictionaries adhering to PanelOutline schema.
    """
    settings = get_settings()

    if settings.DEV_MOCK_AI:
        logger.info("DEV_MOCK_AI enabled; using dynamic mock outline.")
        return _generate_mock_outline(user_prompt, character_name, setting, tone, art_style)

    genai = configure_gemini()
    if genai is None:
        logger.info("Gemini client unavailable; falling back to mock outline.")
        return _generate_mock_outline(user_prompt, character_name, setting, tone, art_style)

    preferred_model = getattr(settings, "GEMINI_MODEL_FLASH", "gemini-3.6-flash")
    raw_candidates = [preferred_model] + DEFAULT_FLASH_MODELS
    candidate_models = list(dict.fromkeys(raw_candidates))

    user_content = (
        f"Story Premise: {user_prompt}\n"
        f"Protagonist Name: {character_name}\n"
        f"Setting: {setting}\n"
        f"Tone: {tone}\n"
        f"Art Style: {art_style}\n\n"
        "Generate the 5-panel comic storyline outline as a JSON array of 5 panel objects."
    )

    for model_name in candidate_models:
        try:
            logger.info("Attempting Gemini Flash outline generation with model: %s", model_name)
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_INSTRUCTION,
                generation_config={"response_mime_type": "application/json"},
            )

            response = model.generate_content(user_content)
            raw_text = response.text.strip()

            # Handle potential markdown wrappers
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
                for candidate_key in ("panels", "outline", "storyboard", "data", "layout"):
                    if candidate_key in parsed and isinstance(parsed[candidate_key], list):
                        raw_panels = parsed[candidate_key]
                        break
            else:
                raw_panels = []

            if len(raw_panels) != 5:
                raise ValueError(f"Expected exactly 5 panels from Gemini Flash, received {len(raw_panels)}")

            validated_panels: List[Dict[str, Any]] = []
            for item in raw_panels:
                outline_model = PanelOutline(
                    panel=int(item.get("panel")),
                    title=str(item.get("title", "")).strip(),
                    scene_description=str(item.get("scene_description", "")).strip(),
                    image_prompt=str(item.get("image_prompt", "")).strip(),
                )
                if not outline_model.title or not outline_model.scene_description or not outline_model.image_prompt:
                    raise ValueError("PanelOutline fields must not be empty.")
                validated_panels.append(outline_model.model_dump())

            logger.info("Successfully generated 5-panel outline using Gemini Flash (%s).", model_name)
            return validated_panels

        except Exception as exc:
            logger.warning(
                "Gemini Flash model '%s' encountered an error: %s. Trying next candidate...",
                model_name,
                exc,
            )
            continue

    logger.warning("All Gemini Flash candidate models failed. Falling back to dynamic mock outline.")
    return _generate_mock_outline(user_prompt, character_name, setting, tone, art_style)
