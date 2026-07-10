"""Agent katmanının ortak arayüzü."""
from abc import ABC, abstractmethod

from app.schemas.chat import ChatResponse


class BaseAgent(ABC):
    @abstractmethod
    async def handle(
        self,
        message: str,
        session_id: str | None,
        attachment_path: str | None = None,
    ) -> ChatResponse:
        raise NotImplementedError