from fastapi import APIRouter

from app.ai.providers import get_ollama_models, run_chat
from app.schemas.ai import AIChatRequest, AIChatResponse, AIModelsResponse

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.get("/models", response_model=AIModelsResponse)
def list_local_models() -> AIModelsResponse:
    return AIModelsResponse(models=get_ollama_models())


@router.post("/chat", response_model=AIChatResponse)
def chat(request: AIChatRequest) -> AIChatResponse:
    return AIChatResponse(answer=run_chat(request))
