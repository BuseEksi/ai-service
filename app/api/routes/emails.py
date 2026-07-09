from fastapi import APIRouter, Depends, HTTPException

from app.schemas.email import EmailSummaryResponse
from app.services.dependencies import get_email_summarizer
from app.services.email_summarizer import EmailSummarizerService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["emails"])


@router.get("/emails/summary", response_model=EmailSummaryResponse)
async def summarize_emails(
    limit: int = 10,
    query: str = "is:unread",
    summarizer: EmailSummarizerService = Depends(get_email_summarizer),
) -> EmailSummaryResponse:
    """
    Son `limit` e-postayı okur, her biri için kısa özet çıkarır ve
    aksiyon gerektirenleri işaretler.

    `query`: Gmail arama sözdizimi (ör. "is:unread", "from:abc@mail.com").
    credentials.json henüz kurulmadıysa otomatik olarak örnek (mock) mailler
    üzerinden çalışır.
    """
    try:
        return await summarizer.summarize_recent(limit=limit, query=query)
    except Exception as exc:
        logger.exception("E-posta özetleme sırasında hata oluştu")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
