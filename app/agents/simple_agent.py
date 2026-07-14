from app.agents.base import BaseAgent
from app.llm.base import BaseLLM
from app.schemas.chat import ChatResponse
from app.tools.registry import get_tools_as_dict
from app.utils.logger import get_logger
import uuid
from app.services import memory_service



logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "Sen bir kurumsal yazılım şirketi için çalışan yardımcı bir AI asistanısın. "
    "Kısa, net ve doğru cevaplar ver. "
    "Kullanıcının isteğini yerine getirmek için sana verilen araçları (tools) kullanabilirsin. "

    "Kullanıcı bir işlemi açıkça talep ettiyse gerekli aracı doğrudan çağır. "
    "İşlemi gerçekleştirmeden önce ek onay isteme. "

    "Bir aracı kullanmaya karar verdiğinde "
    "'onay bekliyorum', 'istersen yaparım', "
    "'gönderebilirim' gibi ifadeler kullanma. "

    "Tool çağrısı yapıldığında işlem gerçekleştirilmiş kabul edilir. "
    "Tool tamamlandıktan sonra yalnızca yapılan işlemi ve sonucunu bildir."
)


class SimpleAgent(BaseAgent):
    def __init__(self, llm: BaseLLM):
        self._llm = llm
        self._tools = get_tools_as_dict()


    async def handle(self, message: str, session_id: str | None, attachment_path: str | None = None) -> ChatResponse:
        if session_id is None:
            session_id = str(uuid.uuid4())

        tool_calls: list[str] = []
        tool_schemas = [tool.get_tool_schema() for tool in self._tools.values()]

        history = memory_service.get_recent_history(session_id, limit=10)
        # Eğer kullanıcı bir dosya yüklediyse, LLM'in bunu görmesi için mesaja ekle
        effective_message = message
        if attachment_path:
            effective_message += (
                f"\n\n[Sistem notu: Kullanıcı bir dosya yükledi. "
                f"Bu dosyanın sunucu üzerindeki yolu: {attachment_path}. "
                f"Kullanıcı bu dosyayı mail ile göndermek isterse, send_gmail aracını çağırırken "
                f"attachment_path parametresine bu değeri ver.]"
            )

        messages = history + [{"role": "user", "content": effective_message}]
        

        for step in range(5):
            logger.info(f"LLM'e istek gönderiliyor... (Adım {step + 1})")

            response = await self._llm.generate(
                messages=messages,
                system=SYSTEM_PROMPT,
                tools=tool_schemas
            )

            if isinstance(response, str):
                memory_service.save_message(session_id, "user", message)
                memory_service.save_message(session_id, "assistant", response)
                return ChatResponse(
                    reply=response,
                    tool_calls=tool_calls,
                    session_id=session_id
                )

            if isinstance(response, dict) and response.get("type") == "tool_use":
                tool_name = response.get("name")
                tool_args = response.get("input", {})

                if tool_name in self._tools:
                    logger.info("Çalıştırılan Tool: %s, Parametreler: %s", tool_name, tool_args)
                    tool_result = await self._tools[tool_name].run(**tool_args)
                    tool_calls.append(tool_name)

                    messages.append({
                        "role": "assistant",
                        "content": [{"type": "tool_use", "id": response["id"], "name": tool_name, "input": tool_args}]
                    })
                    messages.append({
                        "role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": response["id"], "content": str(tool_result)}]
                    })
                else:
                    memory_service.save_message(session_id, "user", message)
                    reply = f"Hata: LLM bilinmeyen bir araç çağırdı ({tool_name})."
                    memory_service.save_message(session_id, "assistant", reply)
                    return ChatResponse(
                        reply=reply,
                        tool_calls=tool_calls,
                        session_id=session_id
                    )

        memory_service.save_message(session_id, "user", message)
        reply = "İşlem çok uzun sürdü veya bir döngüye girildi. Lütfen isteğinizi basitleştirin."
        memory_service.save_message(session_id, "assistant", reply)
        return ChatResponse(
            reply=reply,
            tool_calls=tool_calls,
            session_id=session_id
        )