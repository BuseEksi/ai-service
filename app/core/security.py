"""
Faz 6 - Authentication (API Key)

Basit ama gerçek bir API key doğrulaması. İstek header'ında `X-API-Key`
bekler ve Settings.API_KEYS içindeki değerlerle karşılaştırır.

Neden JWT değil de API Key:
- Bu servis şu an insan kullanıcı login akışına değil, servisler/dahili
  entegrasyonlar arası (n8n, diğer backend'ler) çağrılara maruz kalıyor.
  Bu senaryoda API key,
  JWT'nin login/refresh/expiry karmaşasını gerektirmeden aynı amacı
  (yetkisiz erişimi engellemek) daha az kod ve daha az operasyonel
  yükle karşılıyor.
- İleride gerçek kullanıcı bazlı yetkilendirme gerekirse (örn. Şirket
  kullanıcılarının kendi oturumlarıyla bu servise istek atması), bu
  dosyaya dokunmadan ayrı bir `verify_jwt` dependency'si eklenip
  ilgili route'larda kullanılabilir. Katmanlar birbirinden bağımsız.

Kullanım (route içinde):
    @router.post("/chat", dependencies=[Depends(verify_api_key)])

veya router.py içinde toplu olarak:
    api_router.include_router(chat.router, dependencies=[Depends(verify_api_key)])
"""
import hmac

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config.settings import Settings, get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_API_KEY_HEADER_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=_API_KEY_HEADER_NAME, auto_error=False)

def _is_valid_key(candidate: str, valid_keys: list[str]) -> bool:
    """
    Timing-attack'e karşı hmac.compare_digest ile sabit-zamanlı karşılaştırma.

    NOT: hmac.compare_digest, ASCII-dışı karakter içeren str'lerde
    TypeError fırlatır (örn. "ı" gibi). Bu yüzden karşılaştırmadan önce
    UTF-8 byte'a çeviriyoruz - hem hatayı önlüyor hem de rastgele
    Unicode key gönderilerek servisi 500'e düşürme (DoS) ihtimalini
    kapatıyor.
    """
    candidate_bytes = candidate.encode("utf-8")
    return any(
        hmac.compare_digest(candidate_bytes, key.encode("utf-8"))
        for key in valid_keys
        if key
    )


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> str:
    """
    Korumalı endpoint'ler için dependency. Geçerliyse key'i döner,
    değilse 401 fırlatır.
    """
    if not settings.API_KEYS:
        logger.error("API_KEYS ayarlanmamış; korumalı endpoint çağrılamıyor.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sunucu tarafında API key konfigürasyonu eksik.",
        )

    if not api_key or not _is_valid_key(api_key, settings.API_KEYS):
        logger.warning("Geçersiz veya eksik API key ile istek yapıldı.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya eksik API key.",
            headers={"WWW-Authenticate": _API_KEY_HEADER_NAME},
        )

    return api_key
