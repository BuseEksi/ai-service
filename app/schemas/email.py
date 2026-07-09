from pydantic import BaseModel


class EmailSummaryItem(BaseModel):
    id: str
    sender: str
    subject: str
    summary: str
    action_required: bool
    action_reason: str | None = None


class EmailSummaryResponse(BaseModel):
    total: int
    action_required_count: int
    items: list[EmailSummaryItem]
