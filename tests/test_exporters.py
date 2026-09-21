"""Tests for ComicCraft PDF exporter service."""

import re
from pathlib import Path
from unittest.mock import patch
import pytest
from PIL import Image
from fpdf import FPDF

from app.config import Settings
from app.schemas import ComicPanel
from app.services.exporters import ComicPDF, _clean_text, save_pdf


@pytest.fixture
def test_settings(tmp_path):
    """Provide isolated Settings pointing to tmp_path."""
    return Settings(
        base_dir=tmp_path,
        gemini_api_key="",
        hf_api_key="",
        dev_mock_ai=True,
    )


@pytest.fixture
def sample_metadata():
    return {
        "title": "Rise of the Cyber Knight",
        "character_name": "Valerius",
        "setting": "Neo-Veridia Megacity",
        "tone": "Cyberpunk Noir",
        "art_style": "Classic Comic Book",
    }


@pytest.fixture
def sample_image_files(tmp_path):
    """Generate 5 dummy PNG images for testing PDF embedding."""
    images_dir = tmp_path / "test_panels"
    images_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(1, 6):
        img_path = images_dir / f"panel_{i}.png"
        img = Image.new("RGB", (768, 512), color=(30 * i, 40 * i, 50 * i))
        img.save(img_path)
        paths.append(str(img_path))
    return paths


@pytest.fixture
def sample_layout(sample_image_files):
    return [
        {
            "panel": 1,
            "title": "Neon Awakening",
            "scene_description": "Valerius awakens atop a rain-soaked skyscraper.",
            "caption": "Rain slants across neon-drenched spires.",
            "narration": "In Neo-Veridia, memory is a commodity.",
            "dialogue": "Valerius: The core is destabilizing.",
            "image_prompt": "Cyberpunk hero on a rainy rooftop.",
            "image_path": sample_image_files[0],
            "image_url": "/static/panels/panel_1.png",
        },
        {
            "panel": 2,
            "title": "The Cipher Decoded",
            "scene_description": "A glowing holographic tablet projects encrypted code.",
            "caption": "Fragments of ancient protocol flicker.",
            "narration": "Every sector was locked down by the Syndicate.",
            "dialogue": "Valerius: I have thirty seconds before the trace locks.",
            "image_prompt": "Glowing holographic code in dark room.",
            "image_path": sample_image_files[1],
            "image_url": "/static/panels/panel_2.png",
        },
        {
            "panel": 3,
            "title": "Ambush in Sector 7",
            "scene_description": "Chrome drones descend with crimson optical sensors.",
            "caption": "Whirring rotor blades slice the smog.",
            "narration": "They knew he was coming.",
            "dialogue": "Syndicate Drone: Target acquired. Neutralize.",
            "image_prompt": "Chrome attack drones in alleyway.",
            "image_path": sample_image_files[2],
            "image_url": "/static/panels/panel_3.png",
        },
        {
            "panel": 4,
            "title": "Overclocked Strike",
            "scene_description": "Valerius unleashes an EMP pulse from his cybernetic arm.",
            "caption": "Blue electricity erupts.",
            "narration": "One discharge depleted his remaining energy reserves.",
            "dialogue": "Valerius: Not today.",
            "image_prompt": "Hero releasing explosive electric blast.",
            "image_path": sample_image_files[3],
            "image_url": "/static/panels/panel_4.png",
        },
        {
            "panel": 5,
            "title": "Dawn Over the Spire",
            "scene_description": "The morning sun cuts through clouds as Valerius stands victorious.",
            "caption": "The broadcast signal transmits across the city.",
            "narration": "The truth could no longer be erased.",
            "dialogue": "Valerius: Tell them the revolution has begun.",
            "image_prompt": "Hero standing against golden morning city sunrise.",
            "image_path": sample_image_files[4],
            "image_url": "/static/panels/panel_5.png",
        },
    ]


def test_clean_text_substitutions():
    """Verify _clean_text converts smart quotes, dashes, ellipses, and unencodables."""
    assert _clean_text(None) == ""
    assert _clean_text("") == ""
    assert _clean_text(123) == "123"

    # Smart quotes and apostrophes
    smart_quotes = "\u201cDouble Quotes\u201d and \u2018Single Quotes\u2019"
    cleaned_quotes = _clean_text(smart_quotes)
    assert '"Double Quotes"' in cleaned_quotes
    assert "'Single Quotes'" in cleaned_quotes

    # Em-dash, en-dash, ellipsis
    punct = "Start\u2014Middle\u2013End\u2026"
    cleaned_punct = _clean_text(punct)
    assert " -- " in cleaned_punct
    assert " - " in cleaned_punct
    assert "..." in cleaned_punct

    # Accents valid in Latin-1
    french = "Caf\u00e9 au lait \u00e0 Paris"
    assert _clean_text(french) == french

    # Emojis and characters outside Latin-1
    emoji_str = "Hero \U0001F600 wins \u2728"
    cleaned_emoji = _clean_text(emoji_str)
    # Shouldn't crash and shouldn't contain the raw high-unicode points
    assert "\U0001F600" not in cleaned_emoji


def test_comic_pdf_subclass():
    """Verify ComicPDF subclass initializes and configures custom footer."""
    pdf = ComicPDF()
    assert isinstance(pdf, FPDF)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(text="Hello ComicCraft")
    raw_pdf = pdf.output()
    assert len(raw_pdf) > 0
    assert raw_pdf.startswith(b"%PDF-")


def test_save_pdf_with_valid_layout_and_images(test_settings, sample_layout, sample_metadata):
    """Verify complete PDF export with cover page, panel artwork, and proper metadata."""
    with patch("app.services.exporters.get_settings", return_value=test_settings):
        pdf_url = save_pdf(sample_layout, sample_metadata)

    assert isinstance(pdf_url, str)
    assert pdf_url.startswith("/static/exports/")
    assert pdf_url.endswith(".pdf")

    filename = Path(pdf_url).name
    pdf_path = test_settings.EXPORTS_DIR / filename

    assert pdf_path.exists()
    file_size = pdf_path.stat().st_size
    assert file_size > 1024, f"Expected file size > 1KB, got {file_size}"

    with open(pdf_path, "rb") as f:
        header = f.read(10)
        assert header.startswith(b"%PDF-")
        f.seek(0)
        content = f.read()

    # 1 cover page + 5 panel pages = 6 pages total
    page_count = len(re.findall(rb"/Type\s*/Page\b", content))
    assert page_count == 6, f"Expected 6 pages, found {page_count}"


def test_save_pdf_unicode_resilience(test_settings, sample_image_files):
    """Verify PDF export does not crash when metadata or panels contain special unicode."""
    unicode_metadata = {
        "title": "L\u2019Aventure du \u201cChevalier\u201d \u2014 L\u2019\u00c9p\u00e9e d\u2019Or\u2026",
        "character_name": "Ren\u00e9e \u201cShadow\u201d \u2605",
        "setting": "Ch\u00e2teau de Lumi\u00e8re \U0001F3F0",
        "tone": "Po\u00e9tique & Sombre \u2014 \u00abDramatic\u00bb",
        "art_style": "Classic Comic \u2022 Noir",
    }

    unicode_layout = [
        {
            "panel": 1,
            "title": "L\u2019\u00c9veil \u2014 \u201cBeginnings\u201d",
            "scene_description": "H\u00e9ros regarde la vall\u00e9e\u2026",
            "caption": "\u00abDans l\u2019ombre de la nuit\u2026\u00bb",
            "narration": "Il n\u2019y avait plus d\u2019espoir \u2014 ou presque.",
            "dialogue": "Ren\u00e9e: \u201cNous devons agir maintenant!\u201d \U0001F525",
            "image_prompt": "Hero in French castle.",
            "image_path": sample_image_files[0],
            "image_url": "/static/panels/panel_1.png",
        }
    ]

    with patch("app.services.exporters.get_settings", return_value=test_settings):
        pdf_url = save_pdf(unicode_layout, unicode_metadata)

    pdf_path = test_settings.EXPORTS_DIR / Path(pdf_url).name
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1024


def test_save_pdf_missing_images_graceful(test_settings, sample_metadata):
    """Verify PDF export handles missing, invalid, or empty image paths without crashing."""
    layout_with_missing_images = [
        {
            "panel": 1,
            "title": "Ghost Panel",
            "scene_description": "Artwork missing.",
            "caption": "A missing image placeholder.",
            "narration": "The world remained unseen.",
            "dialogue": "Hero: Where is the picture?",
            "image_prompt": "Missing image.",
            "image_path": "/non/existent/path/does_not_exist.png",
            "image_url": "/static/panels/missing.png",
        },
        {
            "panel": 2,
            "title": "Empty Path Panel",
            "scene_description": "Path is empty string.",
            "caption": "Nothing to display.",
            "narration": "Silence fell.",
            "dialogue": "Hero: Darkness everywhere.",
            "image_prompt": "Empty path.",
            "image_path": "",
            "image_url": "",
        },
        {
            "panel": 3,
            "title": "None Path Panel",
            "scene_description": "Path is None.",
            "caption": "",
            "narration": "",
            "dialogue": "",
            "image_prompt": "None path.",
            "image_path": None,
            "image_url": None,
        },
    ]

    with patch("app.services.exporters.get_settings", return_value=test_settings):
        pdf_url = save_pdf(layout_with_missing_images, sample_metadata)

    pdf_path = test_settings.EXPORTS_DIR / Path(pdf_url).name
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1024

    with open(pdf_path, "rb") as f:
        content = f.read()
    # 1 cover + 3 panel pages = 4 pages
    page_count = len(re.findall(rb"/Type\s*/Page\b", content))
    assert page_count == 4


def test_save_pdf_metadata_defaults(test_settings, sample_layout):
    """Verify save_pdf works with None and empty metadata dictionaries."""
    with patch("app.services.exporters.get_settings", return_value=test_settings):
        pdf_url_none = save_pdf(sample_layout, None)
        pdf_url_empty = save_pdf(sample_layout, {})

    assert Path(test_settings.EXPORTS_DIR / Path(pdf_url_none).name).exists()
    assert Path(test_settings.EXPORTS_DIR / Path(pdf_url_empty).name).exists()


def test_save_pdf_empty_layout(test_settings, sample_metadata):
    """Verify empty layout produces a single cover page PDF."""
    with patch("app.services.exporters.get_settings", return_value=test_settings):
        pdf_url = save_pdf([], sample_metadata)

    pdf_path = test_settings.EXPORTS_DIR / Path(pdf_url).name
    assert pdf_path.exists()
    with open(pdf_path, "rb") as f:
        content = f.read()
    page_count = len(re.findall(rb"/Type\s*/Page\b", content))
    assert page_count == 1


def test_save_pdf_with_pydantic_models(test_settings, sample_layout, sample_metadata):
    """Verify save_pdf handles Pydantic ComicPanel objects directly."""
    pydantic_layout = [ComicPanel(**p) for p in sample_layout]

    with patch("app.services.exporters.get_settings", return_value=test_settings):
        pdf_url = save_pdf(pydantic_layout, sample_metadata)

    pdf_path = test_settings.EXPORTS_DIR / Path(pdf_url).name
    assert pdf_path.exists()
    with open(pdf_path, "rb") as f:
        content = f.read()
    page_count = len(re.findall(rb"/Type\s*/Page\b", content))
    assert page_count == 6
