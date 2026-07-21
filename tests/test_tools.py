"""
app.tools altındaki araçlar için unit testler.

DateTimeTool: dış bağımlılığı yok, doğrudan test edilir.
EmployeeLookupTool: repository mock'lanır (gerçek SQLite'a dokunulmaz).
SlackTool: httpx.AsyncClient mock'lanır (gerçek Slack API'sine çağrı yapılmaz).
"""
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tools.datetime_tool import DateTimeTool
from app.tools.employee_lookup_tool import EmployeeLookupTool
from app.tools.slack_tool import SlackTool
from app.schemas.employee import Employee


class TestDateTimeTool:
    def test_has_expected_name_and_description(self):
        tool = DateTimeTool()

        assert tool.name == "get_current_datetime"
        assert tool.description

    async def test_run_returns_datetime_in_expected_format(self):
        tool = DateTimeTool()

        result = await tool.run()

        assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", result)

    def test_get_tool_schema_has_no_required_properties(self):
        """DateTimeTool'un args_schema'sı yok, bu yüzden şema boş properties dönmeli."""
        tool = DateTimeTool()

        schema = tool.get_tool_schema()

        assert schema["name"] == "get_current_datetime"
        assert schema["input_schema"]["properties"] == {}
        assert "required" not in schema["input_schema"]


class TestEmployeeLookupTool:
    def make_tool(self, find_by_name_return):
        repository = MagicMock()
        repository.find_by_name.return_value = find_by_name_return
        return EmployeeLookupTool(repository=repository), repository

    def test_get_tool_schema_requires_name_field(self):
        tool, _ = self.make_tool([])

        schema = tool.get_tool_schema()

        assert "name" in schema["input_schema"]["properties"]
        assert schema["input_schema"]["required"] == ["name"]

    async def test_returns_not_found_status_when_no_matches(self):
        tool, repository = self.make_tool([])

        result = await tool.run(name="Bulunmayan Kişi")

        assert result["status"] == "not_found"
        repository.find_by_name.assert_called_once_with("Bulunmayan Kişi")

    async def test_returns_found_status_with_employee_when_single_match(self):
        employee = Employee(id=1, full_name="Ali Yılmaz", email="ali.yilmaz@argeset.com", department="Yazılım")
        tool, _ = self.make_tool([employee])

        result = await tool.run(name="Ali")

        assert result["status"] == "found"
        assert result["employee"]["email"] == "ali.yilmaz@argeset.com"

    async def test_returns_multiple_matches_status_when_ambiguous(self):
        employees = [
            Employee(id=1, full_name="Ali Yılmaz", email="ali.yilmaz@argeset.com", department="Yazılım"),
            Employee(id=2, full_name="Ali Kaya", email="ali.kaya@argeset.com", department="Satış"),
        ]
        tool, _ = self.make_tool(employees)

        result = await tool.run(name="Ali")

        assert result["status"] == "multiple_matches"
        assert len(result["matches"]) == 2


class TestSlackTool:
    def test_default_channel_used_when_not_specified_in_schema_call(self):
        tool = SlackTool(bot_token="xoxb-test", default_channel="genel")
        assert tool._default_channel == "genel"

    def test_get_tool_schema_marks_message_as_required_but_not_channel(self):
        tool = SlackTool(bot_token="xoxb-test")

        schema = tool.get_tool_schema()

        assert schema["input_schema"]["required"] == ["message"]
        assert "channel" in schema["input_schema"]["properties"]

    @staticmethod
    def _mock_httpx_client(json_return):
        """httpx.AsyncClient() context manager'ını ve .post()'u mock'lar."""
        mock_response = MagicMock()
        mock_response.json.return_value = json_return

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)

        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        return mock_client_cls, mock_client_instance

    async def test_run_returns_success_message_with_target_channel(self):
        mock_client_cls, mock_client_instance = self._mock_httpx_client({"ok": True})

        with patch("app.tools.slack_tool.httpx.AsyncClient", mock_client_cls):
            tool = SlackTool(bot_token="xoxb-test", default_channel="genel")
            result = await tool.run(message="merhaba ekip")

        assert result == "Mesaj #genel kanalına gönderildi."

    async def test_run_uses_explicit_channel_over_default(self):
        mock_client_cls, mock_client_instance = self._mock_httpx_client({"ok": True})

        with patch("app.tools.slack_tool.httpx.AsyncClient", mock_client_cls):
            tool = SlackTool(bot_token="xoxb-test", default_channel="genel")
            result = await tool.run(message="merhaba", channel="ozel-kanal")

        assert result == "Mesaj #ozel-kanal kanalına gönderildi."
        sent_payload = mock_client_instance.post.call_args.kwargs["json"]
        assert sent_payload["channel"] == "ozel-kanal"

    async def test_run_sends_bearer_token_in_authorization_header(self):
        mock_client_cls, mock_client_instance = self._mock_httpx_client({"ok": True})

        with patch("app.tools.slack_tool.httpx.AsyncClient", mock_client_cls):
            tool = SlackTool(bot_token="xoxb-secret-token")
            await tool.run(message="merhaba")

        sent_headers = mock_client_instance.post.call_args.kwargs["headers"]
        assert sent_headers["Authorization"] == "Bearer xoxb-secret-token"

    async def test_run_returns_error_message_when_slack_reports_failure(self):
        mock_client_cls, _ = self._mock_httpx_client({"ok": False, "error": "channel_not_found"})

        with patch("app.tools.slack_tool.httpx.AsyncClient", mock_client_cls):
            tool = SlackTool(bot_token="xoxb-test")
            result = await tool.run(message="merhaba")

        assert "channel_not_found" in result
