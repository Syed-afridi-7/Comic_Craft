# ComicCraft: AI Comic Story Creator

An end-to-end overview and technical specification for **ComicCraft**, a FastAPI-powered generative AI platform that creates personalized comic books—complete with structured storylines, dialogue, illustrations, and exportable PDFs—using Google Gemini and Stable Diffusion.

---

## 1. Project Overview

ComicCraft automates the entire creative pipeline of comic strip generation:
* **Story Planning & Outlining:** Converts high-level user prompts into structured 5-panel scenarios using **Gemini 1.5 Flash**.
* **Scriptwriting & Dialogue:** Expands scene descriptions into narration and dialogue using **Gemini 1.5 Pro**.
* **Illustration Synthesis:** Generates high-quality comic-style art for each panel using **Stable Diffusion v1.5**.
* **Layout & Compilation:** Packages narrative text and images into responsive web previews and multi-page printable PDFs using **FPDF**.

---

## 2. Complete Project Directory Structure

```text
ComicCraft/
│
├── app/
│   ├── __init__.py              # App package marker
│   ├── main.py                  # App initialization, CORS, and lifespan
│   ├── routes.py                # Route handlers and endpoint controllers
│   ├── config.py                # Environment variable management & app settings
│   ├── schemas.py               # Pydantic request/response models
│   │
│   ├── ai/                      # AI orchestration package
│   │   ├── __init__.py          # AI package marker
│   │   ├── gemini_client.py     # Gemini client initialization and configuration
│   │   ├── gemini_flash.py      # Outline & panel planning logic
│   │   ├── gemini_pro.py        # Narration and dialogue generation
│   │   └── image_generator.py   # Stable Diffusion pipeline & image saving
│   │
│   └── services/                # Business and export services
│       ├── __init__.py          # Services package marker
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
│   ├── panels/                  # Generated panel images
│   └── exports/                 # Generated comic PDFs
│
├── .env.example                 # Environment configuration template
├── .gitignore                   # Ignored files (virtual environments, secrets, media)
├── requirements.txt             # Python project dependencies
└── README.md                    # Project documentation
```

---

## 3. System Architecture & Component Roles

```
[ User Browser ]
       │
       ▼
[ FastAPI Backend (app/routes.py) ]
       │
       ├──► [ Validation & Settings ]
       │       ├── app/config.py   (Loads environment variables)
       │       └── app/schemas.py  (Validates PromptRequest JSON payload)
       │
       ├──► [ AI Package (app/ai/) ]
       │       ├── gemini_client.py     (Shared client session)
       │       ├── gemini_flash.py      (5-panel outline JSON generation)
       │       ├── gemini_pro.py        (Narrative & dialogue expansion)
       │       └── image_generator.py   (Stable Diffusion v1.5 image creation)
       │
       ├──► [ Services Package (app/services/) ]
       │       ├── layout_builder.py    (Aggregates text, images, and outline)
       │       └── exporters.py         (Builds PDF via FPDF)
       │
       └──► [ Presentation Layer ]
               ├── templates/           (index, preview, and success screens)
               └── static/css/style.css (Centralized UI styling)
```

---

## 4. Key Modules & Technical Specifications

### `app/config.py`
Centralizes settings and reads environment variables via `python-dotenv`:
* `GEMINI_API_KEY`: Authentication key for Google Generative AI.
* `HF_API_KEY`: Authentication token for Hugging Face Diffusers models.
* Directories: Defines resolved paths for `static/panels/` and `static/exports/`.

### `app/schemas.py`
Defines Pydantic models for request validation and structured API responses:
* `PromptRequest`: Validates user inputs (`prompt`, `character_name`, `setting`, `tone`, `style`).
* `ComicResponse`: Formats API responses containing panel layouts and download URLs.

### `app/ai/gemini_client.py`
Initializes and manages instances of Google's Generative AI client to avoid redundant re-authentication calls across files.

### `app/ai/gemini_flash.py`
* **Function:** `generate_outline(user_prompt: str) -> list`
* **Model:** `models/gemini-1.5-flash`
* **Task:** Returns a strictly formatted 5-item JSON array. Each object contains:
  * `panel` (integer)
  * `title` (string)
  * `scene_description` (string)
  * `image_prompt` (string)

### `app/ai/gemini_pro.py`
* **Function:** `generate_story(outline: list) -> str`
* **Model:** `models/gemini-1.5-pro`
* **Task:** Expands outline scenes into cohesive narrative prose, character dialogue lines, and panel captions.

### `app/ai/image_generator.py`
* **Function:** `generate_image(prompt: str, filename: str = None) -> str`
* **Model:** `runwayml/stable-diffusion-v1-5` (via `diffusers` & `torch`)
* **Task:** Synthesizes panel artwork from prompts, saves generated images into `static/panels/`, and returns the saved file path.

### `app/services/layout_builder.py`
* **Function:** `build_comic_layout(image_paths: list, full_story: str, outline: list) -> list`
* **Task:** Aligns generated images with corresponding panel text, scene summaries, and titles into a unified data structure ready for template rendering.

### `app/services/exporters.py`
* **Function:** `save_pdf(layout: list) -> str`
* **Engine:** `FPDF`
* **Task:** Generates a structured multi-page PDF document placing panel headers, rendered images, and script blocks on sequential pages. Output is saved to `static/exports/comic_{timestamp}.pdf`.

---

## 5. API Endpoints & Routes

| Method | Route | Description | Input | Output |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | Loads main user interface form | None | HTML (`index.html`) |
| `POST` | `/generate` | Submits form, runs generation pipeline | Form fields | HTML (`comic_preview.html`) |
| `POST` | `/generate-comic/json` | Headless API for comic generation | JSON payload | JSON layout + PDF file path |
| `GET` | `/test-image` | Developer utility for image testing | Query: `prompt` | JSON status + image path |
| `GET` | `/export-success` | Download confirmation screen | Query: `pdf_path` | HTML (`export_success.html`) |

---

## 6. Frontend Templates & Assets

* **`templates/index.html`**: User form capturing the story premise, character name, setting, mood/tone, and art style.
* **`templates/comic_preview.html`**: Sequential reader displaying generated panels, descriptions, character dialogue, captions, and the "Download Your Comic as PDF" action button.
* **`templates/export_success.html`**: Confirmation page providing feedback and a call-to-action to return to the comic creator.
* **`static/css/style.css`**: Centralized stylesheet maintaining consistent typography, responsive grid alignments, card containers, and button states across all pages.

---

## 7. Setup and Execution

### 1. Environment Setup
```bash
# Create and activate virtual environment
python -m venv env

# Windows
env\Scripts\activate

# macOS / Linux
source env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables Configuration
Copy `.env.example` to `.env` and provide your credentials:
```env
GEMINI_API_KEY=your_gemini_api_key_here
HF_API_KEY=your_huggingface_api_key_here
```

### 3. Running the Application
```bash
uvicorn app.main:app --reload
```
* **Web UI:** `http://127.0.0.1:8000`
* **Swagger API Documentation:** `http://127.0.0.1:8000/docs`