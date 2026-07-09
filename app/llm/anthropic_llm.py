import anthropic
from typing import Any
from app.llm.base import BaseLLM
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AnthropicLLM(BaseLLM):
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate(
            self,
            messages: list[dict[str, Any]],
            system: str | None = None,
            tools: list[dict[str, Any]] | None = None
    ) -> str | dict[str, Any]:

        kwargs = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        if tools:
            # Pydantic'ten ürettiğimiz şemaları Anthropic'in istediği formata basıyoruz
            kwargs["tools"] = tools

        response = await self.client.messages.create(**kwargs)

        # Eğer model bir tool kullanmaya karar verdiyse
        for content in response.content:
            if content.type == "tool_use":
                logger.info("LLM Tool seçti: %s", content.name)
                return {
                    "type": "tool_use",
                    "name": content.name,
                    "input": content.input,
                    "id": content.id
                }

        # Düz metin cevabı verdiyse
        return response.content[0].text