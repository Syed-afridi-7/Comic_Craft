"""Integration tests for ComicCraft FastAPI application and routes."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ComicResponse


@pytest.fixture
def client():
    """TestClient fixture with lifespan events active."""
    with TestClient(app) as test_client:
        yield test_client


def test_get_root(client):
    """Test GET / returns 200 and renders the index.html comic creation form."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    text = response.text

    # Verify form elements and expected branding
    assert "ComicCraft" in text
    assert '<form action="/generate" method="POST"' in text
    assert 'name="prompt"' in text
    assert 'name="character_name"' in text
    assert 'name="setting"' in text
    assert 'name="tone"' in text
    assert 'name="art_style"' in text
    assert "Generate 5-Panel Comic" in text


def test_post_generate_form(client):
    """Test POST /generate processes form submission, builds layout, and renders comic_preview.html."""
    form_data = {
        "prompt": "A brave space captain lands on an uncharted crystalline asteroid.",
        "character_name": "Captain Vega",
        "setting": "Deep Space & Asteroid Belt",
        "tone": "Dramatic",
        "art_style": "Classic Comic Book",
    }

    response = client.post("/generate", data=form_data)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    text = response.text

    # Verify metadata rendered in preview
    assert "Captain Vega" in text
    assert "Deep Space &amp; Asteroid Belt" in text or "Deep Space & Asteroid Belt" in text
    assert "Classic Comic Book" in text

    # Verify panels rendered
    assert "panel-card" in text
    assert "/static/panels/" in text

    # Verify PDF download CTA
    assert "Download Your Comic as PDF" in text
    assert "/static/exports/" in text
    assert ".pdf" in text
    assert "/export-success?pdf_path=" in text


def test_post_generate_comic_json(client):
    """Test POST /generate-comic/json returns 200 and a valid ComicResponse with 5 panels."""
    payload = {
        "prompt": "A cyber detective infiltrates the digital underworld of Neo-Shinjuku.",
        "character_name": "Detective Ren",
        "setting": "Cyberpunk Metropolis",
        "tone": "Dramatic",
        "art_style": "Graphic Novel Noir",
    }

    response = client.post("/generate-comic/json", json=payload)
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    data = response.json()
    comic = ComicResponse.model_validate(data)

    assert comic.status == "success"
    assert comic.character_name == "Detective Ren"
    assert comic.setting == "Cyberpunk Metropolis"
    assert comic.tone == "Dramatic"
    assert comic.art_style == "Graphic Novel Noir"
    assert comic.story_title != ""

    # Verify all 5 panels
    assert len(comic.layout) == 5
    for idx, panel in enumerate(comic.layout, start=1):
        assert panel.panel == idx
        assert panel.title != ""
        assert panel.image_url != ""
        assert "/static/panels/" in panel.image_url

    # Verify PDF export URL
    assert comic.pdf_url.startswith("/static/exports/")
    assert comic.pdf_url.endswith(".pdf")


def test_post_generate_comic_json_style_alias(client):
    """Test POST /generate-comic/json supports 'style' alias in request payload."""
    payload = {
        "prompt": "A young mage discovers an ancient talking tome in the library.",
        "character_name": "Lyra",
        "setting": "Ancient Dungeon Ruins",
        "tone": "Light-hearted & Adventurous",
        "style": "Anime",
    }

    response = client.post("/generate-comic/json", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["art_style"] == "Anime"
    assert len(data["layout"]) == 5


def test_get_test_image(client):
    """Test GET /test-image synthesizes a single panel image and returns JSON with image_url."""
    params = {
        "prompt": "A majestic golden dragon soaring over jagged snowy peaks",
        "art_style": "Classic Comic Book",
    }

    response = client.get("/test-image", params=params)
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    data = response.json()
    assert data["status"] == "success"
    assert data["prompt"] == params["prompt"]
    assert data["art_style"] == params["art_style"]
    assert data["image_url"].startswith("/static/panels/")
    assert data["image_url"].endswith(".png")


def test_get_export_success_default(client):
    """Test GET /export-success renders export_success.html with default pdf path."""
    response = client.get("/export-success")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    text = response.text

    assert "Comic Exported!" in text
    assert "/static/exports/comic.pdf" in text
    assert "Download Comic PDF" in text
    assert "Go Create Another Comic" in text


def test_get_export_success_custom_path(client):
    """Test GET /export-success renders export_success.html with custom pdf_path param."""
    custom_pdf = "/static/exports/comic_custom_9999.pdf"
    response = client.get("/export-success", params={"pdf_path": custom_pdf})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert custom_pdf in response.text


def test_post_generate_form_missing_prompt(client):
    """Test POST /generate without required prompt field fails validation with 422."""
    response = client.post("/generate", data={"character_name": "Hero"})
    assert response.status_code == 422


def test_post_generate_comic_json_invalid_length(client):
    """Test POST /generate-comic/json with prompt shorter than min_length=3 returns 422."""
    response = client.post("/generate-comic/json", json={"prompt": "hi"})
    assert response.status_code == 422


def test_get_test_image_missing_prompt(client):
    """Test GET /test-image without prompt query parameter returns 422."""
    response = client.get("/test-image")
    assert response.status_code == 422


def test_static_files_serving(client):
    """Test static file mount serves style.css from /static/css/style.css."""
    response = client.get("/static/css/style.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
    assert "--comic-bg" in response.text
