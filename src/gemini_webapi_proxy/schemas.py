from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: dict[str, Any]


class ModelObject(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str = "google"
    capabilities: dict[str, bool] = Field(default_factory=dict)


class ModelListResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[ModelObject]


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: dict[str, Any]
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: dict[str, int] = Field(
        default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    )


class ImageGenerationRequest(BaseModel):
    model: str
    prompt: str
    n: int = 1
    size: str | None = "1024x1024"
    response_format: Literal["url", "b64_json"] | None = "url"
    # Studio OpenAI-compatible reference images: a data URL or http(s) URL array
    image: list[str] | str | None = None
    extra_body: dict[str, Any] | None = None


class ImageGenerationData(BaseModel):
    url: str | None = None
    b64_json: str | None = None
    revised_prompt: str | None = None


class ImageGenerationResponse(BaseModel):
    created: int
    data: list[ImageGenerationData]
