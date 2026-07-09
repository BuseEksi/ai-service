"""Slack'e mesaj gönderen tool."""
import httpx

from app.tools.base import BaseTool


class SlackTool(BaseTool):
    def __init__(self, bot_token: str, default_channel: str = "social"):
        self.name = "send_slack_message"
        self._bot_token = bot_token
        self._default_channel = default_channel
        self._base_url = "https://slack.com/api/chat.postMessage"

    def get_tool_schema(self) -> dict:
        return {
            "name": "send_slack_message",
            "description": "Slack'te belirtilen kanala mesaj gönderir.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "channel": {
                        "type": "string",
                        "description": "Mesajın gönderileceği kanal adı (belirtilmezse varsayılan kanal kullanılır)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Gönderilecek mesaj içeriği"
                    }
                },
                "required": ["message"]
            }
        }

    async def run(self, message: str, channel: str | None = None) -> str:
        target_channel = channel or self._default_channel
        headers = {"Authorization": f"Bearer {self._bot_token}"}
        payload = {"channel": target_channel, "text": message}

        async with httpx.AsyncClient() as client:
            response = await client.post(self._base_url, headers=headers, json=payload)
            data = response.json()

        if not data.get("ok"):
            error = data.get("error", "bilinmeyen hata")
            return f"Slack mesajı gönderilemedi: {error}"

        return f"Mesaj #{target_channel} kanalına gönderildi."