"""
Merkezi konfigürasyon yönetimi.
Tüm ortam değişkenleri buradan okunur, kodun başka hiçbir yerinde
doğrudan os.environ kullanılmaz. Böylece config kaynağı tek yerden yönetilir.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Mevcut ayarların burada duruyor olmalı (APP_NAME, DEBUG vb.)
    APP_NAME: str = "AI Service"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # LLM Sağlayıcı Seçimi
    LLM_PROVIDER: str = "mock"

    # --- Anthropic Ayarları ---
    ANTHROPIC_API_KEY: str | None = None

    # --- Mistral Ayarları ---
    MISTRAL_API_KEY: str | None = None
    MISTRAL_MODEL: str = "mistral-large-latest"

    #---- Başka AI eklenmek istenirse buraya eklenir ----


    # --------------------------------------------

    # --- Diğer ayarlar (Gmail vb.) ---
    GMAIL_CREDENTIALS_PATH: str = "credentials.json"
    GMAIL_TOKEN_PATH: str = "token.json"

    # --- Slack ---
    SLACK_BOT_TOKEN: str

    #--- Employee DB---
    EMPLOYEE_DB_PATH: str = "employees.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def get_settings() -> Settings:
    return Settings()



def get_settings() -> Settings:
    """Settings nesnesini uygulama boyunca tek sefer oluşturup cache'ler."""
    return Settings()
