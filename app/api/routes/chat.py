from fastapi import APIRouter, Depends, HTTPException

from app.agents.base import BaseAgent
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.dependencies import get_agent
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: BaseAgent = Depends(get_agent),
) -> ChatResponse:
    try:
        return await agent.handle(message=request.message, session_id=request.session_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat isteği işlenirken hata oluştu")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
