"""
Gerçek bir API anahtarı olmadan sistemi uçtan uca test edebilmek için
kullanılan sahte (mock) LLM. LLM_PROVIDER=mock yapılınca devreye girer.
"""
import json
import re

from app.llm.base import BaseLLM


class MockLLM(BaseLLM):
    async def generate(self, messages: list[dict], system: str | None = None) -> str:
        last_user_msg = messages[-1]["content"] if messages else ""

        # E-posta özetleme akışı test edilirken gerçek bir LLM gibi
        # geçerli JSON üretsin diye özel bir dal: sistem promptu bizim
        # email_summarizer'ın kullandığı formatsa, basit kural tabanlı
        # bir "özet" üretip action_required'ı anahtar kelimeyle tahmin ediyoruz.
        if system and "action_required" in system:
            try:
                emails = json.loads(last_user_msg)
            except json.JSONDecodeError:
                emails = []

            action_keywords = [
                "kadar", "gerek", "lütfen", "rica", "imza", "onay",
                "cevap", "toplantı", "teslim", "acil",
            ]
            results = []
            for email in emails:
                body = email.get("body", "")
                lowered = body.lower()
                is_action = any(k in lowered for k in action_keywords)
                short_summary = re.sub(r"\s+", " ", body).strip()[:80]
                results.append(
                    {
                        "id": email.get("id", ""),
                        "summary": short_summary + ("..." if len(body) > 80 else ""),
                        "action_required": is_action,
                        "action_reason": "Anahtar kelime eşleşmesi (mock)" if is_action else None,
                    }
                )
            return json.dumps(results, ensure_ascii=False)

        return f"[mock cevap] Şunu aldım: '{last_user_msg}'"
