"""Tests for comic layout builder service."""

from pathlib import Path
import pytest
from app.schemas import ComicPanel, PanelOutline, PanelStory
from app.services.layout_builder import build_comic_layout


def test_build_comic_layout_basic_dicts():
    outline = [
        {
            "panel": 1,
            "title": "The Awakening",
            "scene_description": "Hero wakes up in a glowing cave.",
            "image_prompt": "A glowing cave with blue crystals.",
        },
        {
            "panel": 2,
            "title": "The Discovery",
            "scene_description": "Hero finds an ancient stone tablet.",
            "image_prompt": "Hero holding an ancient engraved stone.",
        },
        {
            "panel": 3,
            "title": "The Threat",
            "scene_description": "Shadow monster approaches.",
            "image_prompt": "Dark shadow beast with red eyes.",
        },
        {
            "panel": 4,
            "title": "The Clash",
            "scene_description": "Hero battles the monster.",
            "image_prompt": "Hero striking the shadow beast with light sword.",
        },
        {
            "panel": 5,
            "title": "The Victory",
            "scene_description": "Hero stands victorious under the sun.",
            "image_prompt": "Hero standing at cave entrance facing sunrise.",
        },
    ]

    story_elements = [
        {
            "panel": 1,
            "caption": "Deep beneath the earth...",
            "narration": "A dormant power awoke.",
            "dialogue": "Hero: Where am I?",
        },
        {
            "panel": 2,
            "caption": "A forgotten language.",
            "narration": "The runes pulsed with warmth.",
            "dialogue": "Hero: This tablet speaks of an ancient light.",
        },
        {
            "panel": 3,
            "caption": "Divergence.",
            "narration": "The ground trembled violently.",
            "dialogue": "Hero: What is that sound?",
        },
        {
            "panel": 4,
            "caption": "Direct combat.",
            "narration": "The blade flared with radiant solar fury.",
            "dialogue": "Hero: Begone back to shadows!",
        },
        {
            "panel": 5,
            "caption": "Dawn breaks.",
            "narration": "Peace returned to the realm.",
            "dialogue": "Hero: The journey has only begun.",
        },
    ]

    image_paths = [
        "app/static/panels/panel_1.png",
        "app/static/panels/panel_2.png",
        "app/static/panels/panel_3.png",
        "app/static/panels/panel_4.png",
        "app/static/panels/panel_5.png",
    ]

    layout = build_comic_layout(outline, story_elements, image_paths)

    assert len(layout) == 5
    for i, item in enumerate(layout):
        assert isinstance(item, dict)
        panel_obj = ComicPanel(**item)
        assert panel_obj.panel == i + 1
        assert panel_obj.title == outline[i]["title"]
        assert panel_obj.scene_description == outline[i]["scene_description"]
        assert panel_obj.caption == story_elements[i]["caption"]
        assert panel_obj.narration == story_elements[i]["narration"]
        assert panel_obj.dialogue == story_elements[i]["dialogue"]
        assert panel_obj.image_prompt == outline[i]["image_prompt"]
        assert panel_obj.image_path == image_paths[i]
        assert panel_obj.image_url == f"/static/panels/panel_{i+1}.png"


def test_build_comic_layout_image_url_normalization():
    outline = [{"panel": 1, "title": "Intro"}]
    story = [{"panel": 1, "caption": "Once upon a time"}]
    image_paths = ["C:\\path\\to\\comic\\assets\\generated_panel_01.png"]

    layout = build_comic_layout(outline, story, image_paths)
    assert len(layout) == 1
    assert layout[0]["image_url"] == "/static/panels/generated_panel_01.png"
    assert layout[0]["image_path"] == "C:\\path\\to\\comic\\assets\\generated_panel_01.png"


def test_build_comic_layout_empty_image_fallback():
    outline = [{"panel": 1, "title": "Intro"}]
    story = [{"panel": 1, "caption": "Start"}]

    # Empty list
    layout = build_comic_layout(outline, story, [])
    assert len(layout) == 1
    assert layout[0]["image_url"] == "/static/panels/placeholder.png"
    assert layout[0]["image_path"] == ""

    # Empty string inside list
    layout2 = build_comic_layout(outline, story, [""])
    assert len(layout2) == 1
    assert layout2[0]["image_url"] == "/static/panels/placeholder.png"
    assert layout2[0]["image_path"] == ""

    # Whitespace inside list
    layout3 = build_comic_layout(outline, story, ["   "])
    assert len(layout3) == 1
    assert layout3[0]["image_url"] == "/static/panels/placeholder.png"
    assert layout3[0]["image_path"] == ""


def test_build_comic_layout_pydantic_models():
    outline_models = [
        PanelOutline(
            panel=1,
            title="Scene 1",
            scene_description="Description 1",
            image_prompt="Prompt 1",
        ),
        PanelOutline(
            panel=2,
            title="Scene 2",
            scene_description="Description 2",
            image_prompt="Prompt 2",
        ),
    ]

    story_models = [
        PanelStory(
            panel=1,
            caption="Cap 1",
            narration="Narr 1",
            dialogue="Dial 1",
        ),
        PanelStory(
            panel=2,
            caption="Cap 2",
            narration="Narr 2",
            dialogue="Dial 2",
        ),
    ]

    image_paths = [
        "app/static/panels/panel_1.png",
        "app/static/panels/panel_2.png",
    ]

    layout = build_comic_layout(outline_models, story_models, image_paths)
    assert len(layout) == 2
    assert layout[0]["panel"] == 1
    assert layout[0]["title"] == "Scene 1"
    assert layout[0]["caption"] == "Cap 1"
    assert layout[1]["panel"] == 2
    assert layout[1]["title"] == "Scene 2"
    assert layout[1]["caption"] == "Cap 2"


def test_build_comic_layout_out_of_order_matching():
    outline = [
        {"panel": 1, "title": "P1"},
        {"panel": 2, "title": "P2"},
    ]
    # story elements passed in reverse order (panel 2 first)
    story = [
        {"panel": 2, "caption": "Story for 2"},
        {"panel": 1, "caption": "Story for 1"},
    ]
    image_paths = ["p1.png", "p2.png"]

    layout = build_comic_layout(outline, story, image_paths)
    assert layout[0]["panel"] == 1
    assert layout[0]["caption"] == "Story for 1"
    assert layout[1]["panel"] == 2
    assert layout[1]["caption"] == "Story for 2"


def test_build_comic_layout_missing_and_mismatched_story():
    outline = [
        {"panel": 1, "title": "P1", "scene_description": "Desc 1"},
        {"panel": 2, "title": "P2", "scene_description": "Desc 2"},
        {"panel": 3, "title": "P3", "scene_description": "Desc 3"},
    ]
    # Only panel 1 provided, panel 2 and 3 missing
    story = [
        {"panel": 1, "caption": "Only panel 1 story"},
    ]
    image_paths = ["p1.png", "p2.png"]

    layout = build_comic_layout(outline, story, image_paths)
    assert len(layout) == 3

    # Panel 1 has story
    assert layout[0]["panel"] == 1
    assert layout[0]["caption"] == "Only panel 1 story"

    # Panel 2 missing story gracefully defaults
    assert layout[1]["panel"] == 2
    assert layout[1]["caption"] == ""
    assert layout[1]["narration"] == ""
    assert layout[1]["dialogue"] == ""
    assert layout[1]["title"] == "P2"

    # Panel 3 missing story and missing image gracefully defaults
    assert layout[2]["panel"] == 3
    assert layout[2]["caption"] == ""
    assert layout[2]["image_url"] == "/static/panels/placeholder.png"
    assert layout[2]["image_path"] == ""


def test_build_comic_layout_unkeyed_story_index_fallback():
    outline = [
        {"panel": 1, "title": "P1"},
        {"panel": 2, "title": "P2"},
    ]
    # Story dicts without "panel" key fallback to index
    story = [
        {"caption": "Index 0 story"},
        {"caption": "Index 1 story"},
    ]
    layout = build_comic_layout(outline, story, ["p1.png", "p2.png"])
    assert layout[0]["caption"] == "Index 0 story"
    assert layout[1]["caption"] == "Index 1 story"


def test_build_comic_layout_path_objects():
    outline = [{"panel": 1, "title": "P1"}]
    story = [{"panel": 1, "caption": "C1"}]
    image_paths = [Path("app/static/panels/path_obj.png")]

    layout = build_comic_layout(outline, story, image_paths)
    assert layout[0]["image_url"] == "/static/panels/path_obj.png"
    assert "path_obj.png" in layout[0]["image_path"]
