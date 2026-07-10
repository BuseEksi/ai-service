"""

"""
import base64
import os
import mimetypes
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
    attachment_path: str | None = Field(
        default=None,
        description="Eklenecek dosyanın sunucu üzerindeki geçici yol bilgisi. "
                     "Kullanıcı bir dosya yüklediyse ve mail ile göndermek istiyorsa doldurulur."
    )


class GmailTool(BaseTool):
    name = "send_gmail"
    description = (
        "Belirtilen e-posta adresine, belirtilen konu ve içerikle e-posta gönderir. "
        "Eğer kullanıcı bir dosya (PDF vb.) paylaştıysa ve mail ile göndermek istiyorsa "
        "attachment_path parametresi ile dosya ek olarak gönderilir."
    )
    args_schema = GmailToolSchema

    def __init__(self, credentials_path: str, token_path: str):
        self._credentials_path = credentials_path
        self._token_path = token_path

    def _get_service(self):
        # ... (değişmedi, aynı kalıyor)
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

    def _attach_file(self, message: EmailMessage, attachment_path: str):
        if not os.path.exists(attachment_path):
            raise FileNotFoundError(f"Ek dosya bulunamadı: {attachment_path}")

        mime_type, _ = mimetypes.guess_type(attachment_path)
        if mime_type is None:
            mime_type = "application/octet-stream"
        main_type, sub_type = mime_type.split("/", 1)

        with open(attachment_path, "rb") as f:
            file_data = f.read()

        filename = os.path.basename(attachment_path)
        message.add_attachment(
            file_data,
            maintype=main_type,
            subtype=sub_type,
            filename=filename
        )

    async def run(
        self,
        to: str,
        subject: str,
        body: str,
        attachment_path: str | None = None,
        **kwargs
    ) -> str:
        service = self._get_service()
        if service is None:
            return "Hata: credentials.json bulunamadı. Mock (test) ortamında gerçek mail gönderilemez."

        try:
            message = EmailMessage()
            message.set_content(body)
            message["To"] = to
            message["Subject"] = subject

            if attachment_path:
                self._attach_file(message, attachment_path)

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": encoded_message}

            send_message = service.users().messages().send(userId="me", body=create_message).execute()
            logger.info("E-posta başarıyla gönderildi. Message Id: %s", send_message["id"])

            attachment_note = f" (ek: {os.path.basename(attachment_path)})" if attachment_path else ""
            return f"{to} adresine '{subject}' konulu e-posta{attachment_note} başarıyla gönderildi."

        except FileNotFoundError as e:
            logger.error("Ek dosya hatası: %s", e)
            return f"E-posta gönderilemedi. {str(e)}"
        except Exception as e:
            logger.error("E-posta gönderilirken hata: %s", e)
            return f"E-posta gönderilemedi. Hata: {str(e)}"