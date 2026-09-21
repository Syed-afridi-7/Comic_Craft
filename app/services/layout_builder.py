"""Layout builder service for ComicCraft.

Merges outlines, narrative story elements, and generated image paths
into a unified list of comic panels conforming to ComicPanel schema.
"""

from pathlib import Path
from typing import Any, Dict, List, Union
from app.schemas import ComicPanel


def _to_dict(item: Any) -> Dict[str, Any]:
    """Convert a dictionary or Pydantic model into a dictionary."""
    if hasattr(item, "model_dump") and callable(getattr(item, "model_dump")):
        return item.model_dump()
    if hasattr(item, "dict") and callable(getattr(item, "dict")):
        return item.dict()
    if isinstance(item, dict):
        return dict(item)
    return {}


def build_comic_layout(
    outline: List[Union[Dict[str, Any], Any]],
    story_elements: List[Union[Dict[str, Any], Any]],
    image_paths: List[Union[str, Path]],
) -> List[Dict[str, Any]]:
    """Build a cohesive comic layout from outline, story elements, and image paths.

    Args:
        outline: List of panel outlines (dicts or Pydantic models).
        story_elements: List of panel story elements (dicts or Pydantic models).
        image_paths: List of file system image paths or Path objects.

    Returns:
        List of dictionaries conforming to the ComicPanel schema.
    """
    converted_outline = [_to_dict(item) for item in (outline or [])]
    converted_story = [_to_dict(item) for item in (story_elements or [])]

    # Index story elements by panel ID (1..5) when available
    story_by_panel: Dict[int, Dict[str, Any]] = {}
    for item in converted_story:
        raw_p = item.get("panel")
        if raw_p is not None:
            try:
                story_by_panel[int(raw_p)] = item
            except (ValueError, TypeError):
                pass

    layout: List[Dict[str, Any]] = []

    for idx, outline_item in enumerate(converted_outline):
        raw_panel = outline_item.get("panel")
        try:
            panel_num = int(raw_panel) if raw_panel is not None else (idx + 1)
        except (ValueError, TypeError):
            panel_num = idx + 1

        # Match story element: first by panel ID, fallback by index
        story_item: Dict[str, Any] = {}
        if panel_num in story_by_panel:
            story_item = story_by_panel[panel_num]
        elif idx < len(converted_story):
            story_item = converted_story[idx]

        # Process image path and relative web URL
        image_path_str = ""
        if image_paths and idx < len(image_paths):
            raw_img = image_paths[idx]
            if raw_img is not None:
                image_path_str = str(raw_img).strip()

        if image_path_str:
            filename = Path(image_path_str).name
            if filename:
                image_url = f"/static/panels/{filename}"
            else:
                image_url = "/static/panels/placeholder.png"
        else:
            image_path_str = ""
            image_url = "/static/panels/placeholder.png"

        panel_dict = {
            "panel": panel_num,
            "title": str(outline_item.get("title") or ""),
            "scene_description": str(outline_item.get("scene_description") or ""),
            "caption": str(story_item.get("caption") or ""),
            "narration": str(story_item.get("narration") or ""),
            "dialogue": str(story_item.get("dialogue") or ""),
            "image_prompt": str(outline_item.get("image_prompt") or ""),
            "image_path": image_path_str,
            "image_url": image_url,
        }

        # Validate against ComicPanel and convert to standard dict
        panel_obj = ComicPanel(**panel_dict)
        layout.append(panel_obj.model_dump())

    return layout
