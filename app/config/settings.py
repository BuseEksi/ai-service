"""
Merkezi konfigürasyon yönetimi.
Tüm ortam değişkenleri buradan okunur, kodun başka hiçbir yerinde
doğrudan os.environ kullanılmaz. Böylece config kaynağı tek yerden yönetilir.
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Mevcut ayarların burada duruyor olmalı (APP_NAME, DEBUG vb.)
    APP_NAME: str = "AI Service"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # --- Faz 6: Authentication ---
    # .env içinde virgülle ayrılmış birden fazla key tanımlanabilir:
    # API_KEYS=argeset-dev-key,ceng-abi-key
    # Böylece her tüketici (n8n, SetXRM, manuel test) ayrı key kullanabilir
    # ve gerekirse tek bir key iptal edilebilir.
    # NOT: pydantic-settings, list[str] tipindeki alanları env'den JSON
    # olarak parse etmeye çalışır (virgüllü düz string'i JSON sanıp hata
    # verir). Bu yüzden ham string olarak tutup API_KEYS property'siyle
    # split ediyoruz.
    API_KEYS_RAW: str = Field(default="", validation_alias="API_KEYS")

    @property
    def API_KEYS(self) -> list[str]:
        return [key.strip() for key in self.API_KEYS_RAW.split(",") if key.strip()]

    # LLM Sağlayıcı Seçimi
    LLM_PROVIDER: str = "mock"

    # --- Anthropic Ayarları ---
    ANTHROPIC_API_KEY: str | None = None

    # --- Mistral Ayarları ---
    MISTRAL_API_KEY: str | None = None
    MISTRAL_MODEL: str = "mistral-large-latest"

    # --- OpenAI Ayarları ---
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

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
