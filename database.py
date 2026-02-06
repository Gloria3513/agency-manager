"""
데이터베이스 모델 및 초기화 스크립트
SQLite를 사용하며 추후 PostgreSQL/MySQL로 확장 가능하도록 설계
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any


class Database:
    """데이터베이스 관리 클래스"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent / "data" / "agency.db"
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 반환"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """데이터베이스 테이블 초기화"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 고객 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                company TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'lead',
                source TEXT DEFAULT 'survey',
                notes TEXT
            )
        """)

        # 프로젝트 문의(설문) 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                project_type TEXT,
                budget TEXT,
                duration TEXT,
                description TEXT,
                urgency TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'new',
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        """)

        # 견적서 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                inquiry_id INTEGER,
                quotation_number TEXT UNIQUE,
                items_json TEXT,
                total_amount REAL DEFAULT 0,
                validity_days INTEGER DEFAULT 30,
                status TEXT DEFAULT 'draft',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(id),
                FOREIGN KEY (inquiry_id) REFERENCES inquiries(id)
            )
        """)

        # 계약서 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quotation_id INTEGER,
                client_id INTEGER NOT NULL,
                contract_number TEXT UNIQUE,
                content TEXT,
                status TEXT DEFAULT 'pending',
                client_signature TEXT,
                client_signature_ip TEXT,
                client_signed_at TIMESTAMP,
                admin_signature TEXT,
                admin_signature_ip TEXT,
                admin_signed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quotation_id) REFERENCES quotations(id),
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        """)

        # 프로젝트 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER,
                client_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'planning',
                start_date DATE,
                end_date DATE,
                progress INTEGER DEFAULT 0,
                total_contract_amount REAL DEFAULT 0,
                share_token TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contract_id) REFERENCES contracts(id),
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        """)

        # 프로젝트 태스크 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'todo',
                priority TEXT DEFAULT 'medium',
                assigned_to TEXT,
                due_date DATE,
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        # 결제/정산 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                client_id INTEGER NOT NULL,
                payment_type TEXT,
                amount REAL NOT NULL,
                due_date DATE,
                paid_date DATE,
                status TEXT DEFAULT 'pending',
                invoice_number TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        """)

        # AI 사용 로그 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_type TEXT,
                prompt TEXT,
                response TEXT,
                tokens_used INTEGER DEFAULT 0,
                cost REAL DEFAULT 0,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 설정 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 기본 설정 값 추가
        default_settings = {
            'pricing_guideline': '웹사이트 제작: 기본 500만원부터\n랜딩페이지: 200만원부터\n앱 개발: 1000만원부터\n유지보수: 월 50만원부터',
            'smtp_host': '',
            'smtp_port': '587',
            'smtp_email': '',
            'smtp_password': '',
            'company_name': '에이전시명',
            'company_address': '',
            'company_phone': '',
        }

        for key, value in default_settings.items():
            cursor.execute("""
                INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
            """, (key, value))

        conn.commit()
        conn.close()


# ===== CRUD 메서드 =====

class ClientDB(Database):
    """고객 관련 데이터베이스 작업"""

    def add_client(self, name: str, email: str, phone: str = None,
                   company: str = None, source: str = 'survey', notes: str = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clients (name, email, phone, company, source, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, email, phone, company, source, notes))
        client_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return client_id

    def get_client(self, client_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_clients(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_client(self, client_id: int, **kwargs) -> bool:
        allowed_fields = ['name', 'email', 'phone', 'company', 'status', 'notes']
        updates = [f"{k} = ?" for k in kwargs.keys() if k in allowed_fields]
        if not updates:
            return False

        values = [v for k, v in kwargs.items() if k in allowed_fields]
        values.append(client_id)

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE clients SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, values)
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def delete_client(self, client_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0


class InquiryDB(Database):
    """문의/설문 관련 데이터베이스 작업"""

    def add_inquiry(self, client_id: int, project_type: str, budget: str,
                    duration: str, description: str, urgency: str = 'normal') -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inquiries (client_id, project_type, budget, duration, description, urgency)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (client_id, project_type, budget, duration, description, urgency))
        inquiry_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return inquiry_id

    def get_all_inquiries(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.*, c.name as client_name, c.email as client_email
            FROM inquiries i
            LEFT JOIN clients c ON i.client_id = c.id
            ORDER BY i.created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_inquiry(self, inquiry_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.*, c.name as client_name, c.email as client_email
            FROM inquiries i
            LEFT JOIN clients c ON i.client_id = c.id
            WHERE i.id = ?
        """, (inquiry_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


class QuotationDB(Database):
    """견적서 관련 데이터베이스 작업"""

    def add_quotation(self, client_id: int, items: List[Dict], total_amount: float,
                      inquiry_id: int = None, notes: str = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()

        # 견적서 번호 생성 (QT-YYYYMMDD-XXXX)
        date_str = datetime.now().strftime("%Y%m%d")
        cursor.execute("""
            SELECT COUNT(*) as count FROM quotations
            WHERE quotation_number LIKE ?
        """, (f"QT-{date_str}-%",))
        count = cursor.fetchone()['count'] + 1
        quotation_number = f"QT-{date_str}-{count:04d}"

        cursor.execute("""
            INSERT INTO quotations (client_id, inquiry_id, quotation_number, items_json, total_amount, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (client_id, inquiry_id, quotation_number, json.dumps(items), total_amount, notes))
        quotation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return quotation_id

    def get_all_quotations(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT q.*, c.name as client_name, c.email as client_email
            FROM quotations q
            LEFT JOIN clients c ON q.client_id = c.id
            ORDER BY q.created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_quotation(self, quotation_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT q.*, c.name as client_name, c.email as client_email, c.phone as client_phone
            FROM quotations q
            LEFT JOIN clients c ON q.client_id = c.id
            WHERE q.id = ?
        """, (quotation_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            data = dict(row)
            data['items'] = json.loads(data['items_json']) if data['items_json'] else []
            return data
        return None

    def update_quotation_status(self, quotation_id: int, status: str) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE quotations SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, quotation_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0


class ProjectDB(Database):
    """프로젝트 관련 데이터베이스 작업"""

    def add_project(self, client_id: int, name: str, description: str = None,
                    contract_id: int = None, total_contract_amount: float = 0) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()

        # 공유 토큰 생성
        import secrets
        share_token = secrets.token_urlsafe(16)

        cursor.execute("""
            INSERT INTO projects (client_id, contract_id, name, description, total_contract_amount, share_token)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (client_id, contract_id, name, description, total_contract_amount, share_token))
        project_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return project_id

    def get_all_projects(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, c.name as client_name
            FROM projects p
            LEFT JOIN clients c ON p.client_id = c.id
            ORDER BY p.created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_project(self, project_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, c.name as client_name, c.email as client_email
            FROM projects p
            LEFT JOIN clients c ON p.client_id = c.id
            WHERE p.id = ?
        """, (project_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_project_progress(self, project_id: int, progress: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE projects SET progress = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (progress, project_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0


class TaskDB(Database):
    """태스크 관련 데이터베이스 작업"""

    def add_task(self, project_id: int, title: str, description: str = None,
                 priority: str = 'medium', due_date: str = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()

        # 현재 프로젝트의 태스크 수 확인 후 order_index 설정
        cursor.execute("""
            SELECT COALESCE(MAX(order_index), -1) + 1 as next_order
            FROM tasks WHERE project_id = ?
        """, (project_id,))
        order_index = cursor.fetchone()['next_order']

        cursor.execute("""
            INSERT INTO tasks (project_id, title, description, priority, due_date, order_index)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project_id, title, description, priority, due_date, order_index))
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return task_id

    def get_project_tasks(self, project_id: int) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tasks WHERE project_id = ?
            ORDER BY order_index ASC
        """, (project_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_task_status(self, task_id: int, status: str) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        completed_at = "CURRENT_TIMESTAMP" if status == "done" else "NULL"
        cursor.execute(f"""
            UPDATE tasks SET status = ?, completed_at = {completed_at}
            WHERE id = ?
        """, (status, task_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def delete_task(self, task_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0


class SettingsDB(Database):
    """설정 관련 데이터베이스 작업"""

    def get_setting(self, key: str, default: str = "") -> str:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row['value'] if row else default

    def set_setting(self, key: str, value: str) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
        """, (key, value, value))
        conn.commit()
        conn.close()

    def get_all_settings(self) -> Dict[str, str]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        conn.close()
        return {row['key']: row['value'] for row in rows}
