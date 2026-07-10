from pydantic import BaseModel, Field
from app.tools.base import BaseTool
from app.services.employee_repository import EmployeeRepository


class EmployeeLookupArgs(BaseModel):
    name: str = Field(description="Aranacak çalışanın adı veya soyadı")


class EmployeeLookupTool(BaseTool):
    name = "employee_lookup"
    description = (
        "Şirket çalışanlarının veritabanında isme göre arama yapar ve "
        "eşleşen çalışanların email adreslerini döner. Mail göndermeden önce "
        "alıcının email adresini bulmak için kullanılır."
    )
    args_schema = EmployeeLookupArgs

    def __init__(self, repository: EmployeeRepository):
        self.repository = repository

    async def run(self, name: str) -> dict:
        matches = self.repository.find_by_name(name)

        if len(matches) == 0:
            return {"status": "not_found", "message": f"'{name}' isimli çalışan bulunamadı."}

        if len(matches) > 1:
            return {
                "status": "multiple_matches",
                "message": "Birden fazla eşleşme bulundu, kullanıcıya hangisini kastettiği sorulmalı.",
                "matches": [m.model_dump() for m in matches]
            }

        return {"status": "found", "employee": matches[0].model_dump()}