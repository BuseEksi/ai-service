"""
Uygulamanın giriş noktası.
API katmanı sadece HTTP ile ilgilenir; AI mantığının nasıl çalıştığını bilmez.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config.settings import get_settings
from app.services import memory_service

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    return {"message": f"{settings.APP_NAME} çalışıyor. /docs adresine bakabilirsin."}



@app.on_event("startup")
async def startup_event():
    memory_service.init_db()
