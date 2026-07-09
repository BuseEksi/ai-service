"""

"""
import base64
import os
from email.message import EmailMessage

from pydantic import BaseModel, Field

from app.tools.base import BaseTool
from app.utils.logger import get_logger

logger = get_logger(__name__)


SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly"
]


class GmailToolSchema(BaseModel):
    to: str = Field(..., description="E-postanın gönderileceği kişinin mail adresi.")
    subject: str = Field(..., description="E-postanın konusu.")
    body: str = Field(..., description="E-postanın içeriği.")


class GmailTool(BaseTool):
    name = "send_gmail"
    description = "Belirtilen e-posta adresine, belirtilen konu ve içerikle e-posta gönderir."
    args_schema = GmailToolSchema

    def __init__(self, credentials_path: str, token_path: str):
        self._credentials_path = credentials_path
        self._token_path = token_path

    def _get_service(self):
        if not os.path.exists(self._credentials_path):
            logger.warning("'%s' bulunamadı, yetkilendirme yapılamaz.", self._credentials_path)
            return None

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
                flow = InstalledAppFlow.from_client_secrets_file(self._credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self._token_path, "w") as token_file:
                token_file.write(creds.to_json())

        return build("gmail", "v1", credentials=creds)

    async def run(self, to: str, subject: str, body: str, **kwargs) -> str:
        service = self._get_service()
        if service is None:
            return "Hata: credentials.json bulunamadı. Mock (test) ortamında gerçek mail gönderilemez."

        try:
            # E-posta mesajını oluştur
            message = EmailMessage()
            message.set_content(body)
            message["To"] = to
            message["Subject"] = subject

            # Google API'nin beklediği base64 formatına çevir
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": encoded_message}

            # Maili gönder
            send_message = service.users().messages().send(userId="me", body=create_message).execute()
            logger.info("E-posta başarıyla gönderildi. Message Id: %s", send_message["id"])

            return f"{to} adresine '{subject}' konulu e-posta başarıyla gönderildi."

        except Exception as e:
            logger.error("E-posta gönderilirken hata: %s", e)
            return f"E-posta gönderilemedi. Hata: {str(e)}"