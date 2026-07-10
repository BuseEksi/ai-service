"""
E-postaları alıp LLM'den yapılandırılmış (structured) özet + aksiyon tespiti
isteyen servis katmanı.  LLM burada bir "structured data extractor" gibi
kullanılıyor (mail listesi ver, JSON özet al), agent gibi otonom karar vermiyor.
 Tool katmanından (ham mail verisi) ile LLM katmanı
(serbest metin üretir) arasındaki köprü burada kuruluyor.
"""
import json

from app.llm.base import BaseLLM
from app.schemas.email import EmailSummaryItem, EmailSummaryResponse
from app.tools.gmail_reader_tool import GmailReaderTool
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """Sen bir e-posta asistanısın. Sana JSON formatında bir e-posta listesi verilecek.
Her e-posta için:
1. 1-2 cümlelik kısa, net bir özet çıkar (Türkçe).
2. Bu e-postanın gönderenden veya alıcıdan somut bir aksiyon (cevap verme, imza,
   onay, teslim tarihi, toplantıya katılım vb.) gerektirip gerektirmediğine karar ver.
3. Aksiyon gerekiyorsa kısa bir action_reason yaz (ör: "Cuma'ya kadar imza gerekiyor").
   Gerekmiyorsa action_reason'ı null bırak.

SADECE aşağıdaki JSON formatında, başka hiçbir açıklama/markdown olmadan cevap ver:
[
  {"id": "...", "summary": "...", "action_required": true, "action_reason": "..."},
  ...
]
"""


class EmailSummarizerService:
    def __init__(self, llm: BaseLLM, gmail_tool: GmailReaderTool):
        self._llm = llm
        self._gmail_tool = gmail_tool

    @staticmethod
    def _parse_llm_json(raw_text: str) -> list[dict]:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            # olası ```json ... ``` sarmalını temizle
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json\n", "", 1) if cleaned.startswith("json") else cleaned
        return json.loads(cleaned)

    async def summarize_recent(
        self, limit: int = 10, query: str = "is:unread"
    ) -> EmailSummaryResponse:
        emails = await self._gmail_tool.fetch_recent(limit=limit, query=query)

        if not emails:
            return EmailSummaryResponse(total=0, action_required_count=0, items=[])

        llm_input = [
            {"id": e["id"], "sender": e["sender"], "subject": e["subject"], "body": e["body"]}
            for e in emails
        ]

        raw_reply = await self._llm.generate(
            messages=[
                {"role": "user", "content": json.dumps(llm_input, ensure_ascii=False)}
            ],
            system=SYSTEM_PROMPT,
        )

        try:
            parsed = self._parse_llm_json(raw_reply)
        except json.JSONDecodeError:
            logger.error("LLM cevabı JSON olarak parse edilemedi: %s", raw_reply)

            parsed = [
                {
                    "id": e["id"],
                    "summary": "Özet oluşturulamadı.",
                    "action_required": False,
                    "action_reason": None,
                }
                for e in emails
            ]

        sender_subject_by_id = {e["id"]: (e["sender"], e["subject"]) for e in emails}
        items = []
        for entry in parsed:
            sender, subject = sender_subject_by_id.get(entry.get("id"), ("", ""))
            items.append(
                EmailSummaryItem(
                    id=entry.get("id", ""),
                    sender=sender,
                    subject=subject,
                    summary=entry.get("summary", ""),
                    action_required=bool(entry.get("action_required", False)),
                    action_reason=entry.get("action_reason"),
                )
            )

        action_count = sum(1 for item in items if item.action_required)
        return EmailSummaryResponse(
            total=len(items), action_required_count=action_count, items=items
        )
