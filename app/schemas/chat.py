"""API katmanının kullandığı request/response şemaları."""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Kullanıcının mesajı")
    session_id: str | None = Field(
        default=None, description="Konuşma oturumu kimliği (opsiyonel)"
    )


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[str] = Field(
        default_factory=list, description="Bu turda kullanılan tool isimleri"
    )
    session_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    app_name: str
    llm_provider: str
