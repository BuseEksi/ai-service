import json
from typing import Any
from mistralai.client import Mistral
from app.llm.base import BaseLLM
from app.utils.logger import get_logger
import asyncio

logger = get_logger(__name__)


class MistralLLM(BaseLLM):
    def __init__(self, api_key: str, model: str = "mistral-large-latest"):
        # Mistral v1.x asenkron istemcisi
        self.client = Mistral(api_key=api_key)
        self.model = model

    def _format_tools_for_mistral(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Anthropic tarzı tool şemasını Mistral/OpenAI tarzına çevirir."""
        mistral_tools = []
        for tool in tools:
            mistral_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("input_schema", {})
                }
            })
        return mistral_tools

    async def generate(
            self,
            messages: list[dict[str, Any]],
            system: str | None = None,
            tools: list[dict[str, Any]] | None = None
    ) -> str | dict[str, Any]:

        # Sistem promptunu messages listesinin en başına ekliyoruz (Mistral formatı)
        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})

        # Agent'tan gelen geçmiş mesajları ekliyoruz
        for msg in messages:
            if msg["role"] == "user" and isinstance(msg.get("content"), list):
                # Tool sonucunu dönen mesaj formatını Mistral'e uyarlama
                for item in msg["content"]:
                    if item.get("type") == "tool_result":
                        formatted_messages.append({
                            "role": "tool",
                            "name": item.get("name", "tool"),
                            "content": item.get("content", ""),
                            "tool_call_id": item.get("tool_use_id", "")
                        })
            elif msg["role"] == "assistant" and isinstance(msg.get("content"), list):
                # Asistanın tool çağırma mesajını Mistral'e uyarlama
                tool_calls = []
                for item in msg["content"]:
                    if item.get("type") == "tool_use":
                        tool_calls.append({
                            "id": item.get("id"),
                            "type": "function",
                            "function": {
                                "name": item.get("name"),
                                "arguments": json.dumps(item.get("input", {}))
                            }
                        })
                formatted_messages.append({"role": "assistant", "tool_calls": tool_calls})
            else:
                formatted_messages.append({"role": msg["role"], "content": msg["content"]})

        kwargs = {
            "model": self.model,
            "messages": formatted_messages,
        }

        if tools:
            kwargs["tools"] = self._format_tools_for_mistral(tools)
            kwargs["tool_choice"] = "auto"


        # logger.info(json.dumps(kwargs, indent=2, ensure_ascii=False, default=str))
        # Mistral API'sine istek atıyoruz (Timeout + Retry)

        MAX_RETRIES = 3
        TIMEOUT = 30  # saniye

        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                logger.info(
                    "Mistral API çağrısı (%d/%d)",
                    attempt + 1,
                    MAX_RETRIES
                )

                response = await asyncio.wait_for(
                    self.client.chat.complete_async(**kwargs),
                    timeout=TIMEOUT
                )

                logger.info("Mistral API cevap verdi.")
                break

            except asyncio.TimeoutError:
                logger.warning(
                    "Mistral API timeout (%d/%d)",
                    attempt + 1,
                    MAX_RETRIES
                )
                last_error = asyncio.TimeoutError("Mistral API timeout")

            except Exception as e:
                logger.exception(
                    "Mistral API hatası (%d/%d)",
                    attempt + 1,
                    MAX_RETRIES
                )
                last_error = e

            if attempt < MAX_RETRIES - 1:
                logger.info("2 saniye sonra tekrar deneniyor...")
                await asyncio.sleep(2)

        else:
            raise last_error

        choice = response.choices[0]

        # Eğer model bir araç (tool) kullanmaya karar verdiyse
        if choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            logger.info("Mistral Tool seçti: %s", tool_call.function.name)

            # SimpleAgent'ın beklediği Anthropic tool_use formatında döndürüyoruz
            # Bu sayede Agent katmanında hiçbir kodu değiştirmemize gerek kalmıyor
            return {
                "type": "tool_use",
                "name": tool_call.function.name,
                "input": json.loads(tool_call.function.arguments),
                "id": tool_call.id
            }

        # Düz metin cevabı verdiyse
        return choice.message.content