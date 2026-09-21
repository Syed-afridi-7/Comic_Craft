import os
from pathlib import Path
import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.schemas import (
    PromptRequest,
    PanelOutline,
    PanelStory,
    ComicPanel,
    ComicResponse,
)


def test_settings_initialization(tmp_path):
    """Test Settings initialization, directory auto-creation, and attributes."""
    settings = get_settings()
    assert settings.BASE_DIR.exists()
    assert isinstance(settings.GEMINI_API_KEY, str)
    assert isinstance(settings.HF_API_KEY, str)
    assert isinstance(settings.DEV_MOCK_AI, bool)
    assert settings.STATIC_DIR.name == "static"
    assert settings.PANELS_DIR.exists()
    assert settings.EXPORTS_DIR.exists()
    assert settings.PANELS_DIR.is_dir()
    assert settings.EXPORTS_DIR.is_dir()

    # Verify singleton behavior of get_settings
    another = get_settings()
    assert settings is another

    # Verify custom instantiation with custom base_dir
    custom_settings = Settings(base_dir=tmp_path, gemini_api_key="custom_gemini_key", dev_mock_ai=False)
    assert custom_settings.BASE_DIR == tmp_path
    assert custom_settings.GEMINI_API_KEY == "custom_gemini_key"
    assert custom_settings.DEV_MOCK_AI is False
    assert (tmp_path / "static" / "panels").exists()
    assert (tmp_path / "static" / "exports").exists()

    # Verify DEV_MOCK_AI is True when GEMINI_API_KEY is missing/empty
    empty_key_settings = Settings(base_dir=tmp_path, gemini_api_key="")
    assert empty_key_settings.DEV_MOCK_AI is True


def test_prompt_request_defaults_and_custom():
    """Test PromptRequest defaults, custom fields, and style alias support."""
    req_default = PromptRequest(prompt="A knight ventures into the dark caves.")
    assert req_default.prompt == "A knight ventures into the dark caves."
    assert req_default.character_name == "Hero"
    assert req_default.setting == "Enchanted Forest"
    assert req_default.tone == "Dramatic"
    assert req_default.art_style == "Classic Comic Book"

    req_custom = PromptRequest(
        prompt="A detective uncovers secrets.",
        character_name="Detective Miller",
        setting="Rainy Neo-Noir City",
        tone="Suspenseful",
        art_style="Manga",
    )
    assert req_custom.character_name == "Detective Miller"
    assert req_custom.setting == "Rainy Neo-Noir City"
    assert req_custom.tone == "Suspenseful"
    assert req_custom.art_style == "Manga"

    # Alias support for "style"
    req_alias = PromptRequest(prompt="Space wanderer", style="Retro Sci-Fi")
    assert req_alias.art_style == "Retro Sci-Fi"


def test_prompt_request_validation():
    """Test PromptRequest min_length=3 and required validation."""
    with pytest.raises(ValidationError):
        PromptRequest(prompt="")

    with pytest.raises(ValidationError):
        PromptRequest(prompt="ab")

    with pytest.raises(ValidationError):
        PromptRequest()


def test_panel_outline_and_story():
    """Test PanelOutline bounds and PanelStory fields."""
    outline = PanelOutline(
        panel=1,
        title="Opening Scene",
        scene_description="Hero wakes up on a strange planet",
        image_prompt="Hero awakening in red desert sand",
    )
    assert outline.panel == 1
    assert outline.title == "Opening Scene"

    # Panel must be between 1 and 5
    with pytest.raises(ValidationError):
        PanelOutline(
            panel=0,
            title="Invalid",
            scene_description="Desc",
            image_prompt="Prompt",
        )

    with pytest.raises(ValidationError):
        PanelOutline(
            panel=6,
            title="Invalid",
            scene_description="Desc",
            image_prompt="Prompt",
        )

    story = PanelStory(
        panel=1,
        caption="Day 1",
        narration="The air was thin.",
        dialogue="Where am I?",
    )
    assert story.panel == 1
    assert story.caption == "Day 1"
    assert story.narration == "The air was thin."
    assert story.dialogue == "Where am I?"


def test_comic_response_serialization():
    """Test ComicResponse and ComicPanel creation and serialization."""
    panel1 = ComicPanel(
        panel=1,
        title="Arrival",
        scene_description="Spaceship lands on alien planet",
        caption="Planet X",
        narration="Dust billowed across the barren landscape.",
        dialogue="Touchdown confirmed.",
        image_prompt="A spaceship landing on red dusty terrain, comic book art",
        image_path="static/panels/panel_1.png",
        image_url="/static/panels/panel_1.png",
    )
    panel2 = ComicPanel(
        panel=2,
        title="Exploration",
        scene_description="Hero steps out onto the dust",
        caption="First Contact",
        narration="Silence greeted the explorer.",
        dialogue="It's completely deserted.",
        image_prompt="Astronaut stepping out into barren landscape, comic book style",
        image_path="static/panels/panel_2.png",
        image_url="/static/panels/panel_2.png",
    )

    response = ComicResponse(
        story_title="Journey to Planet X",
        character_name="Captain Nova",
        setting="Planet X",
        tone="Sci-Fi Thriller",
        art_style="Classic Comic Book",
        layout=[panel1, panel2],
        pdf_url="/static/exports/comic_12345.pdf",
    )

    assert response.status == "success"
    assert response.story_title == "Journey to Planet X"
    assert len(response.layout) == 2
    assert response.layout[0].title == "Arrival"
    assert response.pdf_url == "/static/exports/comic_12345.pdf"

    # Serialization tests
    data = response.model_dump()
    assert data["status"] == "success"
    assert data["story_title"] == "Journey to Planet X"
    assert len(data["layout"]) == 2
    assert data["layout"][1]["dialogue"] == "It's completely deserted."

    json_data = response.model_dump_json()
    assert "Journey to Planet X" in json_data
    assert "Captain Nova" in json_data
