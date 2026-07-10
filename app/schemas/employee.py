from pydantic import BaseModel

class Employee(BaseModel):
    id: int
    full_name: str
    email: str
    department: str