import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.agents.base import BaseAgent
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.dependencies import get_agent
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["chat"])

UPLOAD_DIR = "/tmp/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/chat/upload")
async def upload_file(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları kabul edilir.")

    file_id = f"{uuid.uuid4()}.pdf"
    save_path = os.path.join(UPLOAD_DIR, file_id)

    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    logger.info("Dosya yüklendi: %s", save_path)
    return {"attachment_path": save_path, "original_filename": file.filename}


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: BaseAgent = Depends(get_agent),
) -> ChatResponse:
    try:
        return await agent.handle(
            message=request.message,
            session_id=request.session_id,
            attachment_path=request.attachment_path,
        )
    except Exception as exc:
        logger.exception("Chat isteği işlenirken hata oluştu")
        raise HTTPException(status_code=500, detail=str(exc)) from exc