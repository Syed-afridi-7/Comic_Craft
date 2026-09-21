# ComicCraft Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy ComicCraft, an end-to-end FastAPI generative AI web platform that transforms user story prompts into cohesive 5-panel comic books with illustrations, dialogue, captions, responsive web viewer, and downloadable multi-page PDFs.

**Architecture:** A modular Python backend where FastAPI coordinates an AI pipeline consisting of Google Gemini 1.5 Flash for 5-panel structured outlines, Google Gemini 1.5 Pro for rich dialogue and narration, and Hugging Face Serverless Stable Diffusion with concurrent thread-pool execution and resilient local placeholder fallbacks for artwork. Business services aggregate panels and compile them into multi-page PDF documents via FPDF, rendered dynamically through Jinja2 templates and modern comic-style CSS.

**Tech Stack:** Python 3, FastAPI, Uvicorn, Pydantic v2, Google Generative AI (`google-generativeai`), Hugging Face / Requests / HTTPX, FPDF2 (`fpdf2`), Pillow (`PIL`), Jinja2, Pytest, Python-Multipart.

**Spec:** [`docs/superpowers/specs/2026-09-21-comiccraft-design.md`](file:///D:/Comic_Craft/docs/superpowers/specs/2026-09-21-comiccraft-design.md)

## Global Constraints

- Must match the exact directory structure and module roles defined in [`technical_guide.md.md`](file:///D:/Comic_Craft/technical_guide.md.md).
- Must run reliably across both offline/test environments (using deterministic mock fallbacks) and production environments with valid `GEMINI_API_KEY` and `HF_API_KEY`.
- Image generation for all 5 panels must execute concurrently using parallel workers to avoid slow sequential response times.
- PDF generation must handle custom formatting, unicode/special characters, panel headers, and image embedding without crashing.
- Every task must follow strict Test-Driven Development (TDD) with automated verification before committing.

---

### Task 1: Scaffolding, Configuration, and Data Schemas

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `app/schemas.py`
- Test: `tests/test_config_and_schemas.py`

**Interfaces:**
- Consumes: Environment variables (`GEMINI_API_KEY`, `HF_API_KEY`, `DEV_MOCK_AI`)
- Produces: `settings` singleton from `app.config`, Pydantic models `PromptRequest`, `PanelOutline`, `PanelStory`, `ComicPanel`, `ComicResponse` from `app.schemas`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config_and_schemas.py
import pytest
from app.config import Settings, get_settings
from app.schemas import PromptRequest, PanelOutline, ComicPanel, ComicResponse

def test_settings_initialization():
    settings = get_settings()
    assert hasattr(settings, "GEMINI_API_KEY")
    assert hasattr(settings, "HF_API_KEY")
    assert settings.PANELS_DIR.exists()
    assert settings.EXPORTS_DIR.exists()

def test_prompt_request_schema():
    req = PromptRequest(
        prompt="A brave knight exploring a cursed dungeon",
        character_name="Arthur",
        setting="Dungeon",
        tone="Dramatic",
        art_style="Comic Book"
    )
    assert req.character_name == "Arthur"
    assert req.setting == "Dungeon"

def test_prompt_request_validation():
    with pytest.raises(ValueError):
        PromptRequest(prompt="")  # min_length validation

def test_comic_response_schema():
    panel = ComicPanel(
        panel=1,
        title="The Gate",
        scene_description="Arthur arrives at the dungeon gate.",
        caption="Night falls on the dungeon.",
        narration="Arthur adjusted his heavy shield.",
        dialogue="Arthur: 'Here begins the trial.'",
        image_prompt="A knight at the iron gate of a gothic dungeon",
        image_path="static/panels/test.png",
        image_url="/static/panels/test.png"
    )
    resp = ComicResponse(
        story_title="The Cursed Dungeon",
        character_name="Arthur",
        setting="Dungeon",
        tone="Dramatic",
        art_style="Comic Book",
        layout=[panel],
        pdf_url="/static/exports/comic_test.pdf"
    )
    assert resp.status == "success"
    assert len(resp.layout) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_and_schemas.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'app')

- [ ] **Step 3: Write minimal implementation**

Create `requirements.txt`:
```text
fastapi>=0.110.0
uvicorn>=0.28.0
jinja2>=3.1.3
python-multipart>=0.0.9
google-generativeai>=0.5.0
fpdf2>=2.7.8
pillow>=10.2.0
requests>=2.31.0
httpx>=0.27.0
python-dotenv>=1.0.1
pydantic>=2.6.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

Create `.env.example`:
```text
GEMINI_API_KEY=your_gemini_api_key_here
HF_API_KEY=your_huggingface_api_key_here
DEV_MOCK_AI=true
```

Create `.gitignore`:
```text
__pycache__/
*.pyc
env/
venv/
.env
static/panels/*.png
static/panels/*.jpg
static/exports/*.pdf
!static/panels/.gitkeep
!static/exports/.gitkeep
.pytest_cache/
```

Create `app/__init__.py`:
```python
"""ComicCraft Application Package."""
```

Create `app/config.py`:
```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
        self.HF_API_KEY = os.getenv("HF_API_KEY", "").strip()
        
        # Enable mock AI if key is missing or explicitly enabled
        mock_env = os.getenv("DEV_MOCK_AI", "").lower()
        self.DEV_MOCK_AI = mock_env in ("true", "1", "yes") or not bool(self.GEMINI_API_KEY)
        
        self.STATIC_DIR = self.BASE_DIR / "static"
        self.PANELS_DIR = self.STATIC_DIR / "panels"
        self.EXPORTS_DIR = self.STATIC_DIR / "exports"
        
        # Ensure media directories exist
        self.PANELS_DIR.mkdir(parents=True, exist_ok=True)
        self.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

_settings_instance = None

def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
```

Create `app/schemas.py`:
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=3, description="Main storyline premise")
    character_name: str = Field(default="Hero", description="Main character name")
    setting: str = Field(default="Enchanted Forest", description="Story environment")
    tone: str = Field(default="Dramatic", description="Mood of the story")
    art_style: str = Field(default="Classic Comic Book", description="Visual style")

class PanelOutline(BaseModel):
    panel: int = Field(..., ge=1, le=5)
    title: str
    scene_description: str
    image_prompt: str

class PanelStory(BaseModel):
    panel: int
    caption: str
    narration: str
    dialogue: str

class ComicPanel(BaseModel):
    panel: int
    title: str
    scene_description: str
    caption: str
    narration: str
    dialogue: str
    image_prompt: str
    image_path: str
    image_url: str

class ComicResponse(BaseModel):
    status: str = "success"
    story_title: str
    character_name: str
    setting: str
    tone: str
    art_style: str
    layout: List[ComicPanel]
    pdf_url: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config_and_schemas.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example .gitignore app/config.py app/schemas.py tests/test_config_and_schemas.py
git commit -m "feat(core): add scaffolding, configuration and pydantic data schemas"
```

---

### Task 2: Gemini Client & Resilient Outline Generation (`gemini_client.py` & `gemini_flash.py`)

**Files:**
- Create: `app/ai/__init__.py`
- Create: `app/ai/gemini_client.py`
- Create: `app/ai/gemini_flash.py`
- Test: `tests/test_gemini_flash.py`

**Interfaces:**
- Consumes: `Settings` from `app.config`
- Produces: `generate_outline(user_prompt: str, character_name: str, setting: str, tone: str, art_style: str) -> List[dict]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gemini_flash.py
import pytest
from app.ai.gemini_flash import generate_outline

def test_generate_outline_structure():
    outline = generate_outline(
        user_prompt="A clever fox searching for the lost star relic",
        character_name="Vulpix",
        setting="Enchanted Forest",
        tone="Adventurous",
        art_style="Classic Comic Book"
    )
    assert isinstance(outline, list)
    assert len(outline) == 5
    for idx, item in enumerate(outline, 1):
        assert item["panel"] == idx
        assert "title" in item and len(item["title"]) > 0
        assert "scene_description" in item and len(item["scene_description"]) > 0
        assert "image_prompt" in item and len(item["image_prompt"]) > 0
        assert "Classic Comic Book" in item["image_prompt"] or "comic" in item["image_prompt"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_gemini_flash.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'app.ai.gemini_flash')

- [ ] **Step 3: Write minimal implementation**

Create `app/ai/__init__.py`:
```python
"""AI orchestration package for ComicCraft."""
```

Create `app/ai/gemini_client.py`:
```python
from app.config import get_settings

def configure_gemini():
    settings = get_settings()
    if settings.GEMINI_API_KEY and not settings.DEV_MOCK_AI:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            return genai
        except Exception as e:
            print(f"Failed to configure Gemini SDK: {e}")
            return None
    return None
```

Create `app/ai/gemini_flash.py`:
```python
import json
import re
from typing import List, Dict, Any
from app.config import get_settings
from app.ai.gemini_client import configure_gemini

def _get_mock_outline(user_prompt: str, character_name: str, setting: str, tone: str, art_style: str) -> List[Dict[str, Any]]:
    return [
        {
            "panel": 1,
            "title": f"Panel 1: The Call to {setting}",
            "scene_description": f"{character_name} stands poised at the threshold of {setting}, clutching an ancient parchment under a heavy sky.",
            "image_prompt": f"Wide comic panel shot, {character_name} in {setting}, looking out towards the horizon, {art_style}, detailed ink and color, cinematic."
        },
        {
            "panel": 2,
            "title": "Panel 2: Signs of the Unknown",
            "scene_description": f"Deeper into the {setting}, {character_name} uncovers strange glowing glyphs pulsating with mysterious energy.",
            "image_prompt": f"Medium angle comic panel, {character_name} examining glowing symbols in {setting}, {tone} atmosphere, {art_style}, dynamic lighting."
        },
        {
            "panel": 3,
            "title": "Panel 3: The Gathering Storm",
            "scene_description": f"An unexpected challenge arises in the {setting}, putting {character_name}'s resolve to the ultimate test.",
            "image_prompt": f"Dramatic low angle comic illustration, confrontation in {setting}, {character_name} standing firm, {art_style}, bold comic shadows."
        },
        {
            "panel": 4,
            "title": "Panel 4: The Decisive Moment",
            "scene_description": f"Summoning courage, {character_name} makes a daring move to overcome the greatest obstacle.",
            "image_prompt": f"Action close-up comic panel, high intensity, {character_name} in action within {setting}, {art_style}, dynamic action lines."
        },
        {
            "panel": 5,
            "title": "Panel 5: Dawn of a New Legend",
            "scene_description": f"The challenge resolved, {character_name} gazes toward the bright morning sun breaking over the {setting}.",
            "image_prompt": f"Inspiring wide establishing comic panel, triumph in {setting}, {character_name} victorious, warm golden glow, {art_style}, masterpiece."
        }
    ]

def generate_outline(user_prompt: str, character_name: str = "Hero", setting: str = "Enchanted Forest", tone: str = "Dramatic", art_style: str = "Classic Comic Book") -> List[Dict[str, Any]]:
    settings = get_settings()
    genai = configure_gemini()
    
    if not genai or settings.DEV_MOCK_AI:
        return _get_mock_outline(user_prompt, character_name, setting, tone, art_style)
        
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt_instruction = f"""
You are an expert comic book editor and storyboard architect.
Create a structured 5-panel comic storyline outline based on:
- Premise: {user_prompt}
- Hero/Character: {character_name}
- Setting: {setting}
- Tone: {tone}
- Art Style: {art_style}

Follow classic 5-panel dramatic structure:
Panel 1: Setup & Introduction
Panel 2: Inciting Incident / Discovery
Panel 3: Escalation / Conflict
Panel 4: Climax / Decisive Action
Panel 5: Resolution & Aftermath

Return strictly a JSON array containing exactly 5 objects. Each object must contain:
- panel: integer (1 to 5)
- title: concise title string
- scene_description: 1-2 sentence atmospheric description
- image_prompt: rich visual description formatted for Stable Diffusion image generation incorporating the art style '{art_style}'
"""
        response = model.generate_content(
            prompt_instruction,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        if isinstance(data, list) and len(data) == 5:
            return data
        elif isinstance(data, dict) and "panels" in data and len(data["panels"]) == 5:
            return data["panels"]
    except Exception as e:
        print(f"Gemini Flash outline generation fallback: {e}")
        
    return _get_mock_outline(user_prompt, character_name, setting, tone, art_style)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_gemini_flash.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add app/ai/__init__.py app/ai/gemini_client.py app/ai/gemini_flash.py tests/test_gemini_flash.py
git commit -m "feat(ai): implement Gemini Flash outline generator with mock fallback"
```

---

### Task 3: Narrative Expansion & Dialogue Generation (`gemini_pro.py`)

**Files:**
- Create: `app/ai/gemini_pro.py`
- Test: `tests/test_gemini_pro.py`

**Interfaces:**
- Consumes: 5-panel outline list from `gemini_flash.generate_outline`
- Produces: `generate_story(outline: List[dict], character_name: str, tone: str) -> List[dict]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gemini_pro.py
import pytest
from app.ai.gemini_pro import generate_story

def test_generate_story_expansion():
    mock_outline = [
        {"panel": i, "title": f"Panel {i}", "scene_description": f"Scene {i}", "image_prompt": f"Prompt {i}"}
        for i in range(1, 6)
    ]
    story_panels = generate_story(
        outline=mock_outline,
        character_name="Kaelen",
        tone="Dramatic"
    )
    assert isinstance(story_panels, list)
    assert len(story_panels) == 5
    for item in story_panels:
        assert "panel" in item
        assert "caption" in item and len(item["caption"]) > 0
        assert "narration" in item and len(item["narration"]) > 0
        assert "dialogue" in item and len(item["dialogue"]) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_gemini_pro.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'app.ai.gemini_pro')

- [ ] **Step 3: Write minimal implementation**

Create `app/ai/gemini_pro.py`:
```python
import json
from typing import List, Dict, Any
from app.config import get_settings
from app.ai.gemini_client import configure_gemini

def _get_mock_story(outline: List[Dict[str, Any]], character_name: str, tone: str) -> List[Dict[str, Any]]:
    story = []
    templates = [
        ("The shadows lengthen across the ancient path.", f"{character_name} checked the map once more, measuring each breath against the silence.", f"{character_name}: 'The journey begins here, no matter the cost.'"),
        ("A sudden hum resonates through the damp air.", f"Curiosity won over fear as {character_name} stepped toward the pulsating glow.", f"{character_name}: 'These ruins... they are awake.'"),
        ("Wind howls as thunder cracks open the horizon.", f"The air turned freezing cold, signaling that they were not alone.", f"{character_name}: 'Show yourself! I'm not turning back!'"),
        ("A blinding flash tears through the confrontation.", f"With swift precision, {character_name} unleashed everything they had learned.", f"{character_name}: 'This ends now!'"),
        ("Golden light bathes the quiet horizon.", f"The trials had ended, leaving behind a hard-won peace.", f"{character_name}: 'We survived... and the story will continue.'")
    ]
    for idx, panel in enumerate(outline):
        p_num = panel.get("panel", idx + 1)
        cap, narr, dial = templates[min(idx, len(templates) - 1)]
        story.append({
            "panel": p_num,
            "caption": cap,
            "narration": narr,
            "dialogue": dial
        })
    return story

def generate_story(outline: List[Dict[str, Any]], character_name: str = "Hero", tone: str = "Dramatic") -> List[Dict[str, Any]]:
    settings = get_settings()
    genai = configure_gemini()
    
    if not genai or settings.DEV_MOCK_AI:
        return _get_mock_story(outline, character_name, tone)
        
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        prompt = f"""
You are an award-winning comic book writer.
Expand this 5-panel comic storyboard outline into compelling script elements for each panel:
Hero: {character_name}
Tone: {tone}

Outline:
{json.dumps(outline, indent=2)}

For each of the 5 panels, write:
1. 'caption': A brief 1-sentence ambient or scene-setting caption.
2. 'narration': 1-2 sentences of gripping storytelling prose.
3. 'dialogue': A line of direct character speech in comic format (e.g. "{character_name}: '...'").

Return strictly a JSON array with 5 objects containing:
panel (int), caption (str), narration (str), dialogue (str).
"""
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        if isinstance(data, list) and len(data) == 5:
            return data
        elif isinstance(data, dict) and "panels" in data:
            return data["panels"]
    except Exception as e:
        print(f"Gemini Pro story expansion fallback: {e}")
        
    return _get_mock_story(outline, character_name, tone)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_gemini_pro.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add app/ai/gemini_pro.py tests/test_gemini_pro.py
git commit -m "feat(ai): implement Gemini Pro narrative expansion with character dialogue"
```

---

### Task 4: Artwork Synthesis & Concurrent Panel Generation (`image_generator.py`)

**Files:**
- Create: `app/ai/image_generator.py`
- Test: `tests/test_image_generator.py`

**Interfaces:**
- Consumes: Prompts from outline, `HF_API_KEY` or fallback
- Produces: `generate_image(prompt: str, panel_number: int, art_style: str) -> str` and `generate_all_panels(outline: List[dict], art_style: str) -> List[str]` returning local file paths.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_image_generator.py
import pytest
from pathlib import Path
from app.ai.image_generator import generate_image, generate_all_panels

def test_generate_single_image():
    path_str = generate_image(
        prompt="A brave fox running in forest",
        panel_number=1,
        art_style="Anime"
    )
    assert Path(path_str).exists()
    assert path_str.endswith(".png")

@pytest.mark.asyncio
async def test_generate_all_panels_concurrently():
    mock_outline = [
        {"panel": i, "image_prompt": f"Test scene {i}", "title": f"Panel {i}"}
        for i in range(1, 6)
    ]
    paths = await generate_all_panels(mock_outline, art_style="Classic Comic Book")
    assert len(paths) == 5
    for p in paths:
        assert Path(p).exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_image_generator.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'app.ai.image_generator')

- [ ] **Step 3: Write minimal implementation**

Create `app/ai/image_generator.py`:
```python
import os
import time
import asyncio
import requests
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image, ImageDraw, ImageFont
from app.config import get_settings

def _generate_fallback_image(prompt: str, panel_number: int, art_style: str, output_path: Path):
    """Creates a stylized comic placeholder image using Pillow."""
    width, height = 768, 512
    # Style palette mapping
    palettes = {
        "Anime": ((41, 50, 60), (255, 107, 107), (78, 205, 196)),
        "Classic Comic Book": ((26, 26, 46), (233, 69, 96), (242, 222, 102)),
        "Pixel Art": ((32, 24, 46), (138, 201, 38), (25, 130, 196)),
        "Realistic": ((33, 37, 41), (108, 117, 125), (206, 212, 218)),
        "Graphic Novel Noir": ((18, 18, 18), (80, 80, 80), (240, 240, 240)),
    }
    bg_color, accent_1, text_color = palettes.get(art_style, ((26, 26, 46), (233, 69, 96), (240, 240, 240)))
    
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Outer comic panel border
    draw.rectangle([(12, 12), (width - 12, height - 12)], outline=accent_1, width=6)
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(255, 255, 255), width=2)
    
    # Panel number banner
    draw.rectangle([(30, 30), (240, 75)], fill=accent_1)
    draw.text((45, 42), f"PANEL {panel_number}", fill=(255, 255, 255))
    
    # Art style badge
    draw.rectangle([(width - 240, 30), (width - 30, 75)], outline=accent_1, width=2)
    draw.text((width - 220, 42), art_style[:18], fill=text_color)
    
    # Comic caption bubble
    draw.rounded_rectangle([(60, 160), (width - 60, height - 100)], radius=15, fill=(38, 43, 64), outline=accent_1, width=3)
    
    # Formatted prompt excerpt
    words = prompt.split()
    chunked = []
    curr = []
    for w in words:
        curr.append(w)
        if len(" ".join(curr)) > 55:
            chunked.append(" ".join(curr))
            curr = []
    if curr:
        chunked.append(" ".join(curr))
        
    y = 200
    for line in chunked[:6]:
        draw.text((90, y), line, fill=text_color)
        y += 32
        
    img.save(output_path, format="PNG")

def generate_image(prompt: str, panel_number: int = 1, art_style: str = "Classic Comic Book") -> str:
    settings = get_settings()
    filename = f"panel_{int(time.time())}_{panel_number}_{os.urandom(3).hex()}.png"
    output_path = settings.PANELS_DIR / filename
    
    if settings.HF_API_KEY and not settings.DEV_MOCK_AI:
        try:
            api_url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
            headers = {"Authorization": f"Bearer {settings.HF_API_KEY}"}
            enhanced_prompt = f"comic book panel illustration, {art_style} style, vivid detailed colors, clean lineart, graphic novel art, high quality: {prompt}"
            payload = {
                "inputs": enhanced_prompt,
                "parameters": {"negative_prompt": "blurry, deformed, distorted, low quality, disfigured"}
            }
            res = requests.post(api_url, headers=headers, json=payload, timeout=25)
            if res.status_code == 200 and "image" in res.headers.get("content-type", ""):
                with open(output_path, "wb") as f:
                    f.write(res.content)
                return str(output_path)
        except Exception as e:
            print(f"HF Inference API error, falling back to local styled panel: {e}")
            
    _generate_fallback_image(prompt, panel_number, art_style, output_path)
    return str(output_path)

async def generate_all_panels(outline: List[Dict[str, Any]], art_style: str = "Classic Comic Book") -> List[str]:
    loop = asyncio.get_running_loop()
    tasks = []
    for item in outline:
        p_num = item.get("panel", 1)
        p_prompt = item.get("image_prompt", item.get("scene_description", "Comic illustration"))
        tasks.append(
            loop.run_in_executor(None, generate_image, p_prompt, p_num, art_style)
        )
    return await asyncio.gather(*tasks)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_image_generator.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add app/ai/image_generator.py tests/test_image_generator.py
git commit -m "feat(ai): implement parallel image generator with Pillow fallback"
```

---

### Task 5: Layout Builder Service (`layout_builder.py`)

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/layout_builder.py`
- Test: `tests/test_layout_builder.py`

**Interfaces:**
- Consumes: `outline` (list of 5 dicts), `story_elements` (list of 5 dicts), `image_paths` (list of 5 file paths)
- Produces: `build_comic_layout(outline, story_elements, image_paths) -> List[dict]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_layout_builder.py
import pytest
from app.services.layout_builder import build_comic_layout

def test_build_comic_layout_assembly():
    outline = [
        {"panel": 1, "title": "The Awakening", "scene_description": "Hero awakens in forest.", "image_prompt": "Hero in forest"}
    ]
    story = [
        {"panel": 1, "caption": "Early morning.", "narration": "Sunlight filtered down.", "dialogue": "Hero: 'Where am I?'"}
    ]
    images = ["static/panels/panel_1.png"]
    
    layout = build_comic_layout(outline, story, images)
    assert len(layout) == 1
    panel = layout[0]
    assert panel["panel"] == 1
    assert panel["title"] == "The Awakening"
    assert panel["caption"] == "Early morning."
    assert panel["dialogue"] == "Hero: 'Where am I?'"
    assert panel["image_path"] == "static/panels/panel_1.png"
    assert panel["image_url"].startswith("/static/panels/")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_layout_builder.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'app.services.layout_builder')

- [ ] **Step 3: Write minimal implementation**

Create `app/services/__init__.py`:
```python
"""Business services package for ComicCraft."""
```

Create `app/services/layout_builder.py`:
```python
from pathlib import Path
from typing import List, Dict, Any

def build_comic_layout(
    outline: List[Dict[str, Any]],
    story_elements: List[Dict[str, Any]],
    image_paths: List[str]
) -> List[Dict[str, Any]]:
    """Merges outline, narrative story elements, and generated image paths into a cohesive layout."""
    layout = []
    story_map = {item["panel"]: item for item in story_elements}
    
    for idx, panel_meta in enumerate(outline):
        panel_num = panel_meta.get("panel", idx + 1)
        story_item = story_map.get(panel_num, {})
        img_disk_path = image_paths[idx] if idx < len(image_paths) else ""
        
        # Convert disk path to web URL path (/static/panels/...)
        img_name = Path(img_disk_path).name if img_disk_path else "placeholder.png"
        image_url = f"/static/panels/{img_name}"
        
        layout.append({
            "panel": panel_num,
            "title": panel_meta.get("title", f"Panel {panel_num}"),
            "scene_description": panel_meta.get("scene_description", ""),
            "caption": story_item.get("caption", ""),
            "narration": story_item.get("narration", ""),
            "dialogue": story_item.get("dialogue", ""),
            "image_prompt": panel_meta.get("image_prompt", ""),
            "image_path": str(img_disk_path),
            "image_url": image_url
        })
        
    return layout
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_layout_builder.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add app/services/__init__.py app/services/layout_builder.py tests/test_layout_builder.py
git commit -m "feat(services): implement layout builder for comic panel aggregation"
```

---

### Task 6: Multi-Page Comic PDF Exporter (`exporters.py`)

**Files:**
- Create: `app/services/exporters.py`
- Test: `tests/test_exporters.py`

**Interfaces:**
- Consumes: `layout: List[dict]`, `metadata: dict`
- Produces: `save_pdf(layout: List[dict], metadata: dict = None) -> str` returning relative web path `/static/exports/comic_...pdf`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_exporters.py
import pytest
from pathlib import Path
from PIL import Image
from app.services.exporters import save_pdf
from app.config import get_settings

def test_save_pdf_generation(tmp_path):
    settings = get_settings()
    # Create dummy panel image
    img_path = settings.PANELS_DIR / "test_panel_export.png"
    Image.new("RGB", (400, 300), color=(100, 150, 200)).save(img_path)
    
    mock_layout = [
        {
            "panel": 1,
            "title": "Panel 1: The Arrival",
            "scene_description": "Hero reaches the castle gate under twilight.",
            "caption": "The winds whispered ancient secrets.",
            "narration": "Step by step, the iron gate loomed nearer.",
            "dialogue": "Hero: 'I am ready.'",
            "image_path": str(img_path)
        }
    ]
    metadata = {
        "title": "Adventures of Arthur",
        "character_name": "Arthur",
        "setting": "Castle",
        "tone": "Dramatic",
        "art_style": "Classic Comic Book"
    }
    
    pdf_url = save_pdf(mock_layout, metadata)
    assert pdf_url.startswith("/static/exports/")
    assert pdf_url.endswith(".pdf")
    
    pdf_filename = Path(pdf_url).name
    assert (settings.EXPORTS_DIR / pdf_filename).exists()
    assert (settings.EXPORTS_DIR / pdf_filename).stat().st_size > 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_exporters.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'app.services.exporters')

- [ ] **Step 3: Write minimal implementation**

Create `app/services/exporters.py`:
```python
import os
import time
from pathlib import Path
from typing import List, Dict, Any
from fpdf import FPDF
from app.config import get_settings

def _clean_text(text: str) -> str:
    """Sanitizes text for latin-1 encoding in standard FPDF fonts."""
    if not text:
        return ""
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2014": "-", "\u2013": "-", "\u2026": "...", "\u00a0": " "
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    return text.encode("latin-1", "replace").decode("latin-1")

class ComicPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"ComicCraft - Page {self.page_no()}", 0, 0, "C")

def save_pdf(layout: List[Dict[str, Any]], metadata: Dict[str, Any] = None) -> str:
    settings = get_settings()
    metadata = metadata or {}
    story_title = metadata.get("title", "ComicCraft Story")
    char_name = metadata.get("character_name", "Hero")
    setting = metadata.get("setting", "Enchanted Forest")
    tone = metadata.get("tone", "Dramatic")
    art_style = metadata.get("art_style", "Classic Comic Book")

    pdf = ComicPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    # 1. Cover Page
    pdf.add_page()
    pdf.set_fill_color(26, 26, 46)
    pdf.rect(0, 0, 210, 297, "F")
    
    # Title Header Box
    pdf.set_xy(15, 30)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(242, 222, 102)
    pdf.cell(180, 15, _clean_text(story_title[:35]), 0, 1, "C")
    
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(233, 69, 96)
    pdf.cell(180, 10, "COMICCRAFT ADVENTURES", 0, 1, "C")
    
    # Metadata badges
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(180, 8, _clean_text(f"Hero: {char_name} | Setting: {setting}"), 0, 1, "C")
    pdf.cell(180, 8, _clean_text(f"Tone: {tone} | Style: {art_style}"), 0, 1, "C")
    
    # Cover image preview if first panel exists
    if layout and Path(layout[0].get("image_path", "")).exists():
        first_img = layout[0]["image_path"]
        pdf.image(first_img, x=25, y=110, w=160)
        
    # 2. Sequential Panel Pages
    for idx, panel in enumerate(layout, 1):
        pdf.add_page()
        
        # Panel Title Header
        pdf.set_fill_color(233, 69, 96)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 16)
        p_title = _clean_text(panel.get("title", f"Panel {idx}"))
        pdf.cell(180, 12, f"  {p_title}", 0, 1, "L", fill=True)
        pdf.ln(4)
        
        # Panel Image
        img_path = panel.get("image_path", "")
        if img_path and Path(img_path).exists():
            pdf.image(img_path, x=25, y=pdf.get_y(), w=160)
            pdf.set_y(pdf.get_y() + 115)
        else:
            pdf.ln(20)
            
        # Scene Description (Italics)
        desc = _clean_text(panel.get("scene_description", ""))
        if desc:
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(180, 5, desc)
            pdf.ln(3)
            
        # Caption Box
        caption = _clean_text(panel.get("caption", ""))
        if caption:
            pdf.set_fill_color(240, 240, 245)
            pdf.set_text_color(50, 50, 50)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(180, 6, f"CAPTION: {caption}", 1, 1, "L", fill=True)
            pdf.ln(2)
            
        # Narration
        narration = _clean_text(panel.get("narration", ""))
        if narration:
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(20, 20, 20)
            pdf.multi_cell(180, 6, f"NARRATION: {narration}")
            pdf.ln(2)
            
        # Dialogue
        dialogue = _clean_text(panel.get("dialogue", ""))
        if dialogue:
            pdf.set_fill_color(255, 248, 220)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(180, 40, 40)
            pdf.multi_cell(180, 7, f'DIALOGUE: "{dialogue}"', 1, "L", fill=True)

    filename = f"comic_{int(time.time())}_{os.urandom(3).hex()}.pdf"
    export_path = settings.EXPORTS_DIR / filename
    pdf.output(str(export_path))
    
    return f"/static/exports/{filename}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_exporters.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add app/services/exporters.py tests/test_exporters.py
git commit -m "feat(services): implement FPDF multi-page comic exporter with cover page"
```

---

### Task 7: Presentation Layer & UI Assets (`style.css` & Jinja2 Templates)

**Files:**
- Create: `static/css/style.css`
- Create: `templates/index.html`
- Create: `templates/comic_preview.html`
- Create: `templates/export_success.html`
- Test: `tests/test_templates.py`

**Interfaces:**
- Consumes: Form data, `layout` list, `story_metadata` dict, `pdf_url` string
- Produces: Complete rendered responsive HTML pages

- [ ] **Step 1: Write the failing test**

```python
# tests/test_templates.py
import pytest
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

def test_templates_exist_and_compile():
    templates_dir = Path("templates")
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    
    index_tmpl = env.get_template("index.html")
    assert "ComicCraft" in index_tmpl.render()
    
    preview_tmpl = env.get_template("comic_preview.html")
    rendered_preview = preview_tmpl.render(
        layout=[{
            "panel": 1,
            "title": "Panel 1: Dawn",
            "scene_description": "Sun shines over the horizon.",
            "caption": "Morning begins.",
            "narration": "Arthur walked ahead.",
            "dialogue": "Arthur: 'Forward!'",
            "image_url": "/static/panels/p1.png",
            "image_prompt": "Knight walking at sunrise"
        }],
        story_metadata={"title": "The Quest", "character_name": "Arthur"},
        pdf_url="/static/exports/comic_1.pdf"
    )
    assert "Panel 1: Dawn" in rendered_preview
    assert "/static/exports/comic_1.pdf" in rendered_preview
    
    export_tmpl = env.get_template("export_success.html")
    rendered_export = export_tmpl.render(pdf_path="/static/exports/comic_1.pdf")
    assert "Download Your Comic" in rendered_export or "Comic Exported" in rendered_export
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_templates.py -v`
Expected: FAIL (jinja2.exceptions.TemplateNotFound)

- [ ] **Step 3: Write minimal implementation**

Create `static/css/style.css`:
```css
/* ComicCraft Unified Stylesheet */
:root {
  --comic-bg: #0f111a;
  --panel-bg: #1a1d29;
  --accent-red: #ff3366;
  --accent-yellow: #ffb703;
  --accent-cyan: #06d6a0;
  --text-main: #f8f9fa;
  --text-muted: #9aa0a6;
  --border-comic: #2b3040;
  --speech-bg: #ffffff;
  --speech-text: #111111;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background-color: var(--comic-bg);
  color: var(--text-main);
  line-height: 1.6;
  min-height: 100vh;
}

.container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

/* Header & Branding */
header.comic-header {
  text-align: center;
  margin-bottom: 2.5rem;
}

.comic-title {
  font-size: 2.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--accent-yellow);
  text-shadow: 3px 3px 0 var(--accent-red);
  margin-bottom: 0.5rem;
}

.comic-subtitle {
  color: var(--text-muted);
  font-size: 1.1rem;
}

/* Cards & Forms */
.card {
  background: var(--panel-bg);
  border: 2px solid var(--border-comic);
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 700;
  color: var(--accent-yellow);
}

input[type="text"],
select,
textarea {
  width: 100%;
  padding: 0.85rem 1rem;
  background: #12141f;
  border: 2px solid var(--border-comic);
  border-radius: 8px;
  color: #fff;
  font-size: 1rem;
  transition: border-color 0.2s;
}

input[type="text"]:focus,
select,
textarea:focus {
  outline: none;
  border-color: var(--accent-red);
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
}

/* Comic Button */
.btn-comic {
  display: inline-block;
  background: var(--accent-red);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 1rem 2rem;
  font-size: 1.15rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: transform 0.1s, box-shadow 0.1s;
  text-decoration: none;
}

.btn-comic:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.btn-comic:active {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.btn-yellow {
  background: var(--accent-yellow);
  color: #111;
}

/* Comic Panel Presentation */
.panel-card {
  background: var(--panel-bg);
  border: 3px solid var(--border-comic);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2.5rem;
}

.panel-badge {
  display: inline-block;
  background: var(--accent-red);
  color: #fff;
  padding: 0.35rem 1rem;
  font-weight: 800;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.panel-image {
  width: 100%;
  border-radius: 8px;
  border: 2px solid #000;
  display: block;
  margin-bottom: 1.25rem;
}

.scene-desc {
  font-style: italic;
  color: var(--text-muted);
  margin-bottom: 1rem;
}

.caption-box {
  background: #242938;
  border-left: 4px solid var(--accent-yellow);
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  border-radius: 0 6px 6px 0;
}

.narration-box {
  margin-bottom: 1rem;
  font-size: 1.05rem;
}

.speech-bubble {
  background: var(--speech-bg);
  color: var(--speech-text);
  border-radius: 16px;
  padding: 1rem 1.25rem;
  font-weight: 700;
  position: relative;
  margin-top: 1rem;
  box-shadow: 3px 3px 0 rgba(0,0,0,0.5);
}

.speech-bubble::after {
  content: '';
  position: absolute;
  bottom: -10px;
  left: 30px;
  border-width: 10px 10px 0;
  border-style: solid;
  border-color: var(--speech-bg) transparent;
  display: block;
  width: 0;
}

/* Spinner Overlay */
#spinner-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(15, 17, 26, 0.9);
  z-index: 999;
  justify-content: center;
  align-items: center;
  flex-direction: column;
}

.spinner {
  width: 60px;
  height: 60px;
  border: 6px solid var(--border-comic);
  border-top-color: var(--accent-red);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 1.5rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

Create `templates/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ComicCraft: AI Comic Story Creator</title>
  <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
  <div class="container">
    <header class="comic-header">
      <h1 class="comic-title">ComicCraft</h1>
      <p class="comic-subtitle">Generate personalized 5-panel comic books powered by Google Gemini and AI Art</p>
    </header>

    <div class="card">
      <form action="/generate" method="POST" id="comic-form">
        <div class="form-group">
          <label for="prompt">Comic Story Premise / Prompt:</label>
          <textarea id="prompt" name="prompt" rows="3" required placeholder="e.g. A clever fox discovers an ancient observatory atop the Whispering Mountain..."></textarea>
        </div>

        <div class="grid-2">
          <div class="form-group">
            <label for="character_name">Hero / Main Character Name:</label>
            <input type="text" id="character_name" name="character_name" value="Kael" required>
          </div>

          <div class="form-group">
            <label for="setting">Setting / World:</label>
            <select id="setting" name="setting">
              <option value="Enchanted Forest" selected>Enchanted Forest</option>
              <option value="Cyberpunk Metropolis">Cyberpunk Metropolis</option>
              <option value="Deep Space & Asteroid Belt">Deep Space & Asteroid Belt</option>
              <option value="Ancient Dungeon Ruins">Ancient Dungeon Ruins</option>
              <option value="High School Campus">High School Campus</option>
            </select>
          </div>
        </div>

        <div class="grid-2">
          <div class="form-group">
            <label for="tone">Story Tone:</label>
            <select id="tone" name="tone">
              <option value="Dramatic" selected>Dramatic & Heroic</option>
              <option value="Funny & Humorous">Funny & Humorous</option>
              <option value="Light-hearted & Adventurous">Light-hearted & Adventurous</option>
              <option value="Poetic & Mysterious">Poetic & Mysterious</option>
            </select>
          </div>

          <div class="form-group">
            <label for="art_style">Comic Art Style:</label>
            <select id="art_style" name="art_style">
              <option value="Classic Comic Book" selected>Classic Comic Book</option>
              <option value="Anime">Anime / Manga</option>
              <option value="Pixel Art">Pixel Art</option>
              <option value="Graphic Novel Noir">Graphic Novel Noir</option>
              <option value="Realistic">Cinematic Realistic</option>
            </select>
          </div>
        </div>

        <div style="text-align: center; margin-top: 1.5rem;">
          <button type="submit" class="btn-comic">⚡ Generate 5-Panel Comic</button>
        </div>
      </form>
    </div>
  </div>

  <div id="spinner-overlay">
    <div class="spinner"></div>
    <h2>Crafting Your Comic...</h2>
    <p style="color: var(--text-muted); margin-top: 0.5rem;">Gemini is writing the script & AI is drawing all 5 panels in parallel!</p>
  </div>

  <script>
    document.getElementById('comic-form').addEventListener('submit', function() {
      document.getElementById('spinner-overlay').style.display = 'flex';
    });
  </script>
</body>
</html>
```

Create `templates/comic_preview.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ story_metadata.title or "Comic Preview" }} - ComicCraft</title>
  <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
  <div class="container">
    <header class="comic-header">
      <h1 class="comic-title">{{ story_metadata.title or "Your Comic Story" }}</h1>
      <p class="comic-subtitle">
        Hero: <strong>{{ story_metadata.character_name }}</strong> | 
        Setting: <strong>{{ story_metadata.setting }}</strong> | 
        Tone: <strong>{{ story_metadata.tone }}</strong> | 
        Style: <strong>{{ story_metadata.art_style }}</strong>
      </p>
      <div style="margin-top: 1.5rem; display: flex; gap: 1rem; justify-content: center;">
        <a href="{{ pdf_url }}" class="btn-comic btn-yellow" download>📥 Download Your Comic as PDF</a>
        <a href="/" class="btn-comic" style="background: #444;">✏️ Create Another</a>
      </div>
    </header>

    <div class="comic-panels-container">
      {% for panel in layout %}
      <div class="panel-card">
        <span class="panel-badge">{{ panel.title }}</span>
        
        <img src="{{ panel.image_url }}" alt="{{ panel.title }}" class="panel-image" loading="lazy">
        
        {% if panel.scene_description %}
        <p class="scene-desc">{{ panel.scene_description }}</p>
        {% endif %}
        
        {% if panel.caption %}
        <div class="caption-box">
          <strong>CAPTION:</strong> {{ panel.caption }}
        </div>
        {% endif %}
        
        {% if panel.narration %}
        <div class="narration-box">
          {{ panel.narration }}
        </div>
        {% endif %}
        
        {% if panel.dialogue %}
        <div class="speech-bubble">
          {{ panel.dialogue }}
        </div>
        {% endif %}
      </div>
      {% endfor %}
    </div>

    <div style="text-align: center; margin: 3rem 0;">
      <a href="{{ pdf_url }}" class="btn-comic btn-yellow" download>📥 Download Your Comic as PDF</a>
      <a href="/export-success?pdf_path={{ pdf_url }}" class="btn-comic" style="margin-left: 1rem;">Complete & View Export</a>
    </div>
  </div>
</body>
</html>
```

Create `templates/export_success.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Comic Exported Successfully! - ComicCraft</title>
  <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
  <div class="container" style="text-align: center; margin-top: 4rem;">
    <div class="card">
      <h1 class="comic-title" style="color: var(--accent-cyan); font-size: 2.5rem;">🎉 Comic Exported!</h1>
      <p style="font-size: 1.25rem; margin: 1.5rem 0;">Your 5-panel comic has been compiled into a high-quality multi-page PDF.</p>
      
      <div style="margin: 2rem 0; display: flex; justify-content: center; gap: 1rem;">
        <a href="{{ pdf_path }}" class="btn-comic btn-yellow" download>📥 Download Comic PDF</a>
        <a href="/" class="btn-comic">✨ Go Create Another Comic</a>
      </div>
    </div>
  </div>
</body>
</html>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_templates.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add static/css/style.css templates/ tests/test_templates.py
git commit -m "feat(frontend): create comic-styled Jinja2 templates and CSS"
```

---

### Task 8: FastAPI Routing & Full Integration (`main.py` & `routes.py`)

**Files:**
- Create: `app/routes.py`
- Create: `app/main.py`
- Test: `tests/test_routes.py`

**Interfaces:**
- Consumes: All AI modules, layout builder, PDF exporter, schemas, templates
- Produces: Live FastAPI ASGI server with endpoints `GET /`, `POST /generate`, `POST /generate-comic/json`, `GET /test-image`, `GET /export-success`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_routes.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_home_page_renders():
    response = client.get("/")
    assert response.status_code == 200
    assert "ComicCraft" in response.text
    assert "Comic Story Premise" in response.text

def test_generate_form_endpoint():
    form_data = {
        "prompt": "A robot finds a glowing blue flower in ruins",
        "character_name": "Unit-7",
        "setting": "Cyberpunk Metropolis",
        "tone": "Dramatic",
        "art_style": "Pixel Art"
    }
    response = client.post("/generate", data=form_data)
    assert response.status_code == 200
    assert "Unit-7" in response.text
    assert "Download Your Comic as PDF" in response.text

def test_generate_comic_json_api():
    payload = {
        "prompt": "An astronaut discovers an ancient obelisk on Mars",
        "character_name": "Elena",
        "setting": "Deep Space & Asteroid Belt",
        "tone": "Dramatic",
        "art_style": "Realistic"
    }
    response = client.post("/generate-comic/json", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["layout"]) == 5
    assert data["pdf_url"].startswith("/static/exports/")

def test_developer_test_image_route():
    response = client.get("/test-image?prompt=A+brave+knight&art_style=Anime")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "image_url" in data

def test_export_success_route():
    response = client.get("/export-success?pdf_path=/static/exports/comic_demo.pdf")
    assert response.status_code == 200
    assert "Comic Exported" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_routes.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'app.main')

- [ ] **Step 3: Write minimal implementation**

Create `app/routes.py`:
```python
from pathlib import Path
from fastapi import APIRouter, Request, Form, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.schemas import PromptRequest, ComicResponse
from app.ai.gemini_flash import generate_outline
from app.ai.gemini_pro import generate_story
from app.ai.image_generator import generate_image, generate_all_panels
from app.services.layout_builder import build_comic_layout
from app.services.exporters import save_pdf

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/generate", response_class=HTMLResponse)
async def post_generate(
    request: Request,
    prompt: str = Form(...),
    character_name: str = Form("Hero"),
    setting: str = Form("Enchanted Forest"),
    tone: str = Form("Dramatic"),
    art_style: str = Form("Classic Comic Book")
):
    try:
        outline = generate_outline(prompt, character_name, setting, tone, art_style)
        story = generate_story(outline, character_name, tone)
        image_paths = await generate_all_panels(outline, art_style)
        layout = build_comic_layout(outline, story, image_paths)
        
        story_metadata = {
            "title": outline[0].get("title", f"{character_name}'s Quest").replace("Panel 1: ", ""),
            "character_name": character_name,
            "setting": setting,
            "tone": tone,
            "art_style": art_style
        }
        pdf_url = save_pdf(layout, story_metadata)
        
        return templates.TemplateResponse(
            "comic_preview.html",
            {
                "request": request,
                "layout": layout,
                "story_metadata": story_metadata,
                "pdf_url": pdf_url
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comic generation error: {str(e)}")

@router.post("/generate-comic/json", response_model=ComicResponse)
async def post_generate_json(req: PromptRequest):
    try:
        outline = generate_outline(req.prompt, req.character_name, req.setting, req.tone, req.art_style)
        story = generate_story(outline, req.character_name, req.tone)
        image_paths = await generate_all_panels(outline, req.art_style)
        layout = build_comic_layout(outline, story, image_paths)
        
        story_metadata = {
            "title": outline[0].get("title", f"{req.character_name}'s Tale").replace("Panel 1: ", ""),
            "character_name": req.character_name,
            "setting": req.setting,
            "tone": req.tone,
            "art_style": req.art_style
        }
        pdf_url = save_pdf(layout, story_metadata)
        
        return ComicResponse(
            status="success",
            story_title=story_metadata["title"],
            character_name=req.character_name,
            setting=req.setting,
            tone=req.tone,
            art_style=req.art_style,
            layout=layout,
            pdf_url=pdf_url
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-image")
async def get_test_image(
    prompt: str = Query("A brave hero standing on a mountain peak"),
    art_style: str = Query("Classic Comic Book")
):
    try:
        image_disk_path = generate_image(prompt, panel_number=1, art_style=art_style)
        filename = Path(image_disk_path).name
        return {
            "status": "success",
            "prompt": prompt,
            "art_style": art_style,
            "image_url": f"/static/panels/{filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export-success", response_class=HTMLResponse)
async def get_export_success(request: Request, pdf_path: str = Query("/static/exports/comic.pdf")):
    return templates.TemplateResponse(
        "export_success.html",
        {"request": request, "pdf_path": pdf_path}
    )
```

Create `app/main.py`:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.PANELS_DIR.mkdir(parents=True, exist_ok=True)
    settings.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(
    title="ComicCraft",
    description="AI Comic Story Creator using Gemini Models and Stable Diffusion",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")
app.include_router(router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_routes.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add app/routes.py app/main.py tests/test_routes.py
git commit -m "feat(api): implement FastAPI routes, static mounts and integration endpoints"
```

---

### Task 9: Full Test Suite, Smoke Testing, and Documentation (`README.md`)

**Files:**
- Create: `README.md`
- Run: `pytest` (Entire test suite across all modules)

**Interfaces:**
- Consumes: All modules
- Produces: Verified 100% green test suite, clear run documentation

- [ ] **Step 1: Write `README.md` documentation**

Document:
- Setup instructions (`pip install -r requirements.txt`)
- Environment variable configuration (`.env`)
- Running the server (`uvicorn app.main:app --reload`)
- API endpoints documentation (`/docs`, `/generate-comic/json`, `/test-image`)
- Running the automated test suite (`pytest -v`)

- [ ] **Step 2: Run full automated test suite**

Run: `pytest -v`
Expected: ALL tests passing across config, AI, services, templates, and routes.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add complete ComicCraft setup and execution guide"
```
