import json
from unittest.mock import MagicMock, patch
import pytest

from app.schemas import PanelOutline
from app.config import Settings
from app.ai.gemini_client import configure_gemini
from app.ai.gemini_flash import generate_outline, _generate_mock_outline


def test_configure_gemini_mock_mode():
    """Verify configure_gemini returns None when DEV_MOCK_AI is True or key is missing."""
    mock_settings = Settings(gemini_api_key="", dev_mock_ai=True)
    with patch("app.ai.gemini_client.get_settings", return_value=mock_settings):
        client = configure_gemini()
        assert client is None

    mock_settings_no_key = Settings(gemini_api_key="", dev_mock_ai=False)
    with patch("app.ai.gemini_client.get_settings", return_value=mock_settings_no_key):
        client = configure_gemini()
        assert client is None


def test_configure_gemini_active_mode():
    """Verify configure_gemini configures google.generativeai when key is present and mock is False."""
    mock_settings = Settings(gemini_api_key="valid-test-key", dev_mock_ai=False)
    with patch("app.ai.gemini_client.get_settings", return_value=mock_settings):
        with patch("google.generativeai.configure") as mock_configure:
            client = configure_gemini()
            assert client is not None
            mock_configure.assert_called_once_with(api_key="valid-test-key")


def test_generate_outline_mock_mode_structure():
    """Verify generate_outline returns exactly 5 structured panels in mock mode."""
    user_prompt = "A brave explorer finds a hidden valley of dragons."
    character_name = "Kaelen"
    setting = "Forgotten Valley"
    tone = "Epic"
    art_style = "Manga Style"

    # Default environment or explicit mock fallback
    mock_settings = Settings(gemini_api_key="", dev_mock_ai=True)
    with patch("app.ai.gemini_flash.get_settings", return_value=mock_settings):
        with patch("app.ai.gemini_flash.configure_gemini", return_value=None):
            panels = generate_outline(
                user_prompt=user_prompt,
                character_name=character_name,
                setting=setting,
                tone=tone,
                art_style=art_style,
            )

    assert isinstance(panels, list)
    assert len(panels) == 5

    found_character = False
    found_setting = False
    found_style = False

    for i, panel in enumerate(panels, start=1):
        assert isinstance(panel, dict)
        assert panel["panel"] == i
        assert isinstance(panel["title"], str) and len(panel["title"].strip()) > 0
        assert isinstance(panel["scene_description"], str) and len(panel["scene_description"].strip()) > 0
        assert isinstance(panel["image_prompt"], str) and len(panel["image_prompt"].strip()) > 0

        # Validate compatibility with Pydantic PanelOutline schema
        validated_panel = PanelOutline(**panel)
        assert validated_panel.panel == i

        # Check reflecting attributes across all panels
        combined_text = f"{panel['title']} {panel['scene_description']} {panel['image_prompt']}"
        if character_name in combined_text:
            found_character = True
        if setting in combined_text:
            found_setting = True
        if art_style in combined_text:
            found_style = True

    assert found_character, f"Character name '{character_name}' was not reflected in generated panels"
    assert found_setting, f"Setting '{setting}' was not reflected in generated panels"
    assert found_style, f"Art style '{art_style}' was not reflected in generated panels"


def test_generate_outline_gemini_success():
    """Verify generate_outline parses valid JSON from Gemini API response."""
    mock_gemini_panels = [
        {
            "panel": 1,
            "title": "The Awakening",
            "scene_description": "Hero stands at the edge of the Enchanted Forest.",
            "image_prompt": "Classic Comic Book style, Hero looking into glowing forest.",
        },
        {
            "panel": 2,
            "title": "The Discovery",
            "scene_description": "Hero uncovers an ancient rune.",
            "image_prompt": "Classic Comic Book style, Hero holding glowing rune.",
        },
        {
            "panel": 3,
            "title": "The Ambush",
            "scene_description": "Shadow creatures emerge from the trees.",
            "image_prompt": "Classic Comic Book style, Hero surrounded by shadow creatures.",
        },
        {
            "panel": 4,
            "title": "The Climax",
            "scene_description": "Hero unleashes radiant beam from rune.",
            "image_prompt": "Classic Comic Book style, radiant energy blast dispersing shadows.",
        },
        {
            "panel": 5,
            "title": "Resolution",
            "scene_description": "The forest returns to tranquil daylight.",
            "image_prompt": "Classic Comic Book style, peaceful forest with Hero walking forward.",
        },
    ]

    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_gemini_panels)

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    mock_genai = MagicMock()
    mock_genai.GenerativeModel.return_value = mock_model

    mock_settings = Settings(gemini_api_key="valid-key", dev_mock_ai=False)

    with patch("app.ai.gemini_flash.get_settings", return_value=mock_settings):
        with patch("app.ai.gemini_flash.configure_gemini", return_value=mock_genai):
            panels = generate_outline(
                user_prompt="Hero explores the forest.",
                character_name="Hero",
                setting="Enchanted Forest",
                tone="Dramatic",
                art_style="Classic Comic Book",
            )

    assert len(panels) == 5
    assert panels[0]["title"] == "The Awakening"
    assert panels[4]["panel"] == 5


def test_generate_outline_gemini_exception_resilience():
    """Verify generate_outline falls back gracefully to mock outline on API error."""
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = RuntimeError("Google API network timeout")

    mock_genai = MagicMock()
    mock_genai.GenerativeModel.return_value = mock_model

    mock_settings = Settings(gemini_api_key="valid-key", dev_mock_ai=False)

    with patch("app.ai.gemini_flash.get_settings", return_value=mock_settings):
        with patch("app.ai.gemini_flash.configure_gemini", return_value=mock_genai):
            # Should not raise exception
            panels = generate_outline(
                user_prompt="Epic quest begins",
                character_name="Arthur",
                setting="Camelot",
                tone="Heroic",
                art_style="Ink and Watercolor",
            )

    assert isinstance(panels, list)
    assert len(panels) == 5
    assert panels[0]["panel"] == 1
    assert "Arthur" in panels[0]["scene_description"] or "Arthur" in panels[0]["image_prompt"]


def test_generate_outline_malformed_json_resilience():
    """Verify generate_outline falls back when Gemini returns invalid JSON."""
    mock_response = MagicMock()
    mock_response.text = "This is not JSON: {some invalid text}"

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    mock_genai = MagicMock()
    mock_genai.GenerativeModel.return_value = mock_model

    mock_settings = Settings(gemini_api_key="valid-key", dev_mock_ai=False)

    with patch("app.ai.gemini_flash.get_settings", return_value=mock_settings):
        with patch("app.ai.gemini_flash.configure_gemini", return_value=mock_genai):
            panels = generate_outline(
                user_prompt="Adventure in space",
                character_name="Nova",
                setting="Nebula Outpost",
                tone="Sci-Fi",
                art_style="Cyberpunk",
            )

    assert isinstance(panels, list)
    assert len(panels) == 5
    assert panels[0]["panel"] == 1
    assert "Nova" in panels[0]["scene_description"] or "Nova" in panels[0]["image_prompt"]
