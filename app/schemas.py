from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, AliasChoices


class PromptRequest(BaseModel):
    """User input payload for comic generation."""

    model_config = ConfigDict(populate_by_name=True)

    prompt: str = Field(..., min_length=3, description="Story premise or idea")
    character_name: str = Field(default="Hero", description="Main character name")
    setting: str = Field(default="Enchanted Forest", description="Story setting or world")
    tone: str = Field(default="Dramatic", description="Narrative mood or tone")
    art_style: str = Field(
        default="Classic Comic Book",
        validation_alias=AliasChoices("art_style", "style"),
        description="Visual art style for comic illustrations",
    )


class PanelOutline(BaseModel):
    """Structured outline plan for an individual comic panel."""

    panel: int = Field(..., ge=1, le=5, description="Panel index (1 through 5)")
    title: str = Field(..., description="Panel heading or scene title")
    scene_description: str = Field(..., description="Visual scene summary")
    image_prompt: str = Field(..., description="Diffusion generation prompt")


class PanelStory(BaseModel):
    """Narrative script and dialogue for an individual comic panel."""

    panel: int = Field(..., description="Panel index")
    caption: str = Field(default="", description="Narrator caption box text")
    narration: str = Field(default="", description="Story narration text")
    dialogue: str = Field(default="", description="Character speech dialogue")


class ComicPanel(BaseModel):
    """Consolidated panel representation combining outline, story, and image data."""

    panel: int = Field(..., description="Panel index")
    title: str = Field(default="", description="Panel title")
    scene_description: str = Field(default="", description="Visual scene description")
    caption: str = Field(default="", description="Panel caption")
    narration: str = Field(default="", description="Panel narration")
    dialogue: str = Field(default="", description="Character dialogue")
    image_prompt: str = Field(default="", description="Synthesized image prompt")
    image_path: str = Field(default="", description="Local file path on disk")
    image_url: str = Field(default="", description="Web-accessible image URL")


class ComicResponse(BaseModel):
    """Standardized API response for generated comic book."""

    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(default="success", description="Response status")
    story_title: str = Field(..., description="Generated comic story title")
    character_name: str = Field(default="Hero", description="Protagonist name")
    setting: str = Field(default="Enchanted Forest", description="Story setting")
    tone: str = Field(default="Dramatic", description="Story tone")
    art_style: str = Field(
        default="Classic Comic Book",
        validation_alias=AliasChoices("art_style", "style"),
        description="Art style",
    )
    layout: List[ComicPanel] = Field(
        default_factory=list, description="List of comic panels"
    )
    pdf_url: str = Field(default="", description="Exported PDF download URL")
