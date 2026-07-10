from abc import ABC, abstractmethod
import sqlite3
from app.schemas.employee import Employee


class EmployeeRepository(ABC):
    @abstractmethod
    def find_by_name(self, name: str) -> list[Employee]:
        ...


class MockEmployeeRepository(EmployeeRepository):
    def __init__(self, db_path: str = "employees.db"):
        self.db_path = db_path
        self._seed_if_empty()

    def _seed_if_empty(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY,
                full_name TEXT,
                email TEXT,
                department TEXT
            )
        """)
        cur.execute("SELECT COUNT(*) FROM employees")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO employees (full_name, email, department) VALUES (?, ?, ?)",
                [
                    ("Ali Yılmaz", "ali.yilmaz@argeset.com", "Yazılım"),
                    ("Ayşe Kaya", "ayse.kaya@argeset.com", "Satış"),
                ]
            )
        conn.commit()
        conn.close()

    def find_by_name(self, name: str) -> list[Employee]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, full_name, email, department FROM employees WHERE full_name LIKE ?",
            (f"%{name}%",)
        )
        rows = cur.fetchall()
        conn.close()
        return [Employee(id=r[0], full_name=r[1], email=r[2], department=r[3]) for r in rows]

    # Gelecekte:
    # class XEmployeeRepository(EmployeeRepository):
    #     def find_by_name(self, name: str) -> list[Employee]:
    #         # Özel API'ye HTTP call atılacak