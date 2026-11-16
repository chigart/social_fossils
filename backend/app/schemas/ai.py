from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

class AIMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AIChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["ollama", "openai-compatible"]
    model: str = Field(min_length=1, max_length=200)
    messages: list[AIMessage] = Field(min_length=1, max_length=20)
    api_key: str | None = None
    base_url: str | None = Field(default=None, max_length=1000)


class AIChatResponse(BaseModel):
    answer: str


class AIModelsResponse(BaseModel):
    models: list[str]
