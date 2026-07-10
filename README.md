# AI Service - v1 (İlk Çalışan Versiyon)

Bu, projendeki **AI_Service_Detailed_Project_Plan** dokümanının Faz 1-4'ünün
minimal ama gerçekten çalışan bir versiyonu. Katman mimarisi (API → Agent →
Tool → LLM) tam olarak plandaki gibi kuruldu; ileride her katman ayrı ayrı
büyütülebilir, birbirini bozmadan.

## Mimari

```
Client → FastAPI API Layer → Agent Layer → Tool Layer → LLM Layer → Response
```

```
app/
  api/routes/     → HTTP endpoint'leri (health, chat)
  agents/          → SimpleAgent: tool gerekip gerekmediğine karar verir
  tools/           → BaseTool arayüzü + DateTimeTool (çalışır) + GmailTool (iskelet)
  llm/             → BaseLLM arayüzü + AnthropicLLM + MockLLM + factory
  schemas/         → Pydantic request/response modelleri
  services/        → Dependency injection (FastAPI Depends)
  config/          → .env okuyan Settings sınıfı
  utils/           → logger ve yardımcı araçlar
```

## Neler çalışıyor (v1)

* **Mimari ve Altyapı**
    * ✅ **Katmanlı Mimari:** API → Agent → Tool → LLM akışı; her katmanın tek bir 
  sorumluluğu olacak şekilde başarıyla kuruldu.
    * ✅ **Provider-Independent LLM:** Anthropic Claude ve Mistral desteği factory 
  pattern ile sisteme entegre edildi; `LLM_PROVIDER=mock` ile anahtar gerektirmeden uçtan uca test imkanı sağlandı.
    * ✅ **FastAPI Standartları:** Sağlıklı bir REST servisi için gerekli olan health-check,
  hata yönetimi ve merkezi logging yapısı hazırlandı.

* **Agent Yetenekleri**
    * ✅ **Otonom Karar Mekanizması (Faz 3):** `SimpleAgent`, Pydantic modelleriyle
  dinamik olarak tanımlanan araç şemalarını kullanarak *function calling* yeteneğine kavuştu.
    * ✅ **Çoklu Araç Döngüsü:** Yapay zeka, karmaşık istekleri yerine getirmek için
  art arda birden fazla aracı (Örn: Önce oku, sonra özetle, sonra rapor maili at) otonom olarak tetikleyebiliyor.

* **Gmail Entegrasyonu (Faz 4)**
    * ✅ **Kapsamlı Erişim:** Gerçek Google OAuth2 akışı ile `gmail.readonly` ve
  `gmail.send` yetkileri aktif edildi.
    * ✅ **Akıllı Özetleme ve Aksiyon:** `GET /emails/summary` ile mailler okunup özetleniyor
  ve aksiyon gerektirenler tespit ediliyor.
    * ✅ **Otonom Raporlama:** Tespit edilen özetler, `send_gmail` aracı ile kullanıcıya
  e-posta olarak raporlanabiliyor.
  
* **Aktif Toollar**
    * ✅ **DateTimeTool:** Agent, `şu an saat kaç?` gibi sorulara yanıt verebiliyor.
    * ✅ **GmailTool:** Agent, Gmail API'si üzerinden mail özetleme ve raporlama yapabiliyor.
    * ✅ **SlackTool:** Slack API'si üzerinden mesaj gönderme yeteneği (opsiyonel, Slack token gerektirir).
    * ✅ **EmployeeLookupTool:** Database üzerinden çalışan adına göre göre çalışan e-postası döndürülebiliyor.


## Mail özetleme özelliği

`GET /api/v1/emails/summary?limit=10&query=is:unread`

Her mail için şunu döndürür:
```json
{
  "total": 4,
  "action_required_count": 1,
  "items": [
    {
      "id": "...",
      "sender": "Buse Ekşi <buse.eksi@deneme.com>",
      "subject": "Bu bir denemedir.",
      "summary": "Deneme için mock veri.",
      "action_required": false,
      "action_reason": "Mock veri aksiyon gerektirmiyor."
    }
  ]
}
```

**Gerçek Gmail'e bağlanmak için (opsiyonel, credentials.json yoksa mock mailler kullanılır):**
1. [Google Cloud Console](https://console.cloud.google.com/) → yeni proje → **Gmail API**'yi etkinleştir
2. **OAuth consent screen** oluştur (Internal/External, test kullanıcısı olarak kendi mailini ekle)
3. **Credentials → Create Credentials → OAuth client ID → Desktop app**
4. İndirdiğin dosyayı proje köküne `credentials.json` olarak koy
5. `uvicorn app.main:app --reload` ile çalıştır, `/emails/summary`'yi ilk çağırdığında
   tarayıcı açılıp izin isteyecek (bu terminalde/local'de çalıştırman gerekir,
   headless sunucuda ilk auth için ayrı bir akış gerekir)
6. İzin verince `token.json` otomatik oluşur, sonraki çağrılarda tekrar sorulmaz
`credentials.json` yoksa sistem otomatik olarak örnek (mock) mailler üzerinden çalışır,
böylece OAuth kurulumunu bitirmeden diğer katmanlar test edilebilir.

## Kurulum

```bash
cd ai-service
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` dosyasında iki seçenek var:

```env
# API key olmadan test etmek için:
LLM_PROVIDER=mock

# Gerçek Claude cevapları almak için:
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

## Çalıştırma

```bash
uvicorn app.main:app --reload --port 8000
```

Sonra tarayıcıda **http://127.0.0.1:8000/docs** açarsan otomatik oluşan
Swagger arayüzünden endpoint'leri deneyebilirsin.

## Test edilmiş örnek istekler

```bash
curl http://127.0.0.1:8000/api/v1/health

curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "merhaba, nasılsın?"}'

# Tool tetikleyen örnek (agent otomatik DateTimeTool'u çağırır):
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "şu an saat kaç?"}'
```

## Sırada ne var (plandaki sonraki fazlar)



- **Faz 6**: Authentication (API key / JWT)
- **Faz 7**: Docker, testler, CI/CD

Bu fazların her biri mevcut mimariyi bozmadan eklenecek şekilde tasarlandı;
katmanlar birbirinden bağımsız olduğu için örneğin memory eklemek Agent
katmanına dokunmayı gerektirmeyecek, sadece yeni bir `services/memory.py`
eklenip Agent'a inject edilecek.
