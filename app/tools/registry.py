"""
Tool registry: sistemdeki tüm tool'ların merkezi listesi.
Yeni bir tool eklemek için sadece burada listeye eklemek yeterli.
"""

from app.config.settings import get_settings
from app.tools.base import BaseTool
from app.tools.datetime_tool import DateTimeTool
from app.tools.gmail_tool import GmailTool
from app.tools.gmail_reader_tool import GmailReaderTool
from app.tools.slack_tool import SlackTool


def get_available_tools() -> list[BaseTool]:
    settings = get_settings()

    return [
        DateTimeTool(),


        GmailTool(
            credentials_path=settings.GMAIL_CREDENTIALS_PATH,
            token_path=settings.GMAIL_TOKEN_PATH
        ),


        GmailReaderTool(
            credentials_path=settings.GMAIL_CREDENTIALS_PATH,
            token_path=settings.GMAIL_TOKEN_PATH
        ),

        SlackTool(
            bot_token=settings.SLACK_BOT_TOKEN
        ),
    ]


def get_tools_as_dict() -> dict[str, BaseTool]:
    return {tool.name: tool for tool in get_available_tools()}

