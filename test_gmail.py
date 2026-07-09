"""
Gmail OAuth bağlantısını tek başına test etmek için basit script.
Çalıştırınca tarayıcı açılıp Google izin ekranı gelmeli.
İzin verince proje köküne token.json dosyası oluşacak.
"""
import asyncio

from app.tools.gmail_reader_tool import GmailReaderTool


async def main():
    tool = GmailReaderTool(
        credentials_path="credentials.json",
        token_path="token.json",
    )
    emails = await tool.fetch_recent(limit=5, query="is:unread")

    print(f"\n{len(emails)} e-posta bulundu:\n")
    for e in emails:
        print(f"- [{e['sender']}] {e['subject']}")


if __name__ == "__main__":
    asyncio.run(main())