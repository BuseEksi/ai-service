from abc import ABC, abstractmethod
from typing import Any, Type
from pydantic import BaseModel


class BaseTool(ABC):
    name: str
    description: str
    # Her aracın alacağı parametreleri Pydantic modeli olarak tanımlayacağız
    args_schema: Type[BaseModel] | None = None

    def get_tool_schema(self) -> dict[str, Any]:
        """
        LLM'in (Anthropic vb.) aracı anlayabilmesi için JSON şemasını üretir.
        """
        schema = {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {},
            }
        }

        # Eğer aracın bir Pydantic şeması varsa, onu JSON formata çevirip ekle
        if self.args_schema:
            # Pydantic v2 metodu
            json_schema = self.args_schema.model_json_schema()
            schema["input_schema"]["properties"] = json_schema.get("properties", {})

            if "required" in json_schema:
                schema["input_schema"]["required"] = json_schema["required"]

        return schema

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        raise NotImplementedError