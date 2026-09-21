# ComicCraft: AI Comic Story Creator — System Design Specification

## 1. Goal & Product Overview
ComicCraft is an automated, AI-driven generative platform that takes user narrative prompts and transforms them into cohesive 5-panel comic stories with illustrations, character dialogues, narrative captions, and exportable multi-page PDF documents.

The application is built on:
* **FastAPI:** Asynchronous ASGI framework for API endpoints and Jinja2 frontend template rendering.
* **Google Gemini 1.5 Flash:** High-speed structured 5-panel outline generation.
* **Google Gemini 1.5 Pro:** Cohesive narrative expansion, character dialogue, and caption generation.
* **Stable Diffusion v1.5 / Hugging Face Serverless Inference API:** Panel-by-panel comic artwork synthesis (with resilient offline/mock placeholder engine for zero-dependency local testing).
* **FPDF (`fpdf2`):** Multi-page PDF compilation generating formatted comic books.

---

## 2. Directory Layout
```text
ComicCraft/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI initialization, CORS, static mounts, lifespan
│   ├── routes.py                # Route handlers and endpoint controllers
│   ├── config.py                # Environment variable management & app settings
│   ├── schemas.py               # Pydantic request/response models
│   │
│   ├── ai/                      # AI orchestration package
│   │   ├── __init__.py
│   │   ├── gemini_client.py     # Gemini client initialization and configuration
│   │   ├── gemini_flash.py      # Outline & 5-panel planning logic
│   │   ├── gemini_pro.py        # Narration and dialogue expansion logic
│   │   └── image_generator.py   # Stable Diffusion API & concurrent image generation
│   │
│   └── services/                # Business and export services
│       ├── __init__.py
│       ├── layout_builder.py    # Panel-to-story data aggregation
│       └── exporters.py         # Multi-page PDF generation via FPDF
│
├── templates/                   # Jinja2 HTML templates
│   ├── index.html               # Comic creation prompt form
│   ├── comic_preview.html       # Sequential comic panel viewer
│   └── export_success.html      # PDF download confirmation page
│
├── static/                      # Static assets
│   ├── css/
│   │   └── style.css            # Centralized application stylesheet
│   ├── panels/                  # Generated panel images (.png)
│   └── exports/                 # Generated comic PDFs (.pdf)
│
├── tests/                       # Automated test suite
│   ├── __init__.py
│   ├── test_ai_modules.py       # Unit tests for outline, story, and image generation
│   ├── test_services.py         # Unit tests for layout builder and PDF export
│   └── test_routes.py           # Integration tests for FastAPI endpoints
│
├── docs/                        # Project documentation and specifications
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-09-21-comiccraft-design.md
│       └── plans/
│
├── .env.example                 # Environment configuration template
├── .gitignore                   # Ignored files (venv, secrets, generated media)
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

---

## 3. Configuration & Schema Specifications

### 3.1 `app/config.py`
* Reads environment variables via `python-dotenv` or `pydantic-settings`.
* Fields:
  * `GEMINI_API_KEY: str = ""`
  * `HF_API_KEY: str = ""`
  * `BASE_DIR: Path`: Project root directory.
  * `PANELS_DIR: Path`: Resolved directory for `static/panels`.
  * `EXPORTS_DIR: Path`: Resolved directory for `static/exports`.
  * `DEV_MOCK_AI: bool`: Set to `True` if `GEMINI_API_KEY` is not provided or in testing environment.

### 3.2 `app/schemas.py`
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

---

## 4. AI Orchestration Engine (`app/ai/`)

### 4.1 `app/ai/gemini_client.py`
* Wraps `google.generativeai`.
* Configures API key if provided.
* Provides helper methods `get_flash_model()` and `get_pro_model()`.
* Automatically activates mock responses if `DEV_MOCK_AI=True` or `GEMINI_API_KEY` is empty.

### 4.2 `app/ai/gemini_flash.py`
* **Function:** `generate_outline(user_prompt: str, character_name: str, setting: str, tone: str, art_style: str) -> List[dict]`
* **Model:** `models/gemini-1.5-flash`
* **Output:** Strictly validated 5-element JSON array following the 5-act narrative structure (Setup, Inciting Incident, Rising Action, Climax, Resolution).
* **Fallback:** Returns a rich, context-aware 5-panel mock outline matching the user's inputs when Gemini API key is not configured.

### 4.3 `app/ai/gemini_pro.py`
* **Function:** `generate_story(outline: List[dict], character_name: str, tone: str) -> List[dict]`
* **Model:** `models/gemini-1.5-pro`
* **Output:** Expands each panel in the outline into:
  * `caption`: Ambient sound/scene cue.
  * `narration`: Narrative prose detailing actions and thoughts.
  * `dialogue`: In-character speech formatted for dialogue bubbles.
* **Fallback:** Generates immersive thematic story elements for each panel matching the user's specified character and tone.

### 4.4 `app/ai/image_generator.py`
* **Function:** `generate_image(prompt: str, panel_number: int, art_style: str) -> str`
* **Function:** `generate_all_panels(outline: List[dict], art_style: str) -> List[str]`
* **Primary Engine:** Hugging Face Serverless Inference API for `runwayml/stable-diffusion-v1-5` using `HF_API_KEY`.
* **Prompt Engineering:** Enriches prompts with style triggers (e.g., `"vibrant comic book art, detailed line work, graphic novel style, cinematic lighting, masterpiece"`).
* **Parallel Execution:** Uses `asyncio.to_thread` / `concurrent.futures.ThreadPoolExecutor` to generate all 5 panel images simultaneously, reducing latency by up to 80%.
* **Resilient Pillow Fallback:** When `HF_API_KEY` is not present, network fails, or in unit tests, generates styled comic panel placeholder images with color gradients, panel headers, and comic speech bubble motifs saved to `static/panels/`.

---

## 5. Services Layer (`app/services/`)

### 5.1 `app/services/layout_builder.py`
* **Function:** `build_comic_layout(outline: List[dict], story_elements: List[dict], image_paths: List[str]) -> List[dict]`
* Combines outline, expanded narrative/dialogue, and generated image paths into a structured panel list ready for template rendering and PDF export.

### 5.2 `app/services/exporters.py`
* **Engine:** `fpdf2`
* **Function:** `save_pdf(layout: List[dict], story_metadata: dict) -> str`
* Creates a multi-page PDF:
  * **Page 1 (Cover):** Title banner, metadata tags (Character, Setting, Tone, Art Style), and cover preview.
  * **Pages 2–6 (Panels 1–5):**
    * Panel header banner (`Panel N: Title`).
    * Centered panel image (`w=160mm`) with border.
    * Italicized scene description box.
    * Caption and character dialogue speech box.
    * Footer with page numbers (`Page X of 6`) and ComicCraft branding.
* Saves to `static/exports/comic_{timestamp}_{id}.pdf` and returns the static web URL (`/static/exports/...`).

---

## 6. Routing & Endpoints (`app/routes.py` & `app/main.py`)

* `GET /`: Renders `templates/index.html` with form inputs and options.
* `POST /generate`: Form submission endpoint parsing `prompt`, `character_name`, `setting`, `tone`, and `art_style`. Runs pipeline and returns `templates/comic_preview.html`.
* `POST /generate-comic/json`: Headless JSON endpoint accepting `PromptRequest` and returning `ComicResponse`.
* `GET /test-image`: Utility endpoint accepting `prompt` and `art_style` query params for standalone image testing.
* `GET /export-success`: Renders `templates/export_success.html` with direct download link and return CTA.

---

## 7. Frontend & Visual Design

* **`templates/index.html`:** Form interface with curated settings, tones, and art styles, paired with an interactive animated loading spinner on submit.
* **`templates/comic_preview.html`:** Responsive sequential panel viewer with:
  * Panel title badges
  * High-res illustration cards
  * Italicized scene descriptions
  * Styled ambient caption cards
  * Character dialogue speech bubbles with pointing tails
  * Collapsible prompt reference
  * "Download Your Comic as PDF" action button
* **`templates/export_success.html`:** Congratulatory confirmation page with download trigger and "Create Another Comic" CTA.
* **`static/css/style.css`:** Vibrant comic-book styling with clean borders, halftone accents, card elevation, and responsive flex/grid layouts.

---

## 8. Verification & Testing Strategy
* `tests/test_ai_modules.py`: Tests outline generation, story expansion, and image synthesis with deterministic mocks.
* `tests/test_services.py`: Tests layout aggregation and PDF generation (verifying valid PDF binary output).
* `tests/test_routes.py`: Tests `GET /`, `POST /generate`, `POST /generate-comic/json`, `GET /test-image`, and `GET /export-success`.
