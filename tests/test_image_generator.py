import asyncio
import io
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image

from app.config import Settings
from app.schemas import PanelOutline
from app.ai.image_generator import (
    generate_image,
    generate_all_panels,
    _generate_fallback_image,
    STYLE_PALETTES,
)


@pytest.fixture
def sample_outline():
    return [
        {
            "panel": 1,
            "title": "Dawn of the Quest",
            "scene_description": "Hero gazes across the misty mountain range.",
            "image_prompt": "Classic Comic Book style, hero overlooking misty mountain range at sunrise.",
        },
        {
            "panel": 2,
            "title": "The Ancient Shrine",
            "scene_description": "Hero steps into the crumbling moss-covered shrine.",
            "image_prompt": "Classic Comic Book style, mysterious mossy stone shrine interior.",
        },
        {
            "panel": 3,
            "title": "Shadow Lurkers",
            "scene_description": "Crystalline shadow creatures emerge from the floor.",
            "image_prompt": "Classic Comic Book style, glowing obsidian beasts surrounding the hero.",
        },
        {
            "panel": 4,
            "title": "Spark of Magic",
            "scene_description": "Hero channels brilliant azure flame to hold them back.",
            "image_prompt": "Classic Comic Book style, intense azure magical blast pushing back shadows.",
        },
        {
            "panel": 5,
            "title": "Path Cleared",
            "scene_description": "Hero walks into the sunlight towards the temple gate.",
            "image_prompt": "Classic Comic Book style, triumphant hero striding towards majestic golden gates.",
        },
    ]


def test_generate_image_fallback_creates_valid_png(tmp_path):
    """Verify generate_image creates a valid 768x512 PNG file on disk in fallback/mock mode."""
    test_settings = Settings(
        base_dir=tmp_path,
        hf_api_key="",
        dev_mock_ai=True,
    )

    with patch("app.ai.image_generator.get_settings", return_value=test_settings):
        output_path_str = generate_image(
            prompt="A daring knight facing a giant clockwork dragon",
            panel_number=1,
            art_style="Classic Comic Book",
        )

    output_path = Path(output_path_str)
    assert output_path.exists()
    assert output_path.is_file()
    assert output_path.suffix.lower() == ".png"

    with Image.open(output_path) as img:
        assert img.format == "PNG"
        assert img.size == (768, 512)


def test_generate_image_custom_filename(tmp_path):
    """Verify generate_image respects an explicitly provided filename."""
    test_settings = Settings(
        base_dir=tmp_path,
        hf_api_key="",
        dev_mock_ai=True,
    )
    custom_name = "custom_panel_special_42.png"

    with patch("app.ai.image_generator.get_settings", return_value=test_settings):
        output_path_str = generate_image(
            prompt="Futuristic city with flying speeders",
            panel_number=2,
            art_style="Pixel Art",
            filename=custom_name,
        )

    output_path = Path(output_path_str)
    assert output_path.exists()
    assert output_path.name == custom_name
    assert output_path.parent == test_settings.PANELS_DIR

    with Image.open(output_path) as img:
        assert img.size == (768, 512)


def test_generate_image_style_palettes_applied(tmp_path):
    """Verify _generate_fallback_image handles all standard style palettes cleanly."""
    test_settings = Settings(base_dir=tmp_path)

    for idx, style in enumerate(
        ["Classic Comic Book", "Anime", "Pixel Art", "Realistic", "Graphic Novel Noir", "Unknown Novel"]
    ):
        file_path = test_settings.PANELS_DIR / f"test_style_{idx}.png"
        _generate_fallback_image(
            prompt=f"Testing art style rendering for {style}",
            panel_number=idx + 1,
            art_style=style,
            output_path=file_path,
        )
        assert file_path.exists()
        with Image.open(file_path) as img:
            assert img.size == (768, 512)
            assert img.mode in ("RGB", "RGBA")


def test_generate_image_hf_api_success(tmp_path):
    """Verify generate_image calls Hugging Face API when key is present and dev_mock_ai is False."""
    test_settings = Settings(
        base_dir=tmp_path,
        hf_api_key="hf_test_valid_token_12345",
        dev_mock_ai=False,
    )

    # Prepare a valid mock image byte stream
    mock_img = Image.new("RGB", (768, 512), color=(20, 80, 160))
    img_byte_arr = io.BytesIO()
    mock_img.save(img_byte_arr, format="PNG")
    mock_bytes = img_byte_arr.getvalue()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = mock_bytes

    with patch("app.ai.image_generator.get_settings", return_value=test_settings):
        with patch("requests.post", return_value=mock_response) as mock_post:
            output_path_str = generate_image(
                prompt="Cyberpunk warrior in neon alleyway",
                panel_number=3,
                art_style="Anime",
            )

    output_path = Path(output_path_str)
    assert output_path.exists()
    mock_post.assert_called_once()
    called_url = mock_post.call_args[0][0]
    called_headers = mock_post.call_args[1].get("headers", {})
    called_json = mock_post.call_args[1].get("json", {})

    assert "huggingface.co" in called_url
    assert called_headers.get("Authorization") == "Bearer hf_test_valid_token_12345"
    assert "Anime style" in called_json.get("inputs", "")
    assert "Cyberpunk warrior" in called_json.get("inputs", "")

    with Image.open(output_path) as img:
        assert img.size == (768, 512)


def test_generate_image_hf_api_failure_fallback(tmp_path):
    """Verify generate_image falls back to Pillow fallback generator when HF API fails or raises error."""
    test_settings = Settings(
        base_dir=tmp_path,
        hf_api_key="hf_token_that_will_fail",
        dev_mock_ai=False,
    )

    # 1. Test when requests.post raises network exception
    with patch("app.ai.image_generator.get_settings", return_value=test_settings):
        with patch("requests.post", side_effect=RuntimeError("HF Network Connection Error")):
            output_path_str = generate_image(
                prompt="Mystic wizard casting lightning",
                panel_number=4,
                art_style="Graphic Novel Noir",
            )

    output_path = Path(output_path_str)
    assert output_path.exists()
    with Image.open(output_path) as img:
        assert img.size == (768, 512)

    # 2. Test when requests.post returns 503 Service Unavailable / Model Loading
    mock_503 = MagicMock()
    mock_503.status_code = 503
    mock_503.content = b'{"error": "Model runwayml/stable-diffusion-v1-5 is currently loading"}'

    with patch("app.ai.image_generator.get_settings", return_value=test_settings):
        with patch("requests.post", return_value=mock_503):
            output_path_str_503 = generate_image(
                prompt="Steampunk airship flying into thunderstorm",
                panel_number=5,
                art_style="Classic Comic Book",
            )

    output_path_503 = Path(output_path_str_503)
    assert output_path_503.exists()
    with Image.open(output_path_503) as img:
        assert img.size == (768, 512)


def test_generate_all_panels_concurrent(tmp_path, sample_outline):
    """Verify generate_all_panels generates 5 valid panel images concurrently."""
    test_settings = Settings(
        base_dir=tmp_path,
        hf_api_key="",
        dev_mock_ai=True,
    )

    with patch("app.ai.image_generator.get_settings", return_value=test_settings):
        paths = asyncio.run(
            generate_all_panels(
                outline=sample_outline,
                art_style="Classic Comic Book",
            )
        )

    assert isinstance(paths, list)
    assert len(paths) == 5

    for idx, path_str in enumerate(paths, start=1):
        p = Path(path_str)
        assert p.exists()
        assert p.suffix.lower() == ".png"
        with Image.open(p) as img:
            assert img.size == (768, 512)


def test_generate_all_panels_with_pydantic_models(tmp_path):
    """Verify generate_all_panels also accepts Pydantic PanelOutline instances."""
    test_settings = Settings(
        base_dir=tmp_path,
        hf_api_key="",
        dev_mock_ai=True,
    )

    pydantic_outline = [
        PanelOutline(
            panel=i,
            title=f"Scene {i}",
            scene_description=f"Description for scene {i}",
            image_prompt=f"Vivid artwork for panel {i}",
        )
        for i in range(1, 6)
    ]

    with patch("app.ai.image_generator.get_settings", return_value=test_settings):
        paths = asyncio.run(
            generate_all_panels(
                outline=pydantic_outline,
                art_style="Anime",
            )
        )

    assert len(paths) == 5
    for path_str in paths:
        assert Path(path_str).exists()
