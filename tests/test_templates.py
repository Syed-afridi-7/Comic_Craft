import pytest
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


@pytest.fixture
def jinja_env():
    templates_dir = Path("templates")
    return Environment(loader=FileSystemLoader(str(templates_dir)))


def test_templates_exist_and_compile(jinja_env):
    """Verify that templates directory exists and templates compile without syntax errors."""
    for template_name in ["index.html", "comic_preview.html", "export_success.html"]:
        tmpl = jinja_env.get_template(template_name)
        assert tmpl is not None


def test_index_template_rendering(jinja_env):
    """Verify index.html renders required form elements, names, and spinner overlay."""
    tmpl = jinja_env.get_template("index.html")
    rendered = tmpl.render()

    assert "ComicCraft" in rendered
    assert "Comic Story Premise" in rendered or "prompt" in rendered
    assert 'action="/generate"' in rendered
    assert 'method="POST"' in rendered or 'method="post"' in rendered

    # Form field names
    assert 'name="prompt"' in rendered
    assert 'name="character_name"' in rendered
    assert 'name="setting"' in rendered
    assert 'name="tone"' in rendered
    assert 'name="art_style"' in rendered

    # Default character name
    assert 'value="Kael"' in rendered

    # Dropdown options
    for setting in [
        "Enchanted Forest",
        "Cyberpunk Metropolis",
        "Deep Space & Asteroid Belt",
        "Ancient Dungeon Ruins",
        "High School Campus",
    ]:
        assert setting in rendered

    for tone in [
        "Dramatic",
        "Funny & Humorous",
        "Light-hearted & Adventurous",
        "Poetic & Mysterious",
    ]:
        assert tone in rendered

    for style in [
        "Classic Comic Book",
        "Anime",
        "Pixel Art",
        "Graphic Novel Noir",
        "Realistic",
    ]:
        assert style in rendered

    # Loading spinner overlay
    assert 'id="spinner-overlay"' in rendered
    assert 'id="comic-form"' in rendered


def test_comic_preview_template_rendering(jinja_env):
    """Verify comic_preview.html renders all 5 panels, metadata, speech bubbles, and action buttons."""
    tmpl = jinja_env.get_template("comic_preview.html")

    layout = [
        {
            "panel": i,
            "title": f"Panel {i}: Scene {i}",
            "scene_description": f"Scene description for panel {i}",
            "caption": f"Caption text for panel {i}",
            "narration": f"Narrative text for panel {i}",
            "dialogue": f"Character {i}: 'Dialogue line {i}'",
            "image_url": f"/static/panels/panel_{i}.png",
            "image_prompt": f"Art prompt {i}",
        }
        for i in range(1, 6)
    ]

    story_metadata = {
        "title": "Chronicles of Kael",
        "character_name": "Kael",
        "setting": "Cyberpunk Metropolis",
        "tone": "Dramatic",
        "art_style": "Classic Comic Book",
    }
    pdf_url = "/static/exports/comic_12345.pdf"

    rendered = tmpl.render(
        layout=layout,
        story_metadata=story_metadata,
        pdf_url=pdf_url,
    )

    # Metadata checks
    assert "Chronicles of Kael" in rendered
    assert "Kael" in rendered
    assert "Cyberpunk Metropolis" in rendered
    assert "Dramatic" in rendered
    assert "Classic Comic Book" in rendered

    # PDF links and CTAs
    assert f'href="{pdf_url}"' in rendered
    assert "Download Your Comic as PDF" in rendered
    assert "Create Another" in rendered
    assert f"/export-success?pdf_path={pdf_url}" in rendered

    # All 5 panels
    for i in range(1, 6):
        assert f"Panel {i}: Scene {i}" in rendered
        assert f"/static/panels/panel_{i}.png" in rendered
        assert f"Scene description for panel {i}" in rendered
        assert f"Caption text for panel {i}" in rendered
        assert f"Narrative text for panel {i}" in rendered
        assert f"Character {i}: &#39;Dialogue line {i}&#39;" in rendered or f"Character {i}: 'Dialogue line {i}'" in rendered


def test_export_success_template_rendering(jinja_env):
    """Verify export_success.html renders confirmation, download link, and create another CTA."""
    tmpl = jinja_env.get_template("export_success.html")
    pdf_path = "/static/exports/comic_completed.pdf"
    rendered = tmpl.render(pdf_path=pdf_path)

    assert "Comic Exported!" in rendered
    assert f'href="{pdf_path}"' in rendered
    assert 'href="/"' in rendered
    assert "Go Create Another Comic" in rendered


def test_style_css_exists_and_contains_rules():
    """Verify static/css/style.css exists and defines the comic design system classes."""
    css_path = Path("static/css/style.css")
    assert css_path.exists(), "style.css must exist"

    content = css_path.read_text(encoding="utf-8")
    # Palette variables
    assert "--comic-bg" in content
    assert "--panel-bg" in content
    assert "--accent-red" in content
    assert "--accent-yellow" in content
    assert "--accent-cyan" in content

    # Component classes
    assert ".btn-comic" in content
    assert ".speech-bubble" in content
    assert ".panel-card" in content
    assert "#spinner-overlay" in content
    assert ".caption-box" in content
    assert ".panel-image" in content
