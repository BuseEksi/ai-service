"""
SimpleAgent.handle() metodunun orkestrasyon mantığı için unit testler.

Gerçek LLM'e, gerçek araçlara (Gmail/Slack/DB) ve gerçek SQLite hafızasına
hiçbir çağrı yapılmaz:
- get_tools_as_dict() patch'lenerek sahte (fake) araçlar enjekte edilir.
- memory_service patch'lenerek konuşma geçmişi/kaydı taklit edilir.
- LLM'in generate() metodu AsyncMock ile kontrol edilir.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.simple_agent import SimpleAgent


class FakeTool:
    """BaseTool arayüzünü taklit eden, gerçek iş yapmayan test aracı."""

    def __init__(self, name: str, run_return=None, run_side_effect=None):
        self.name = name
        self.description = f"{name} için sahte açıklama"
        self.run = AsyncMock(return_value=run_return, side_effect=run_side_effect)

    def get_tool_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {"type": "object", "properties": {}},
        }


@pytest.fixture
def agent_env():
    """
    get_tools_as_dict ve memory_service'i patch'li tutan fixture.
    Testler bu patch'ler aktifken SimpleAgent kurup handle() çağırmalı.
    """
    with patch("app.agents.simple_agent.get_tools_as_dict") as mock_get_tools, \
         patch("app.agents.simple_agent.memory_service") as mock_memory:
        mock_get_tools.return_value = {}
        mock_memory.get_recent_history.return_value = []
        yield mock_get_tools, mock_memory


def make_llm(generate_return=None, generate_side_effect=None):
    llm = MagicMock()
    llm.generate = AsyncMock(return_value=generate_return, side_effect=generate_side_effect)
    return llm


class TestSessionIdHandling:
    async def test_new_uuid_generated_when_session_id_is_none(self, agent_env):
        llm = make_llm(generate_return="merhaba")
        agent = SimpleAgent(llm=llm)

        result = await agent.handle(message="selam", session_id=None)

        # Geçerli bir UUID string'i üretilmiş olmalı
        assert result.session_id is not None
        uuid.UUID(result.session_id)  # geçersizse ValueError fırlatır

    async def test_provided_session_id_is_reused(self, agent_env):
        llm = make_llm(generate_return="merhaba")
        agent = SimpleAgent(llm=llm)

        result = await agent.handle(message="selam", session_id="sohbet-123")

        assert result.session_id == "sohbet-123"


class TestTextResponse:
    async def test_returns_plain_text_reply_directly(self, agent_env):
        llm = make_llm(generate_return="Türkiye'nin başkenti Ankara'dır.")
        agent = SimpleAgent(llm=llm)

        result = await agent.handle(message="başkent neresi?", session_id="s1")

        assert result.reply == "Türkiye'nin başkenti Ankara'dır."
        assert result.tool_calls == []

    async def test_saves_user_and_assistant_messages_to_memory(self, agent_env):
        _, mock_memory = agent_env
        llm = make_llm(generate_return="cevap")
        agent = SimpleAgent(llm=llm)

        await agent.handle(message="orijinal mesaj", session_id="s1")

        mock_memory.save_message.assert_any_call("s1", "user", "orijinal mesaj")
        mock_memory.save_message.assert_any_call("s1", "assistant", "cevap")

    async def test_recent_history_is_included_in_llm_request(self, agent_env):
        mock_get_tools, mock_memory = agent_env
        mock_memory.get_recent_history.return_value = [
            {"role": "user", "content": "önceki mesaj"},
            {"role": "assistant", "content": "önceki cevap"},
        ]
        llm = make_llm(generate_return="yeni cevap")
        agent = SimpleAgent(llm=llm)

        await agent.handle(message="yeni mesaj", session_id="s1")

        sent_messages = llm.generate.call_args.kwargs["messages"]
        assert sent_messages[0] == {"role": "user", "content": "önceki mesaj"}
        assert sent_messages[1] == {"role": "assistant", "content": "önceki cevap"}
        assert sent_messages[2] == {"role": "user", "content": "yeni mesaj"}

    async def test_tool_schemas_of_all_registered_tools_sent_to_llm(self, agent_env):
        mock_get_tools, _ = agent_env
        tool_a = FakeTool("tool_a")
        tool_b = FakeTool("tool_b")
        mock_get_tools.return_value = {"tool_a": tool_a, "tool_b": tool_b}
        llm = make_llm(generate_return="cevap")
        agent = SimpleAgent(llm=llm)

        await agent.handle(message="merhaba", session_id="s1")

        sent_tools = llm.generate.call_args.kwargs["tools"]
        sent_names = {t["name"] for t in sent_tools}
        assert sent_names == {"tool_a", "tool_b"}


class TestAttachmentHandling:
    async def test_attachment_note_appended_to_llm_message_but_not_saved_to_memory(self, agent_env):
        mock_get_tools, mock_memory = agent_env
        llm = make_llm(generate_return="tamam")
        agent = SimpleAgent(llm=llm)

        await agent.handle(
            message="bu dosyayı gönder",
            session_id="s1",
            attachment_path="/tmp/uploads/abc.pdf",
        )

        sent_messages = llm.generate.call_args.kwargs["messages"]
        last_user_message = sent_messages[-1]
        assert "/tmp/uploads/abc.pdf" in last_user_message["content"]

        # Hafızaya orijinal mesaj kaydedilmeli, sistem notu eklenmiş hali değil
        mock_memory.save_message.assert_any_call("s1", "user", "bu dosyayı gönder")

    async def test_no_attachment_note_when_attachment_path_is_none(self, agent_env):
        llm = make_llm(generate_return="tamam")
        agent = SimpleAgent(llm=llm)

        await agent.handle(message="merhaba", session_id="s1", attachment_path=None)

        sent_messages = llm.generate.call_args.kwargs["messages"]
        assert sent_messages[-1] == {"role": "user", "content": "merhaba"}


class TestToolUseFlow:
    async def test_known_tool_is_executed_and_result_fed_back_to_llm(self, agent_env):
        mock_get_tools, _ = agent_env
        fake_tool = FakeTool("get_current_datetime", run_return="2026-07-21 10:00:00")
        mock_get_tools.return_value = {"get_current_datetime": fake_tool}

        llm = make_llm(generate_side_effect=[
            {"type": "tool_use", "name": "get_current_datetime", "input": {}, "id": "call_1"},
            "Şu an saat 10:00.",
        ])
        agent = SimpleAgent(llm=llm)

        result = await agent.handle(message="saat kaç?", session_id="s1")

        fake_tool.run.assert_awaited_once_with()
        assert result.reply == "Şu an saat 10:00."
        assert result.tool_calls == ["get_current_datetime"]
        assert llm.generate.await_count == 2

        # İkinci LLM çağrısına tool_result mesajı eklenmiş olmalı
        second_call_messages = llm.generate.call_args_list[1].kwargs["messages"]
        tool_result_message = second_call_messages[-1]
        assert tool_result_message["role"] == "user"
        assert tool_result_message["content"][0]["type"] == "tool_result"
        assert tool_result_message["content"][0]["tool_use_id"] == "call_1"
        assert "2026-07-21 10:00:00" in tool_result_message["content"][0]["content"]

    async def test_tool_called_with_llm_provided_arguments(self, agent_env):
        mock_get_tools, _ = agent_env
        fake_tool = FakeTool("employee_lookup", run_return={"status": "found"})
        mock_get_tools.return_value = {"employee_lookup": fake_tool}

        llm = make_llm(generate_side_effect=[
            {"type": "tool_use", "name": "employee_lookup", "input": {"name": "Ali"}, "id": "call_1"},
            "Ali bulundu.",
        ])
        agent = SimpleAgent(llm=llm)

        await agent.handle(message="ali'yi bul", session_id="s1")

        fake_tool.run.assert_awaited_once_with(name="Ali")

    async def test_multiple_sequential_tool_calls_are_all_tracked(self, agent_env):
        mock_get_tools, _ = agent_env
        tool_a = FakeTool("tool_a", run_return="sonuç a")
        tool_b = FakeTool("tool_b", run_return="sonuç b")
        mock_get_tools.return_value = {"tool_a": tool_a, "tool_b": tool_b}

        llm = make_llm(generate_side_effect=[
            {"type": "tool_use", "name": "tool_a", "input": {}, "id": "call_1"},
            {"type": "tool_use", "name": "tool_b", "input": {}, "id": "call_2"},
            "İkisi de tamamlandı.",
        ])
        agent = SimpleAgent(llm=llm)

        result = await agent.handle(message="ikisini de yap", session_id="s1")

        assert result.tool_calls == ["tool_a", "tool_b"]
        tool_a.run.assert_awaited_once()
        tool_b.run.assert_awaited_once()


class TestUnknownTool:
    async def test_unknown_tool_returns_error_reply_and_stops(self, agent_env):
        llm = make_llm(generate_return={
            "type": "tool_use", "name": "does_not_exist", "input": {}, "id": "call_1"
        })
        agent = SimpleAgent(llm=llm)

        result = await agent.handle(message="bilinmeyen araç dene", session_id="s1")

        assert "does_not_exist" in result.reply
        assert result.tool_calls == []
        assert llm.generate.await_count == 1


class TestMaxStepsGuard:
    async def test_stops_after_five_steps_and_returns_fallback_message(self, agent_env):
        mock_get_tools, _ = agent_env
        looping_tool = FakeTool("loop_tool", run_return="tekrar tekrar")
        mock_get_tools.return_value = {"loop_tool": looping_tool}

        # LLM her seferinde aynı tool'u çağırmaya devam ediyormuş gibi davran
        llm = make_llm(generate_return={
            "type": "tool_use", "name": "loop_tool", "input": {}, "id": "call_x"
        })
        agent = SimpleAgent(llm=llm)

        result = await agent.handle(message="sonsuz döngü", session_id="s1")

        assert "çok uzun sürdü" in result.reply or "döngü" in result.reply
        assert llm.generate.await_count == 5
        assert looping_tool.run.await_count == 5
