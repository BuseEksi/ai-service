from fastapi import APIRouter, Depends

from app.config.settings import Settings, get_settings
from app.schemas.chat import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        llm_provider=settings.LLM_PROVIDER,
    )
