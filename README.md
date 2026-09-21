# ComicCraft 🎨📖

> **Autonomous AI Comic Story Creator powered by Google Gemini, Stable Diffusion, and FastAPI.**

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-1.5%20Flash%20%26%20Pro-8E75B2.svg?logo=google&logoColor=white)](https://ai.google.dev/)
[![FPDF2](https://img.shields.io/badge/Export-FPDF2%20Multi--Page-E05A47.svg)](https://py-pdf.github.io/fpdf2/)
[![Tests](https://img.shields.io/badge/Tests-58%2F58%20Passing%20(100%25)-success.svg)](tests/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

ComicCraft turns creative ideas into complete, publication-ready comic books in seconds. It coordinates multi-tier LLMs for structured narrative pacing, generates stylized panel illustrations, renders responsive reading experiences in the browser, and compiles multi-page printable PDF editions ready for distribution.

---

## 🌟 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Core AI Technologies](#-core-ai-technologies)
- [Project Directory Structure](#-project-directory-structure)
- [Quick Start & Installation](#-quick-start--installation)
  - [Prerequisites](#prerequisites)
  - [1. Clone Repository & Setup Virtual Environment](#1-clone-repository--setup-virtual-environment)
  - [2. Install Dependencies](#2-install-dependencies)
  - [3. Configure Environment Variables](#3-configure-environment-variables)
  - [4. Launch the Application](#4-launch-the-application)
- [Feature Walkthrough](#-feature-walkthrough)
  - [1. Interactive Web Interface](#1-interactive-web-interface)
  - [2. Sequential Comic Reader](#2-sequential-comic-reader)
  - [3. Publication-Grade Multi-Page PDF Export](#3-publication-grade-multi-page-pdf-export)
  - [4. Headless REST API](#4-headless-rest-api)
  - [5. Developer Image Testing Utility](#5-developer-image-testing-utility)
  - [6. Interactive Swagger Documentation](#6-interactive-swagger-documentation)
- [Testing & Quality Verification](#-testing--quality-verification)
- [Supported Art Styles & Themes](#-supported-art-styles--themes)
- [Fault Tolerance & Resilience](#-fault-tolerance--resilience)
- [License & Acknowledgments](#-license--acknowledgments)

---

## 🚀 Overview

Creating graphic novels and comic strips usually demands scriptwriters, story artists, illustrators, letterers, and book binders. **ComicCraft** unifies these creative disciplines into an autonomous AI generation pipeline:

1. **Storyline Architecture**: Converts natural language prompts into a 5-panel classic narrative arc (Setup, Inciting Incident, Escalation, Climax, Resolution).
2. **Character & Dialogue Scripting**: Synthesizes atmospheric narrator captions, descriptive scene prose, and expressive character speech.
3. **Artwork Generation**: Generates 5 high-resolution panel illustrations with consistent visual styles, color palettes, and panel borders.
4. **Layout Assembly**: Aggregates story elements, metadata, and artwork paths into structured Pydantic models.
5. **Multi-Format Publication**: Renders an in-browser comic viewer and compiles an A4 multi-page PDF with cover page, metadata block, and individual panel pages.

---

## 🏗️ System Architecture

```
                                  ┌────────────────────────┐
                                  │      User Request      │
                                  │   (Web Form / JSON)    │
                                  └───────────┬────────────┘
                                              │
                                              ▼
                                 ┌─────────────────────────┐
                                 │   FastAPI Router        │
                                 │   (app/routes.py)       │
                                 └────────────┬────────────┘
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼                                                   ▼
       ┌─────────────────────────┐                         ┌─────────────────────────┐
       │   Gemini 1.5 Flash      │                         │     Gemini 1.5 Pro      │
       │   5-Panel Story Outline │                         │   Dialogue & Narration  │
       │  (app/ai/gemini_flash)  │                         │   (app/ai/gemini_pro)   │
       └────────────┬────────────┘                         └────────────┬────────────┘
                    │                                                   │
                    ▼                                                   │
       ┌─────────────────────────┐                                      │
       │ Stable Diffusion / PIL  │                                      │
       │ Parallel Panel Artwork  │                                      │
       │(app/ai/image_generator) │                                      │
       └────────────┬────────────┘                                      │
                    │                                                   │
                    └─────────────────────────┬─────────────────────────┘
                                              │
                                              ▼
                                 ┌─────────────────────────┐
                                 │     Layout Builder      │
                                 │ (app/services/layout)   │
                                 └────────────┬────────────┘
                                              │
                         ┌────────────────────┴────────────────────┐
                         ▼                                         ▼
            ┌─────────────────────────┐               ┌─────────────────────────┐
            │   Jinja2 Web Preview    │               │    FPDF2 PDF Exporter   │
            │ (templates/comic_preview│               │ (app/services/exporters)│
            └─────────────────────────┘               └─────────────────────────┘
```

---

## 🤖 Core AI Technologies

| Component | Technology | Responsibility | Fallback Mechanism |
| :--- | :--- | :--- | :--- |
| **Story Outline** | **Google Gemini 1.5 Flash** | Rapidly analyzes user premise and outlines a 5-panel narrative arc with visual image prompts in strict JSON schema. | Procedural dynamic mock outline tailored to character, setting, and tone. |
| **Script & Dialogue** | **Google Gemini 1.5 Pro** | Generates rich narrative text, atmospheric captions, and character dialogue formatted in speech syntax. | Deterministic narrative generator with tone adaptation. |
| **Panel Artwork** | **Stable Diffusion v1.5** | Generates 768×512 visual illustrations via Hugging Face Serverless Inference API. | Procedural Pillow canvas generator with custom borders, badges, halftone dots, and art style palettes. |
| **Document Engine** | **FPDF2** | Typesets vector layouts, title covers, metadata cards, artwork scaling, and Latin-1 sanitized typography. | Direct download link and localized asset preservation. |
| **Web Framework** | **FastAPI & Uvicorn** | Async ASGI backend supporting HTML templating, CORS, OpenAPI documentation, and headless JSON endpoints. | Automatic exception interception and detailed 500 error envelopes. |

---

## 📁 Project Directory Structure

```text
ComicCraft/
│
├── app/
│   ├── __init__.py                  # App package initialization
│   ├── main.py                      # FastAPI app entry point, CORS & lifespan hooks
│   ├── routes.py                    # Endpoint routes (Web UI, API, Image tests, PDF exports)
│   ├── config.py                    # Environment settings (Pydantic-free dotenv singleton)
│   ├── schemas.py                   # Data schemas (PromptRequest, PanelOutline, ComicResponse)
│   │
│   ├── ai/                          # Generative AI & Artwork synthesis
│   │   ├── __init__.py              # AI package marker
│   │   ├── gemini_client.py         # Google Generative AI authentication singleton
│   │   ├── gemini_flash.py          # Gemini 1.5 Flash 5-panel outline planner
│   │   ├── gemini_pro.py            # Gemini 1.5 Pro dialogue & narration generator
│   │   └── image_generator.py       # Stable Diffusion & Pillow procedural artwork engine
│   │
│   └── services/                    # Business logic and export layer
│       ├── __init__.py              # Services package marker
│       ├── layout_builder.py        # Panel aggregation and image normalization
│       └── exporters.py             # Multi-page publication PDF generator via FPDF2
│
├── static/                          # Static public assets
│   ├── css/
│   │   └── style.css                # Comic-book styled CSS with responsive grid
│   ├── panels/                      # Generated comic panel PNG illustrations
│   └── exports/                     # Generated comic book PDF documents
│
├── templates/                       # Jinja2 HTML templates
│   ├── index.html                   # Comic creation input studio form
│   ├── comic_preview.html           # In-browser sequential comic panel reader
│   └── export_success.html          # PDF download confirmation screen
│
├── tests/                           # Complete automated pytest test suite
│   ├── test_config_and_schemas.py   # Settings and schema validation tests
│   ├── test_gemini_flash.py         # Flash outline generator unit tests
│   ├── test_gemini_pro.py           # Pro dialogue & narrative unit tests
│   ├── test_image_generator.py      # Image generator & fallback unit tests
│   ├── test_layout_builder.py       # Layout aggregator unit tests
│   ├── test_exporters.py            # FPDF2 multi-page PDF exporter unit tests
│   ├── test_templates.py            # Jinja2 template rendering tests
│   └── test_routes.py               # FastAPI endpoint integration tests
│
├── .env.example                     # Environment template configuration
├── .gitignore                       # Git ignore rules for media, venv, and secrets
├── requirements.txt                 # Pinned project dependencies
└── README.md                        # Master project documentation
```

---

## ⚡ Quick Start & Installation

### Prerequisites
* **Python**: 3.10 or higher
* **Git**: Installed on your system
* *(Optional)*: Google Gemini API key ([Google AI Studio](https://aistudio.google.com/))
* *(Optional)*: Hugging Face API key ([Hugging Face Tokens](https://huggingface.co/settings/tokens))

> **Note**: ComicCraft includes offline mock AI and procedural image generation engines. You can run and test the complete application locally even without API keys!

---

### 1. Clone Repository & Setup Virtual Environment

```bash
# Clone the repository
git clone https://github.com/your-username/ComicCraft.git
cd ComicCraft

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On Windows (Command Prompt):
.\venv\Scripts\activate.bat

# On macOS / Linux:
source venv/bin/activate
```

---

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 3. Configure Environment Variables

Create your `.env` file from the provided `.env.example`:

```bash
# Windows PowerShell:
Copy-Item .env.example .env

# macOS / Linux:
cp .env.example .env
```

Open `.env` and set your configuration options:

```dotenv
# Google Gemini API key for story outline and dialogue generation
GEMINI_API_KEY=your_gemini_api_key_here

# Hugging Face Access Token for Stable Diffusion panel illustrations
HF_API_KEY=your_huggingface_api_key_here

# Set to true to run offline with zero API calls (ideal for dev & testing)
# Set to false to use live Gemini and Stable Diffusion APIs
DEV_MOCK_AI=true
```

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | `string` | `""` | API key from Google AI Studio. |
| `HF_API_KEY` | `string` | `""` | User Access Token with inference permissions from Hugging Face. |
| `DEV_MOCK_AI` | `boolean` | `true` (if no key) | When `true`, enables deterministic local mock generation. Automatically enabled if `GEMINI_API_KEY` is omitted. |

---

### 4. Launch the Application

Start the FastAPI ASGI server with auto-reload:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Once started, access the application:
- 🌐 **Web Studio UI**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- 📚 **Interactive Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 📖 **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🎨 Feature Walkthrough

### 1. Interactive Web Interface
Navigate to `http://127.0.0.1:8000` to access the ComicCraft Studio:
* **Story Premise**: Describe your core idea or storyline (minimum 3 characters).
* **Protagonist Name**: Name your hero, villain, or explorer.
* **Story Setting**: Specify the world or backdrop (e.g., *Cyberpunk Neo-Tokyo*, *Enchanted Forest*, *Deep Space Station*).
* **Narrative Tone**: Set the emotional frequency (*Dramatic*, *Humorous*, *Action-Packed*, *Mysterious*, *Heartwarming*).
* **Art Style**: Select from 5 distinct visual aesthetics (*Classic Comic Book*, *Anime*, *Pixel Art*, *Realistic*, *Graphic Novel Noir*).

---

### 2. Sequential Comic Reader
Submitting the form executes the pipeline and renders `comic_preview.html`:
* **Comic Header**: Displays the generated issue title, protagonist, setting, and style badge.
* **5 Sequential Panels**:
  - High-resolution illustration artwork.
  - Scene direction summary.
  - Distinct amber atmospheric caption box.
  - Narrative action text.
  - Dedicated speech bubble container formatted for character dialogue.
* **Actions**: Download as PDF, or start a new comic.

---

### 3. Publication-Grade Multi-Page PDF Export
Clicking **Download Comic as PDF** or navigating to `/export-success` generates an A4 document:
* **Cover Page**:
  - Dark navy title banner with golden border accents.
  - Dynamic preview teaser art from Panel 1.
  - Structured Metadata Specification card (Protagonist, Setting, Tone, Art Style, Panel count).
  - ComicCraft digital edition watermark.
* **Panel Pages (1 Panel per page)**:
  - Header banner with Panel number and Scene title.
  - Proportional artwork framing with dark border.
  - Italicized scene direction.
  - Highlighted caption box.
  - Narration text box.
  - Highlighted dialogue box.
  - Stylized footer: `"ComicCraft - Page X of Y"`.

---

### 4. Headless REST API

ComicCraft provides a headless REST API for programmatically generating comics.

#### `POST /generate-comic/json`

##### Request Body
```json
{
  "prompt": "A courageous cyber-detective solves a digital heist inside a quantum vault",
  "character_name": "Detective Vane",
  "setting": "Neo-Veridia Sector 7",
  "tone": "Mysterious",
  "art_style": "Graphic Novel Noir"
}
```

##### Example cURL
```bash
curl -X POST "http://127.0.0.1:8000/generate-comic/json" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A courageous cyber-detective solves a digital heist inside a quantum vault",
    "character_name": "Detective Vane",
    "setting": "Neo-Veridia Sector 7",
    "tone": "Mysterious",
    "art_style": "Graphic Novel Noir"
  }'
```

##### Example Python
```python
import requests

payload = {
    "prompt": "A lonely astronaut encounters a friendly star creature",
    "character_name": "Nova",
    "setting": "Andromeda Nebula",
    "tone": "Heartwarming",
    "art_style": "Anime",
}

response = requests.post("http://127.0.0.1:8000/generate-comic/json", json=payload)
data = response.json()

print(f"Title: {data['story_title']}")
print(f"PDF URL: {data['pdf_url']}")
print(f"Total Panels: {len(data['layout'])}")
```

##### Sample JSON Response
```json
{
  "status": "success",
  "story_title": "Nova's Quest in Andromeda Nebula",
  "character_name": "Nova",
  "setting": "Andromeda Nebula",
  "tone": "Heartwarming",
  "art_style": "Anime",
  "layout": [
    {
      "panel": 1,
      "title": "The Beginning at Andromeda Nebula",
      "scene_description": "In this heartwarming tale inspired by 'A lonely astronaut encounters a friendly star creature', Nova arrives at Andromeda Nebula, surveying the vast landscape and preparing for what lies ahead.",
      "caption": "[The Beginning at Andromeda Nebula] An uneasy quiet settles across the landscape as winds whisper of imminent change.",
      "narration": "In this heartwarming journey, Nova steps into the unknown, eyes scanning the horizon for signs of destiny.",
      "dialogue": "Nova: 'Every journey begins with a choice. I won't turn back now.'",
      "image_prompt": "Anime illustration of Nova standing resolutely at Andromeda Nebula...",
      "image_path": "D:\\Comic_Craft\\static\\panels\\panel_1790010251_1_6b090901.png",
      "image_url": "/static/panels/panel_1790010251_1_6b090901.png"
    }
  ],
  "pdf_url": "/static/exports/comic_1790010251_a1b2c3d4.pdf"
}
```

---

### 5. Developer Image Testing Utility

To quickly test illustration generation for a single prompt without running the full 5-panel pipeline:

#### `GET /test-image`
```
GET /test-image?prompt=Cyberpunk+cyborg+standing+in+neon+rain&art_style=Pixel+Art
```

Response:
```json
{
  "status": "success",
  "prompt": "Cyberpunk cyborg standing in neon rain",
  "art_style": "Pixel Art",
  "image_url": "/static/panels/panel_1790010260_1_8f2a1b9c.png"
}
```

---

### 6. Interactive Swagger Documentation
Explore and test all endpoints directly from your browser:
* Open `http://127.0.0.1:8000/docs` to execute requests with interactive schemas, validation feedback, and response previews.

---

## 🧪 Testing & Quality Verification

ComicCraft includes a comprehensive automated test suite with **58 tests** covering all layers of the application.

### Running Tests

```bash
# Run the entire test suite with verbose output
pytest -v
```

### Test Suite Breakdown

| Test File | Covered Components | Tests |
| :--- | :--- | :--- |
| `tests/test_config_and_schemas.py` | Settings initialization, `.env` detection, Pydantic validation for `PromptRequest`, `PanelOutline`, `ComicPanel`, and `ComicResponse`. | 5 |
| `tests/test_gemini_flash.py` | Outline generation, schema validation, Gemini client fallback, exception handling, and malformed JSON resilience. | 6 |
| `tests/test_gemini_pro.py` | Story scripting, dialogue structuring, mock narrative fallback, empty outline handling, and JSON parsing. | 5 |
| `tests/test_image_generator.py` | Stable Diffusion API requests, Pillow canvas procedural fallback, palette application, and concurrent panel synthesis (`generate_all_panels`). | 7 |
| `tests/test_layout_builder.py` | Panel outline and story reconciliation, out-of-order panel matching, image path normalization, and Pydantic object handling. | 8 |
| `tests/test_exporters.py` | FPDF2 multi-page PDF generation, cover page layout, Latin-1 character sanitization (`_clean_text`), missing image handling, and page numbering. | 8 |
| `tests/test_templates.py` | Jinja2 template syntax verification, template compilation, HTML element assertions, and CSS stylesheet verification. | 5 |
| `tests/test_routes.py` | FastAPI endpoint integration testing (`GET /`, `POST /generate`, `POST /generate-comic/json`, `GET /test-image`, `GET /export-success`), error handlers, and static file serving. | 14 |
| **Total** | **Full System Verification** | **58 / 58 (100% Pass Rate)** |

---

## 🎨 Supported Art Styles & Themes

Each art style is deeply integrated into both the prompt generation engineering and the procedural fallback engine:

| Style Name | Palette Theme | Background / Accents | Visual Characteristic |
| :--- | :--- | :--- | :--- |
| **Classic Comic Book** | Deep Comic Blue & Golden Yellow | `#181E30` / `#FACC15` / `#EF4444` | High-contrast ink lines, Ben-Day dot pattern, retro comic badges. |
| **Anime** | Twilight Purple & Neon Sakura | `#201840` / `#F472B6` / `#A855F7` | Soft anime gradients, vibrant highlights, modern light framing. |
| **Pixel Art** | 8-Bit Midnight & Emerald Green | `#0F172A` / `#34D399` / `#0EA5E9` | Retro arcade aesthetic, monospace balance, cyber-grid highlights. |
| **Realistic** | Neutral Zinc & Polished Silver | `#18181B` / `#D4D4D8` / `#71717A` | Cinematic subdued tones, sleek cards, refined border lines. |
| **Graphic Novel Noir** | Stark Charcoal & Sinister Crimson | `#0A0A0A` / `#DC2626` / `#FFFFFF` | High-contrast chiaroscuro, heavy black shadows, dramatic crimson accents. |

---

## 🛡️ Fault Tolerance & Resilience

ComicCraft is engineered for production-grade reliability:

1. **Autonomous Offline Fallback (`DEV_MOCK_AI`)**:
   - If no API key is provided, or if external AI services experience downtime or rate limits, the system transparently falls back to procedural story generation and Pillow artwork synthesis.
2. **Robust JSON Parsing & Markdown Sanitization**:
   - LLM responses wrapped in markdown code blocks (` ```json ... ``` `) or nested dictionaries are automatically extracted and validated against Pydantic models.
3. **Unicode-Safe PDF Export**:
   - FPDF standard Latin-1 fonts often crash when encountering smart quotes, em-dashes, or unicode emojis. ComicCraft's `_clean_text` sanitizes typography to prevent encoding errors.
4. **Resilient Image Handling**:
   - Missing or corrupted panel images automatically render graceful placeholder frames in the PDF rather than failing the export.

---

## 📄 License & Acknowledgments

This project is licensed under the MIT License.

* **Google Generative AI**: [Google AI Gemini Documentation](https://ai.google.dev/docs)
* **FastAPI Framework**: [Tiangolo FastAPI](https://fastapi.tiangolo.com/)
* **FPDF2**: [py-pdf/fpdf2](https://github.com/py-pdf/fpdf2)
* **Pillow (PIL Fork)**: [Python Imaging Library](https://python-pillow.org/)
