"""FastAPI endpoint routes and controllers for ComicCraft."""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.ai.gemini_flash import generate_outline
from app.ai.gemini_pro import generate_story
from app.ai.image_generator import generate_all_panels, generate_image
from app.config import get_settings
from app.schemas import ComicPanel, ComicResponse, PromptRequest
from app.services.exporters import save_pdf
from app.services.layout_builder import build_comic_layout

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "templates"))
DEFAULT_EXPORT_PDF = "/static/exports/comic.pdf"


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main comic creator input form page."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )


@router.post("/generate", response_class=HTMLResponse)
async def generate_comic_html(
    request: Request,
    prompt: str = Form(...),
    character_name: str = Form("Hero"),
    setting: str = Form("Enchanted Forest"),
    tone: str = Form("Dramatic"),
    art_style: str = Form("Classic Comic Book"),
):
    """Execute the full comic generation pipeline from HTML form submission.

    Renders sequential comic preview with panel illustrations and PDF download link.
    """
    logger.info("Starting comic generation pipeline for character '%s'", character_name)

    try:
        # 1. Generate 5-panel story outline via Gemini Flash (offloaded to thread)
        outline = await asyncio.to_thread(
            generate_outline, prompt, character_name, setting, tone, art_style
        )

        # 2. Generate narrative, captions, and dialogues via Gemini Pro (offloaded to thread)
        story = await asyncio.to_thread(generate_story, outline, character_name, tone)

        # 3. Concurrently synthesize all panel artwork
        image_paths = await generate_all_panels(outline, art_style)

        # 4. Assemble layout data structure
        layout = build_comic_layout(outline, story, image_paths)

        # 5. Compile story metadata
        story_title = f"{character_name}'s Quest in {setting}"
        story_metadata: Dict[str, Any] = {
            "title": story_title,
            "story_title": story_title,
            "character_name": character_name,
            "setting": setting,
            "tone": tone,
            "art_style": art_style,
        }

        # 6. Save publication PDF export (offloaded to thread)
        pdf_url = await asyncio.to_thread(save_pdf, layout, story_metadata)
    except Exception as exc:
        logger.error("Comic HTML generation pipeline failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Comic generation failed: {str(exc)}",
        ) from exc

    return templates.TemplateResponse(
        request=request,
        name="comic_preview.html",
        context={
            "request": request,
            "layout": layout,
            "story_metadata": story_metadata,
            "pdf_url": pdf_url,
        },
    )


@router.post("/generate-comic/json", response_model=ComicResponse)
async def generate_comic_json(req: PromptRequest):
    """Execute the comic generation pipeline via JSON REST API.

    Returns structured JSON containing panel metadata, image URLs, and PDF link.
    """
    logger.info("Generating comic via JSON API for character '%s'", req.character_name)

    try:
        outline = await asyncio.to_thread(
            generate_outline,
            req.prompt,
            req.character_name,
            req.setting,
            req.tone,
            req.art_style,
        )
        story = await asyncio.to_thread(generate_story, outline, req.character_name, req.tone)
        image_paths = await generate_all_panels(outline, req.art_style)
        layout = build_comic_layout(outline, story, image_paths)

        story_title = f"{req.character_name}'s Quest in {req.setting}"
        story_metadata: Dict[str, Any] = {
            "title": story_title,
            "story_title": story_title,
            "character_name": req.character_name,
            "setting": req.setting,
            "tone": req.tone,
            "art_style": req.art_style,
        }

        pdf_url = await asyncio.to_thread(save_pdf, layout, story_metadata)

        comic_panels = [
            ComicPanel(**panel) if isinstance(panel, dict) else panel
            for panel in layout
        ]
    except Exception as exc:
        logger.error("Comic JSON generation pipeline failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Comic generation failed: {str(exc)}",
        ) from exc

    return ComicResponse(
        status="success",
        story_title=story_title,
        character_name=req.character_name,
        setting=req.setting,
        tone=req.tone,
        art_style=req.art_style,
        layout=comic_panels,
        pdf_url=pdf_url,
    )


@router.get("/test-image")
def test_image(
    prompt: str = Query(...),
    art_style: str = Query("Classic Comic Book"),
):
    """Developer testing endpoint to generate a single panel illustration."""
    try:
        saved_path = generate_image(prompt=prompt, panel_number=1, art_style=art_style)
        filename = Path(saved_path).name
        return {
            "status": "success",
            "prompt": prompt,
            "art_style": art_style,
            "image_url": f"/static/panels/{filename}",
        }
    except Exception as exc:
        logger.error("Single panel image generation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Image generation failed: {str(exc)}",
        ) from exc


@router.get("/export-success", response_class=HTMLResponse)
async def get_export_success(
    request: Request,
    pdf_path: str = Query(DEFAULT_EXPORT_PDF),
):
    """Render export completion confirmation screen with direct PDF download link."""
    if not pdf_path or not pdf_path.startswith("/static/exports/") or ".." in pdf_path or ":" in pdf_path:
        logger.warning(
            "Invalid or suspicious pdf_path '%s' provided to /export-success, sanitizing to default.",
            pdf_path,
        )
        pdf_path = DEFAULT_EXPORT_PDF

    return templates.TemplateResponse(
        request=request,
        name="export_success.html",
        context={
            "request": request,
            "pdf_path": pdf_path,
        },
    )


# Backward compatibility alias
export_success = get_export_success
