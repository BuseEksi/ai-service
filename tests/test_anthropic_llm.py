"""
AnthropicLLM sınıfı için unit testler.

Gerçek Anthropic API'sine hiçbir çağrı yapılmaz; app.llm.anthropic_llm.anthropic
modülündeki AsyncAnthropic client'ı mock'lanarak client.messages.create'in
döneceği cevaplar simüle edilir.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.llm.anthropic_llm import AnthropicLLM


def make_text_response(text: str):
    """response.content = [TextBlock(type='text', text=...)] şeklinde sahte bir cevap üretir."""
    block = SimpleNamespace(type="text", text=text)
    return SimpleNamespace(content=[block])


def make_tool_use_response(tool_name: str, tool_input: dict, tool_id: str = "toolu_123"):
    """response.content içinde bir tool_use bloğu olan sahte bir cevap üretir."""
    block = SimpleNamespace(type="tool_use", name=tool_name, input=tool_input, id=tool_id)
    return SimpleNamespace(content=[block])


def make_mixed_response(text: str, tool_name: str, tool_input: dict, tool_id: str = "toolu_456"):
    """Önce metin, sonra tool_use bloğu içeren bir cevap üretir (Anthropic bunu döndürebilir)."""
    text_block = SimpleNamespace(type="text", text=text)
    tool_block = SimpleNamespace(type="tool_use", name=tool_name, input=tool_input, id=tool_id)
    return SimpleNamespace(content=[text_block, tool_block])


@pytest.fixture
def llm():
    """AsyncAnthropic client'ı mock'lanmış bir AnthropicLLM örneği döndürür."""
    with patch("app.llm.anthropic_llm.anthropic.AsyncAnthropic") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.messages.create = AsyncMock()
        instance = AnthropicLLM(api_key="test-key", model="claude-3-haiku-20240307")
        yield instance


class TestGenerateTextResponse:
    async def test_returns_plain_text_when_no_tool_called(self, llm):
        llm.client.messages.create.return_value = make_text_response("merhaba, nasıl yardımcı olabilirim?")

        result = await llm.generate(messages=[{"role": "user", "content": "merhaba"}])

        assert result == "merhaba, nasıl yardımcı olabilirim?"

    async def test_max_tokens_and_model_always_sent(self, llm):
        llm.client.messages.create.return_value = make_text_response("ok")

        await llm.generate(messages=[{"role": "user", "content": "merhaba"}])

        sent_kwargs = llm.client.messages.create.call_args.kwargs
        assert sent_kwargs["model"] == "claude-3-haiku-20240307"
        assert sent_kwargs["max_tokens"] == 1024

    async def test_system_prompt_included_when_provided(self, llm):
        llm.client.messages.create.return_value = make_text_response("ok")

        await llm.generate(
            messages=[{"role": "user", "content": "merhaba"}],
            system="Sen yardımsever bir asistansın.",
        )

        sent_kwargs = llm.client.messages.create.call_args.kwargs
        assert sent_kwargs["system"] == "Sen yardımsever bir asistansın."

    async def test_system_key_omitted_when_not_provided(self, llm):
        llm.client.messages.create.return_value = make_text_response("ok")

        await llm.generate(messages=[{"role": "user", "content": "merhaba"}])

        sent_kwargs = llm.client.messages.create.call_args.kwargs
        assert "system" not in sent_kwargs

    async def test_messages_passed_through_unchanged(self, llm):
        llm.client.messages.create.return_value = make_text_response("ok")
        history = [
            {"role": "user", "content": "merhaba"},
            {"role": "assistant", "content": "selam"},
        ]

        await llm.generate(messages=history)

        sent_kwargs = llm.client.messages.create.call_args.kwargs
        assert sent_kwargs["messages"] == history

    async def test_tools_omitted_when_not_provided(self, llm):
        llm.client.messages.create.return_value = make_text_response("ok")

        await llm.generate(messages=[{"role": "user", "content": "merhaba"}])

        sent_kwargs = llm.client.messages.create.call_args.kwargs
        assert "tools" not in sent_kwargs

    async def test_tools_passed_through_as_is(self, llm):
        """AnthropicLLM tool şemasını kendi native formatında (dönüşümsüz) gönderir."""
        llm.client.messages.create.return_value = make_text_response("ok")
        tools = [{"name": "get_time", "description": "Saat bilgisini döndürür", "input_schema": {}}]

        await llm.generate(messages=[{"role": "user", "content": "saat kaç?"}], tools=tools)

        sent_kwargs = llm.client.messages.create.call_args.kwargs
        assert sent_kwargs["tools"] == tools


class TestGenerateToolUseResponse:
    async def test_returns_tool_use_dict_when_tool_called(self, llm):
        llm.client.messages.create.return_value = make_tool_use_response(
            tool_name="get_weather",
            tool_input={"city": "İstanbul"},
            tool_id="toolu_abc",
        )

        result = await llm.generate(
            messages=[{"role": "user", "content": "istanbul'da hava nasıl?"}],
            tools=[{"name": "get_weather", "description": "...", "input_schema": {}}],
        )

        assert result == {
            "type": "tool_use",
            "name": "get_weather",
            "input": {"city": "İstanbul"},
            "id": "toolu_abc",
        }

    async def test_returns_first_tool_use_block_when_mixed_with_text(self, llm):
        """Response hem text hem tool_use bloğu içeriyorsa, tool_use öncelikli döner."""
        llm.client.messages.create.return_value = make_mixed_response(
            text="Kontrol ediyorum...",
            tool_name="get_weather",
            tool_input={"city": "Ankara"},
        )

        result = await llm.generate(messages=[{"role": "user", "content": "ankara hava"}])

        assert result["type"] == "tool_use"
        assert result["name"] == "get_weather"
        assert result["input"] == {"city": "Ankara"}
