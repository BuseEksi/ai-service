"""
MistralLLM sınıfı için unit testler.

Gerçek Mistral API'sine hiçbir çağrı yapılmaz; app.llm.mistral_llm.Mistral
client'ı mock'lanarak client.chat.complete_async'in döneceği cevaplar simüle edilir.
"""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.llm.mistral_llm import MistralLLM


def make_text_response(text: str):
    """choices[0].message.content dolu, tool_calls boş sahte bir Mistral cevabı üretir."""
    message = SimpleNamespace(content=text, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def make_tool_call_response(tool_name: str, arguments: dict, call_id: str = "call_123"):
    """choices[0].message.tool_calls dolu sahte bir Mistral cevabı üretir."""
    function = SimpleNamespace(name=tool_name, arguments=json.dumps(arguments))
    tool_call = SimpleNamespace(id=call_id, function=function)
    message = SimpleNamespace(content=None, tool_calls=[tool_call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.fixture
def llm():
    """Mistral client'ı mock'lanmış bir MistralLLM örneği döndürür."""
    with patch("app.llm.mistral_llm.Mistral") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.chat.complete_async = AsyncMock()
        instance = MistralLLM(api_key="test-key", model="mistral-large-latest")
        yield instance


class TestFormatToolsForMistral:
    def test_converts_anthropic_style_schema_to_openai_function_format(self, llm):
        anthropic_style_tools = [
            {
                "name": "get_weather",
                "description": "Verilen şehir için hava durumunu döndürür",
                "input_schema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            }
        ]

        result = llm._format_tools_for_mistral(anthropic_style_tools)

        assert result == [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Verilen şehir için hava durumunu döndürür",
                    "parameters": anthropic_style_tools[0]["input_schema"],
                },
            }
        ]

    def test_missing_input_schema_defaults_to_empty_dict(self, llm):
        tools = [{"name": "no_args_tool", "description": "Parametresiz araç"}]

        result = llm._format_tools_for_mistral(tools)

        assert result[0]["function"]["parameters"] == {}


class TestGenerateTextResponse:
    async def test_returns_plain_text_when_no_tool_called(self, llm):
        llm.client.chat.complete_async.return_value = make_text_response("merhaba, nasıl yardımcı olabilirim?")

        result = await llm.generate(messages=[{"role": "user", "content": "merhaba"}])

        assert result == "merhaba, nasıl yardımcı olabilirim?"

    async def test_system_prompt_is_prepended_as_system_message(self, llm):
        llm.client.chat.complete_async.return_value = make_text_response("ok")

        await llm.generate(
            messages=[{"role": "user", "content": "merhaba"}],
            system="Sen yardımsever bir asistansın.",
        )

        sent_kwargs = llm.client.chat.complete_async.call_args.kwargs
        assert sent_kwargs["messages"][0] == {
            "role": "system",
            "content": "Sen yardımsever bir asistansın.",
        }

    async def test_no_system_message_added_when_system_is_none(self, llm):
        llm.client.chat.complete_async.return_value = make_text_response("ok")

        await llm.generate(messages=[{"role": "user", "content": "merhaba"}])

        sent_kwargs = llm.client.chat.complete_async.call_args.kwargs
        assert sent_kwargs["messages"][0] == {"role": "user", "content": "merhaba"}

    async def test_tools_omitted_from_request_when_not_provided(self, llm):
        llm.client.chat.complete_async.return_value = make_text_response("ok")

        await llm.generate(messages=[{"role": "user", "content": "merhaba"}])

        sent_kwargs = llm.client.chat.complete_async.call_args.kwargs
        assert "tools" not in sent_kwargs
        assert "tool_choice" not in sent_kwargs

    async def test_tools_included_and_auto_chosen_when_provided(self, llm):
        llm.client.chat.complete_async.return_value = make_text_response("ok")
        tools = [{"name": "get_time", "description": "Saat bilgisini döndürür", "input_schema": {}}]

        await llm.generate(messages=[{"role": "user", "content": "saat kaç?"}], tools=tools)

        sent_kwargs = llm.client.chat.complete_async.call_args.kwargs
        assert sent_kwargs["tool_choice"] == "auto"
        assert sent_kwargs["tools"][0]["function"]["name"] == "get_time"


class TestGenerateToolUseResponse:
    async def test_returns_anthropic_style_tool_use_dict(self, llm):
        llm.client.chat.complete_async.return_value = make_tool_call_response(
            tool_name="get_weather",
            arguments={"city": "İstanbul"},
            call_id="call_abc",
        )

        result = await llm.generate(
            messages=[{"role": "user", "content": "istanbul'da hava nasıl?"}],
            tools=[{"name": "get_weather", "description": "...", "input_schema": {}}],
        )

        assert result == {
            "type": "tool_use",
            "name": "get_weather",
            "input": {"city": "İstanbul"},
            "id": "call_abc",
        }


class TestGenerateMessageHistoryFormatting:
    async def test_tool_result_message_converted_to_tool_role(self, llm):
        llm.client.chat.complete_async.return_value = make_text_response("ok")

        history = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_abc",
                        "name": "get_weather",
                        "content": "İstanbul: 28°C, açık",
                    }
                ],
            }
        ]

        await llm.generate(messages=history)

        sent_kwargs = llm.client.chat.complete_async.call_args.kwargs
        assert sent_kwargs["messages"][0] == {
            "role": "tool",
            "name": "get_weather",
            "content": "İstanbul: 28°C, açık",
            "tool_call_id": "call_abc",
        }

    async def test_tool_result_missing_name_defaults_to_tool(self, llm):
        """item.get('name', 'tool') davranışı: name alanı yoksa 'tool' varsayılanı kullanılmalı."""
        llm.client.chat.complete_async.return_value = make_text_response("ok")

        history = [
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "call_abc", "content": "sonuç"}
                ],
            }
        ]

        await llm.generate(messages=history)

        sent_kwargs = llm.client.chat.complete_async.call_args.kwargs
        assert sent_kwargs["messages"][0]["name"] == "tool"

    async def test_assistant_tool_use_message_converted_to_tool_calls(self, llm):
        llm.client.chat.complete_async.return_value = make_text_response("ok")

        history = [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "call_abc",
                        "name": "get_weather",
                        "input": {"city": "İstanbul"},
                    }
                ],
            }
        ]

        await llm.generate(messages=history)

        sent_kwargs = llm.client.chat.complete_async.call_args.kwargs
        sent_message = sent_kwargs["messages"][0]
        assert sent_message["role"] == "assistant"
        assert sent_message["tool_calls"][0]["function"]["name"] == "get_weather"
        assert json.loads(sent_message["tool_calls"][0]["function"]["arguments"]) == {"city": "İstanbul"}

    async def test_plain_role_content_messages_pass_through_unchanged(self, llm):
        llm.client.chat.complete_async.return_value = make_text_response("ok")

        await llm.generate(messages=[{"role": "user", "content": "merhaba"}])

        sent_kwargs = llm.client.chat.complete_async.call_args.kwargs
        assert sent_kwargs["messages"][0] == {"role": "user", "content": "merhaba"}


class TestGenerateRetryBehaviour:
    async def test_retries_on_timeout_then_succeeds(self, llm):
        with patch("app.llm.mistral_llm.asyncio.sleep", new=AsyncMock()):
            with patch(
                "app.llm.mistral_llm.asyncio.wait_for",
                side_effect=[TimeoutError(), make_text_response("ikinci denemede başardı")],
            ):
                result = await llm.generate(messages=[{"role": "user", "content": "merhaba"}])

        assert result == "ikinci denemede başardı"

    async def test_raises_last_error_after_max_retries(self, llm):
        boom = ValueError("kalıcı hata")
        with patch("app.llm.mistral_llm.asyncio.sleep", new=AsyncMock()):
            with patch("app.llm.mistral_llm.asyncio.wait_for", side_effect=[boom, boom, boom]):
                with pytest.raises(ValueError, match="kalıcı hata"):
                    await llm.generate(messages=[{"role": "user", "content": "merhaba"}])
