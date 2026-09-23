import json
from unittest.mock import MagicMock, patch
import pytest

from app.config import Settings
from app.schemas import PanelStory
from app.ai.gemini_pro import generate_story, _get_mock_story


@pytest.fixture
def sample_outline():
    return [
        {
            "panel": 1,
            "title": "The Awakening",
            "scene_description": "Hero stands at the edge of the Enchanted Forest.",
            "image_prompt": "Classic Comic Book style, Hero looking into glowing forest.",
        },
        {
            "panel": 2,
            "title": "The Discovery",
            "scene_description": "Hero uncovers an ancient rune in the glade.",
            "image_prompt": "Classic Comic Book style, Hero holding glowing rune.",
        },
        {
            "panel": 3,
            "title": "The Ambush",
            "scene_description": "Shadow beasts surround Hero with glowing eyes.",
            "image_prompt": "Classic Comic Book style, Hero surrounded by shadow creatures.",
        },
        {
            "panel": 4,
            "title": "The Decisive Clash",
            "scene_description": "Hero unleashes radiant beam to shatter the shadows.",
            "image_prompt": "Classic Comic Book style, radiant energy blast dispersing shadows.",
        },
        {
            "panel": 5,
            "title": "Tranquil Dawn",
            "scene_description": "Hero gazes at sunrise over the restored woods.",
            "image_prompt": "Classic Comic Book style, peaceful forest with Hero walking forward.",
        },
    ]


def test_generate_story_mock_mode_structure(sample_outline):
    """Verify generate_story returns exactly 5 structured panels in mock mode."""
    character_name = "Lyra"
    tone = "Dramatic"

    mock_settings = Settings(gemini_api_key="", dev_mock_ai=True)
    with patch("app.ai.gemini_pro.get_settings", return_value=mock_settings):
        with patch("app.ai.gemini_pro.configure_gemini", return_value=None):
            story_panels = generate_story(
                outline=sample_outline,
                character_name=character_name,
                tone=tone,
            )

    assert isinstance(story_panels, list)
    assert len(story_panels) == 5

    found_character_dialogue = False

    for i, panel in enumerate(story_panels, start=1):
        assert isinstance(panel, dict)
        assert panel["panel"] == i
        assert isinstance(panel["caption"], str) and len(panel["caption"].strip()) > 0
        assert isinstance(panel["narration"], str) and len(panel["narration"].strip()) > 0
        assert isinstance(panel["dialogue"], str) and len(panel["dialogue"].strip()) > 0

        # Validate with Pydantic PanelStory schema
        validated_story = PanelStory(**panel)
        assert validated_story.panel == i

        if character_name in panel["dialogue"]:
            found_character_dialogue = True

    assert found_character_dialogue, f"Character name '{character_name}' should appear in dialogue lines"


def test_generate_story_gemini_success(sample_outline):
    """Verify generate_story parses valid JSON from Gemini 1.5 Pro response."""
    mock_gemini_story = [
        {
            "panel": 1,
            "caption": "A lone sentinel watches from the ancient ridge.",
            "narration": "Lyra surveyed the quiet woods, senses sharp against the looming silence.",
            "dialogue": "Lyra: 'Whatever is hidden here, I will find it.'",
        },
        {
            "panel": 2,
            "caption": "A hum of forgotten power resonates in the stone.",
            "narration": "The mossy relic pulsed with azure light as Lyra leaned close.",
            "dialogue": "Lyra: 'The legends were true... it is awakening.'",
        },
        {
            "panel": 3,
            "caption": "Darkness descends like a sudden eclipse.",
            "narration": "Monstrous shapes crept from the twisting roots, encircling the glade.",
            "dialogue": "Lyra: 'Stand back, creatures of the void!'",
        },
        {
            "panel": 4,
            "caption": "A brilliant flare ignites the shadows.",
            "narration": "Lyra struck the ground with determination, channeling blazing radiance.",
            "dialogue": "Lyra: 'Not today!'",
        },
        {
            "panel": 5,
            "caption": "Peace gently restores the ancient sanctuary.",
            "narration": "The forest sighed in relief as the dawn sun broke through the canopy.",
            "dialogue": "Lyra: 'The balance holds. For now.'",
        },
    ]

    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_gemini_story)

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    mock_genai = MagicMock()
    mock_genai.GenerativeModel.return_value = mock_model

    mock_settings = Settings(gemini_api_key="valid-key", dev_mock_ai=False)

    with patch("app.ai.gemini_pro.get_settings", return_value=mock_settings):
        with patch("app.ai.gemini_pro.configure_gemini", return_value=mock_genai):
            story_panels = generate_story(
                outline=sample_outline,
                character_name="Lyra",
                tone="Dramatic",
            )

    assert len(story_panels) == 5
    assert story_panels[0]["caption"] == "A lone sentinel watches from the ancient ridge."
    assert "Lyra: 'Whatever is hidden here, I will find it.'" in story_panels[0]["dialogue"]
    mock_genai.GenerativeModel.assert_called_once()
    call_args, call_kwargs = mock_genai.GenerativeModel.call_args
    assert call_kwargs.get("model_name") in ["gemini-pro-latest", "gemini-1.5-pro", "gemini-3.6-flash"]


def test_generate_story_gemini_exception_resilience(sample_outline):
    """Verify generate_story falls back gracefully to mock story on API error."""
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = RuntimeError("Google API network timeout")

    mock_genai = MagicMock()
    mock_genai.GenerativeModel.return_value = mock_model

    mock_settings = Settings(gemini_api_key="valid-key", dev_mock_ai=False)

    with patch("app.ai.gemini_pro.get_settings", return_value=mock_settings):
        with patch("app.ai.gemini_pro.configure_gemini", return_value=mock_genai):
            story_panels = generate_story(
                outline=sample_outline,
                character_name="Marcus",
                tone="Epic",
            )

    assert isinstance(story_panels, list)
    assert len(story_panels) == 5
    assert story_panels[0]["panel"] == 1
    assert any("Marcus" in p["dialogue"] for p in story_panels)


def test_generate_story_malformed_json_resilience(sample_outline):
    """Verify generate_story falls back when Gemini returns invalid JSON."""
    mock_response = MagicMock()
    mock_response.text = "```json\nNot JSON at all!}\n```"

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    mock_genai = MagicMock()
    mock_genai.GenerativeModel.return_value = mock_model

    mock_settings = Settings(gemini_api_key="valid-key", dev_mock_ai=False)

    with patch("app.ai.gemini_pro.get_settings", return_value=mock_settings):
        with patch("app.ai.gemini_pro.configure_gemini", return_value=mock_genai):
            story_panels = generate_story(
                outline=sample_outline,
                character_name="Marcus",
                tone="Epic",
            )

    assert isinstance(story_panels, list)
    assert len(story_panels) == 5
    assert story_panels[0]["panel"] == 1
    assert any("Marcus" in p["dialogue"] for p in story_panels)


def test_generate_story_empty_outline_handled():
    """Verify generate_story gracefully handles an empty outline."""
    story_panels = _get_mock_story(
        outline=[],
        character_name="Valerie",
        tone="Humorous",
    )
    assert len(story_panels) == 5
    for p in story_panels:
        assert "Valerie" in p["dialogue"]
        assert len(p["caption"]) > 0
        assert len(p["narration"]) > 0
