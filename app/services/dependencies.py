"""
FastAPI'nin Depends() mekanizması ile kullanılan servis üretim fonksiyonları.
API katmanı bu fonksiyonlar sayesinde LLM/Agent'ın nasıl kurulduğunu bilmez.
"""
from functools import lru_cache

from app.agents.base import BaseAgent
from app.agents.simple_agent import SimpleAgent
from app.config.settings import Settings, get_settings
from app.llm.factory import get_llm
from app.services.email_summarizer import EmailSummarizerService
from app.tools.gmail_reader_tool import GmailReaderTool


@lru_cache
def get_agent() -> BaseAgent:
    settings: Settings = get_settings()
    llm = get_llm(settings)
    return SimpleAgent(llm=llm)


@lru_cache
def get_gmail_reader_tool() -> GmailReaderTool:
    settings: Settings = get_settings()
    return GmailReaderTool(
        credentials_path=settings.GMAIL_CREDENTIALS_PATH,
        token_path=settings.GMAIL_TOKEN_PATH,
    )


@lru_cache
def get_email_summarizer() -> EmailSummarizerService:
    settings: Settings = get_settings()
    llm = get_llm(settings)
    return EmailSummarizerService(llm=llm, gmail_tool=get_gmail_reader_tool())


