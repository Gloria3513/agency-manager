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

        # 캘린더 이벤트 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP,
                event_type TEXT DEFAULT 'general',
                description TEXT,
                project_id INTEGER,
                task_id INTEGER,
                payment_id INTEGER,
                all_day BOOLEAN DEFAULT 1,
                location TEXT,
                color TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (task_id) REFERENCES tasks(id),
                FOREIGN KEY (payment_id) REFERENCES payments(id)
            )
        """)

        # 캘린더 리마인더 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendar_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                reminder_date TIMESTAMP NOT NULL,
                reminder_type TEXT DEFAULT 'email',
                sent BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES calendar_events(id)
            )
        """)

        # 시간 기록 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                entry_date DATE NOT NULL,
                task_id INTEGER,
                description TEXT,
                billable BOOLEAN DEFAULT 1,
                hourly_rate REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)

        # 타이머 세션 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                task_id INTEGER,
                title TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)

        # 파일 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                mime_type TEXT,
                uploaded_by TEXT DEFAULT 'admin',
                task_id INTEGER,
                category TEXT DEFAULT 'general',
                description TEXT,
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)

        # 파일 공유 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                share_token TEXT UNIQUE,
                expires_at TIMESTAMP,
                download_count INTEGER DEFAULT 0,
                max_downloads INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files(id)
            )
        """)

        # 알림 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_type TEXT DEFAULT 'admin',
                recipient_id INTEGER,
                title TEXT,
                message TEXT NOT NULL,
                notification_type TEXT DEFAULT 'info',
                link TEXT,
                metadata TEXT,
                is_read BOOLEAN DEFAULT 0,
                read_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 알림 설정 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                notification_type TEXT NOT NULL,
                email_enabled BOOLEAN DEFAULT 1,
                push_enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, notification_type)
            )
        """)

        # 포털 토큰 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portal_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                project_id INTEGER,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(id),
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        # 포털 활동 로그 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portal_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                description TEXT,
                ip_address TEXT,
                project_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(id),
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        # 고객 커뮤니케이션 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_communications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                project_id INTEGER,
                is_internal BOOLEAN DEFAULT 0,
                is_read BOOLEAN DEFAULT 0,
                read_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(id),
                FOREIGN KEY (project_id) REFERENCES projects(id)
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


class CalendarDB(Database):
    """캘린더 관련 데이터베이스 작업"""

    def add_event(self, title: str, start_date: str, end_date: str = None,
                  event_type: str = 'general', description: str = None,
                  project_id: int = None, task_id: int = None,
                  payment_id: int = None, all_day: bool = True,
                  location: str = None, color: str = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO calendar_events (title, start_date, end_date, event_type,
                description, project_id, task_id, payment_id, all_day, location, color)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, start_date, end_date, event_type, description,
              project_id, task_id, payment_id, all_day, location, color))

        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return event_id

    def get_event(self, event_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_events(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()

        if start_date and end_date:
            cursor.execute("""
                SELECT * FROM calendar_events
                WHERE start_date >= ? AND start_date <= ?
                ORDER BY start_date ASC
            """, (start_date, end_date))
        else:
            cursor.execute("SELECT * FROM calendar_events ORDER BY start_date ASC")

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_events_by_type(self, event_type: str) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM calendar_events
            WHERE event_type = ?
            ORDER BY start_date ASC
        """, (event_type,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_events_by_project(self, project_id: int) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM calendar_events
            WHERE project_id = ?
            ORDER BY start_date ASC
        """, (project_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_event(self, event_id: int, **kwargs) -> bool:
        allowed_fields = ['title', 'start_date', 'end_date', 'event_type',
                         'description', 'all_day', 'location', 'color']
        updates = [f"{k} = ?" for k in kwargs.keys() if k in allowed_fields]
        if not updates:
            return False

        values = [v for k, v in kwargs.items() if k in allowed_fields]
        values.append(event_id)

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE calendar_events SET {', '.join(updates)}
            WHERE id = ?
        """, values)
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def delete_event(self, event_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def add_reminder(self, event_id: int, reminder_date: str,
                     reminder_type: str = 'email', sent: bool = False) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO calendar_reminders (event_id, reminder_date, reminder_type, sent)
            VALUES (?, ?, ?, ?)
        """, (event_id, reminder_date, reminder_type, sent))
        reminder_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return reminder_id

    def get_pending_reminders(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, e.title as event_title, e.start_date as event_start
            FROM calendar_reminders r
            JOIN calendar_events e ON r.event_id = e.id
            WHERE r.sent = 0 AND r.reminder_date <= CURRENT_TIMESTAMP
            ORDER BY r.reminder_date ASC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def mark_reminder_sent(self, reminder_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE calendar_reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0


class TimeEntryDB(Database):
    """시간 추적 관련 데이터베이스 작업"""

    def add_entry(self, project_id: int, title: str, duration_minutes: int,
                  entry_date: str, task_id: int = None, description: str = None,
                  billable: bool = True, hourly_rate: float = 0) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO time_entries (project_id, title, duration_minutes, entry_date,
                task_id, description, billable, hourly_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_id, title, duration_minutes, entry_date, task_id,
              description, billable, hourly_rate))
        entry_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return entry_id

    def get_entries_by_project(self, project_id: int) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM time_entries
            WHERE project_id = ?
            ORDER BY entry_date DESC
        """, (project_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_entries_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM time_entries
            WHERE entry_date >= ? AND entry_date <= ?
            ORDER BY entry_date DESC
        """, (start_date, end_date))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_total_hours(self, project_id: int = None, start_date: str = None,
                        end_date: str = None, billable_only: bool = False) -> float:
        conn = self.get_connection()
        cursor = conn.cursor()

        query = "SELECT SUM(duration_minutes) as total FROM time_entries WHERE 1=1"
        params = []

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        if start_date:
            query += " AND entry_date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND entry_date <= ?"
            params.append(end_date)

        if billable_only:
            query += " AND billable = 1"

        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()

        total_minutes = result['total'] or 0
        return round(total_minutes / 60, 2)

    def update_entry(self, entry_id: int, **kwargs) -> bool:
        allowed_fields = ['title', 'duration_minutes', 'entry_date', 'description',
                         'billable', 'hourly_rate']
        updates = [f"{k} = ?" for k in kwargs.keys() if k in allowed_fields]
        if not updates:
            return False

        values = [v for k, v in kwargs.items() if k in allowed_fields]
        values.append(entry_id)

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE time_entries SET {', '.join(updates)}
            WHERE id = ?
        """, values)
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def delete_entry(self, entry_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM time_entries WHERE id = ?", (entry_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0


class TimeSessionDB(Database):
    """타이머 세션 관련 데이터베이스 작업"""

    def start_session(self, project_id: int, task_id: int = None,
                      title: str = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()

        # 진행 중인 세션 확인
        cursor.execute("""
            SELECT id FROM time_sessions
            WHERE project_id = ? AND end_time IS NULL
            ORDER BY start_time DESC LIMIT 1
        """, (project_id,))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return existing['id']

        cursor.execute("""
            INSERT INTO time_sessions (project_id, task_id, title, start_time)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (project_id, task_id, title))
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id

    def stop_session(self, session_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE time_sessions
            SET end_time = CURRENT_TIMESTAMP
            WHERE id = ? AND end_time IS NULL
        """, (session_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def get_active_session(self, project_id: int = None) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()

        if project_id:
            cursor.execute("""
                SELECT * FROM time_sessions
                WHERE project_id = ? AND end_time IS NULL
                ORDER BY start_time DESC LIMIT 1
            """, (project_id,))
        else:
            cursor.execute("""
                SELECT * FROM time_sessions
                WHERE end_time IS NULL
                ORDER BY start_time DESC LIMIT 1
            """)

        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_session_duration(self, session_id: int) -> int:
        """세션 지속 시간을 분 단위로 반환"""
        session = self.get_session(session_id)
        if not session:
            return 0

        start = datetime.fromisoformat(session['start_time'])
        end = datetime.fromisoformat(session['end_time']) if session['end_time'] else datetime.now()
        duration = int((end - start).total_seconds() / 60)
        return duration

    def get_session(self, session_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM time_sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


class FileDB(Database):
    """파일 관리 관련 데이터베이스 작업"""

    def add_file(self, project_id: int, filename: str, file_path: str,
                 file_size: int, mime_type: str, uploaded_by: str = 'admin',
                 task_id: int = None, category: str = 'general',
                 description: str = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()

        # 버전 번호 계산
        cursor.execute("""
            SELECT COALESCE(MAX(version), 0) + 1 as next_version
            FROM files
            WHERE project_id = ? AND filename = ?
        """, (project_id, filename))
        version = cursor.fetchone()['next_version']

        cursor.execute("""
            INSERT INTO files (project_id, filename, file_path, file_size,
                mime_type, uploaded_by, task_id, category, description, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_id, filename, file_path, file_size, mime_type,
              uploaded_by, task_id, category, description, version))

        file_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return file_id

    def get_file(self, file_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_files_by_project(self, project_id: int) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM files
            WHERE project_id = ?
            ORDER BY created_at DESC
        """, (project_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_files_by_category(self, project_id: int, category: str) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM files
            WHERE project_id = ? AND category = ?
            ORDER BY created_at DESC
        """, (project_id, category))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_file(self, file_id: int, **kwargs) -> bool:
        allowed_fields = ['filename', 'category', 'description']
        updates = [f"{k} = ?" for k in kwargs.keys() if k in allowed_fields]
        if not updates:
            return False

        values = [v for k, v in kwargs.items() if k in allowed_fields]
        values.append(file_id)

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE files SET {', '.join(updates)}
            WHERE id = ?
        """, values)
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def delete_file(self, file_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()

        # 파일 정보 가져오기
        cursor.execute("SELECT file_path FROM files WHERE id = ?", (file_id,))
        row = cursor.fetchone()

        if row:
            import os
            file_path = row['file_path']
            # 실제 파일 삭제
            if os.path.exists(file_path):
                os.remove(file_path)

        cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def get_file_versions(self, project_id: int, filename: str) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM files
            WHERE project_id = ? AND filename = ?
            ORDER BY version DESC
        """, (project_id, filename))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


class NotificationDB(Database):
    """알림 관련 데이터베이스 작업"""

    def create_notification(self, recipient_type: str, recipient_id: int = None,
                            title: str = None, message: str = None,
                            notification_type: str = 'info',
                            link: str = None, metadata: str = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notifications (recipient_type, recipient_id, title,
                message, notification_type, link, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (recipient_type, recipient_id, title, message,
              notification_type, link, metadata))
        notification_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return notification_id

    def get_notifications(self, recipient_type: str = 'admin',
                          unread_only: bool = False) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()

        if unread_only:
            cursor.execute("""
                SELECT * FROM notifications
                WHERE recipient_type = ? AND is_read = 0
                ORDER BY created_at DESC
            """, (recipient_type,))
        else:
            cursor.execute("""
                SELECT * FROM notifications
                WHERE recipient_type = ?
                ORDER BY created_at DESC
            """, (recipient_type,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def mark_as_read(self, notification_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE notifications SET is_read = 1, read_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (notification_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def mark_all_as_read(self, recipient_type: str = 'admin') -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE notifications SET is_read = 1, read_at = CURRENT_TIMESTAMP
            WHERE recipient_type = ? AND is_read = 0
        """, (recipient_type,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected

    def delete_notification(self, notification_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0


class NotificationPreferenceDB(Database):
    """알림 설정 관련 데이터베이스 작업"""

    def get_preference(self, user_id: int, notification_type: str) -> Dict:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM notification_preferences
            WHERE user_id = ? AND notification_type = ?
        """, (user_id, notification_type))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def set_preference(self, user_id: int, notification_type: str,
                       email_enabled: bool = True, push_enabled: bool = True) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO notification_preferences
            (user_id, notification_type, email_enabled, push_enabled)
            VALUES (?, ?, ?, ?)
        """, (user_id, notification_type, email_enabled, push_enabled))
        conn.commit()
        conn.close()
        return 0


class PortalTokenDB(Database):
    """포털 토큰 관련 데이터베이스 작업"""

    def create_token(self, client_id: int, project_id: int = None,
                     expires_days: int = 30) -> str:
        import secrets
        token = secrets.token_urlsafe(32)

        conn = self.get_connection()
        cursor = conn.cursor()

        # 만료일 계산
        from datetime import timedelta
        expires_at = datetime.now() + timedelta(days=expires_days)

        cursor.execute("""
            INSERT INTO portal_tokens (client_id, project_id, token, expires_at)
            VALUES (?, ?, ?, ?)
        """, (client_id, project_id, token, expires_at.isoformat()))

        conn.commit()
        conn.close()
        return token

    def validate_token(self, token: str) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, c.name as client_name
            FROM portal_tokens t
            LEFT JOIN clients c ON t.client_id = c.id
            WHERE t.token = ? AND t.is_active = 1
            AND (t.expires_at IS NULL OR t.expires_at > CURRENT_TIMESTAMP)
        """, (token,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def revoke_token(self, token: str) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE portal_tokens SET is_active = 0
            WHERE token = ?
        """, (token,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def get_client_tokens(self, client_id: int) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM portal_tokens
            WHERE client_id = ?
            ORDER BY created_at DESC
        """, (client_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


class PortalActivityDB(Database):
    """포털 활동 로그 관련 데이터베이스 작업"""

    def log_activity(self, client_id: int, activity_type: str,
                     description: str = None, ip_address: str = None,
                     project_id: int = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO portal_activity (client_id, activity_type, description,
                ip_address, project_id)
            VALUES (?, ?, ?, ?, ?)
        """, (client_id, activity_type, description, ip_address, project_id))
        activity_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return activity_id

    def get_client_activities(self, client_id: int, limit: int = 50) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM portal_activity
            WHERE client_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (client_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


class ClientCommunicationDB(Database):
    """고객 커뮤니케이션 관련 데이터베이스 작업"""

    def send_message(self, client_id: int, sender: str, message: str,
                     project_id: int = None, is_internal: bool = False) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO client_communications (client_id, sender, message,
                project_id, is_internal)
            VALUES (?, ?, ?, ?, ?)
        """, (client_id, sender, message, project_id, is_internal))
        msg_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return msg_id

    def get_messages(self, client_id: int, project_id: int = None,
                     include_internal: bool = False) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()

        if project_id:
            if include_internal:
                cursor.execute("""
                    SELECT * FROM client_communications
                    WHERE client_id = ? AND project_id = ?
                    ORDER BY created_at ASC
                """, (client_id, project_id))
            else:
                cursor.execute("""
                    SELECT * FROM client_communications
                    WHERE client_id = ? AND project_id = ? AND is_internal = 0
                    ORDER BY created_at ASC
                """, (client_id, project_id))
        else:
            if include_internal:
                cursor.execute("""
                    SELECT * FROM client_communications
                    WHERE client_id = ?
                    ORDER BY created_at ASC
                """, (client_id,))
            else:
                cursor.execute("""
                    SELECT * FROM client_communications
                    WHERE client_id = ? AND is_internal = 0
                    ORDER BY created_at ASC
                """, (client_id,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def mark_as_read(self, message_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE client_communications SET is_read = 1, read_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (message_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def get_unread_count(self, client_id: int) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM client_communications
            WHERE client_id = ? AND is_read = 0 AND sender != 'client'
        """, (client_id,))
        result = cursor.fetchone()
        conn.close()
        return result['count'] if result else 0
