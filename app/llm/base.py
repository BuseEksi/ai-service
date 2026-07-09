from abc import ABC, abstractmethod
from typing import Any

class BaseLLM(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None
    ) -> str | dict[str, Any]:
        """
        LLM'den metin veya tool çağrısı üretir.

        - messages: Sohbet geçmişi
        - system: Sistem promptu
        - tools: BaseTool.get_tool_schema() ile üretilmiş JSON formatındaki araç şemaları listesi
        """
        raise NotImplementedError