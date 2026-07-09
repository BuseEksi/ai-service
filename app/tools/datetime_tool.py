"""
İlk çalışan versiyon için gerçekten işlev gören basit bir tool.
Sisteminin uçtan uca çalıştığını göstermek için hiçbir
 dış bağımlılık gerektirmeden çalışır.
"""
from datetime import datetime

from app.tools.base import BaseTool


class DateTimeTool(BaseTool):
    name = "get_current_datetime"
    description = "Şu anki tarih ve saati döndürür."

    async def run(self, **kwargs) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
