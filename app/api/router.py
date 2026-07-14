from fastapi import APIRouter, Depends

from app.api.routes import chat, emails, health
from app.core.security import verify_api_key

api_router = APIRouter()

# /health kasıtlı olarak açık: monitoring/load balancer key taşımadan
# erişebilmeli.
api_router.include_router(health.router)

# Auth gerektiren route grupları:
api_router.include_router(chat.router, dependencies=[Depends(verify_api_key)])
api_router.include_router(emails.router, dependencies=[Depends(verify_api_key)])
