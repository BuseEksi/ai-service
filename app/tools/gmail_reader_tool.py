"""
Gmail'den son e-postaları okuyan tool.

Kullanım için Google Cloud Console'dan bir OAuth Client ID (Desktop app)
oluşturup indirdiğin credentials.json dosyasını proje köküne koyman gerekir.
İlk çalıştırmada tarayıcı açılıp izin isteyecek, sonrasında token.json
dosyasına kaydedilip otomatik yenilenir.

credentials.json henüz yoksa bu tool otomatik olarak mock (örnek) verilerle
çalışır - böylece OAuth kurulumunu bitirmeden pipeline'ın geri kalanını
(özetleme, aksiyon tespiti, API response'u) test edebilirsin.
"""
import base64
import json
import os
from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from app.tools.base import BaseTool
from app.utils.logger import get_logger
from app.utils.text import fix_mojibake

logger = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly"
]


# 1. LLM için Pydantic şemasını ekliyoruz
class GmailReaderSchema(BaseModel):
    limit: int = Field(default=5, description="Okunacak maksimum e-posta sayısı.")
    query: str = Field(default="is:unread",
                       description="Gmail arama sorgusu. Örn: 'is:unread', 'from:boss@company.com'")


class GmailReaderTool(BaseTool):
    name = "list_recent_emails"
    description = "Gmail gelen kutusundan son e-postaları okur ve içeriklerini getirir. Mailleri özetlemek veya kontrol etmek için bu aracı kullan."

    # 2. Şemayı araca bağlıyoruz
    args_schema = GmailReaderSchema

    def __init__(self, credentials_path: str, token_path: str):
        self._credentials_path = credentials_path
        self._token_path = token_path

    def _get_service(self):
        """
        Gmail API servisini kurar. credentials.json yoksa None döner,
        böylece çağıran taraf mock veriye düşer.
        """
        if not os.path.exists(self._credentials_path):
            logger.warning(
                "'%s' bulunamadı, mock e-posta verisi kullanılacak.",
                self._credentials_path,
            )
            return None

        # Google kütüphaneleri sadece gerçekten gerektiğinde import edilir,
        # böylece credentials.json olmayan kurulumlarda bu paketler
        # zorunlu bağımlılık haline gelmez.
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None
        if os.path.exists(self._token_path):
            creds = Credentials.from_authorized_user_file(self._token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(self._token_path, "w") as token_file:
                token_file.write(creds.to_json())

        return build("gmail", "v1", credentials=creds)

    @staticmethod
    def _extract_body(payload: dict) -> str:
        """Mesaj gövdesinden düz metni çıkarır (multipart mailleri de gezer)."""
        if payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
            data = payload["body"]["data"]
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

        for part in payload.get("parts", []):
            text = GmailReaderTool._extract_body(part)
            if text:
                return text
        return ""

    def _fetch_from_gmail(self, service, limit: int, query: str) -> list[dict]:
        results = (
            service.users()
            .messages()
            .list(userId="me", maxResults=limit, q=query)
            .execute()
        )
        messages = results.get("messages", [])
        emails = []
        for msg in messages:
            full = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="full")
                .execute()
            )
            headers = {h["name"]: h["value"] for h in full["payload"]["headers"]}
            body = self._extract_body(full["payload"]) or full.get("snippet", "")
            emails.append(
                {
                    "id": msg["id"],
                    "sender": fix_mojibake(headers.get("From", "")),
                    "subject": fix_mojibake(headers.get("Subject", "(konu yok)")),
                    "date": headers.get("Date", ""),
                    "body": fix_mojibake(body)[:3000],
                    # LLM'e aşırı uzun gövde göndermemek için kırp
                }
            )
        return emails

    def _mock_emails(self, limit: int) -> list[dict]:
        now = datetime.now()
        samples = [
            {
                "id": "mock-1",
                "sender": "Ali Baran <ali.baran@argeset.com>",
                "subject": "LBYS modülü için mockup revizyonu",
                "date": (now - timedelta(hours=2)).isoformat(),
                "body": (
                    "Merhaba, LBYS numune kabul modülündeki mockup'ı gözden geçirdim. "
                    "Yarın öğlene kadar revize edip tekrar gönderebilir misin? "
                    "Müşteri toplantısı öğleden sonra saat 15:00'te."
                ),
            },
            {
                "id": "mock-2",
                "sender": "SetXRM Bildirim <no-reply@setxrm.com>",
                "subject": "Haftalık sistem bakım bildirimi",
                "date": (now - timedelta(hours=5)).isoformat(),
                "body": (
                    "Bu hafta sonu 02:00-04:00 arası planlı bakım yapılacaktır. "
                    "Herhangi bir aksiyon gerekmemektedir."
                ),
            },
            {
                "id": "mock-3",
                "sender": "İK <ik@argeset.com>",
                "subject": "Staj sözleşmeniz için imza bekleniyor",
                "date": (now - timedelta(days=1)).isoformat(),
                "body": (
                    "Staj sözleşmenizin ıslak imzalı halini bu Cuma'ya kadar "
                    "İK ofisine teslim etmeniz gerekmektedir."
                ),
            },
            {
                "id": "mock-4",
                "sender": "LinkedIn <notifications@linkedin.com>",
                "subject": "3 kişi profilinizi görüntüledi",
                "date": (now - timedelta(days=2)).isoformat(),
                "body": "Bu hafta profilinizi görüntüleyen kişileri görün.",
            },
        ]
        return samples[:limit]

    async def fetch_recent(self, limit: int = 10, query: str = "is:unread") -> list[dict]:
        service = self._get_service()
        if service is None:
            return self._mock_emails(limit)
        return self._fetch_from_gmail(service, limit=limit, query=query)

    # 3. run metodunu LLM'e okunabilir veri dönecek şekilde güncelledik
    async def run(self, limit: int = 5, query: str = "is:unread", **kwargs) -> str:
        emails = await self.fetch_recent(limit=limit, query=query)

        if not emails:
            return "Kriterlere uygun e-posta bulunamadı."

        # LLM'in anlayabilmesi için mailleri JSON formatında string olarak dönüyoruz
        formatted_emails = []
        for e in emails:
            formatted_emails.append({
                "Kimden": e["sender"],
                "Tarih": e["date"],
                "Konu": e["subject"],
                "İçerik": e["body"][:500] + "..." if len(e["body"]) > 500 else e["body"]
            })

        return json.dumps(formatted_emails, ensure_ascii=False)