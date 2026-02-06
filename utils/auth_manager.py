"""
인증 및 권한 관리자
사용자 인증, 권한 확인, 세션 관리
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from database import UserDB, RoleDB, ActivityLogDB


class AuthManager:
    """인증 관리자"""

    def __init__(self):
        self.user_db = UserDB()
        self.role_db = RoleDB()
        self.activity_db = ActivityLogDB()

    def hash_password(self, password: str) -> str:
        """비밀번호 해싱"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str, password_hash: str) -> bool:
        """비밀번호 확인"""
        return self.hash_password(password) == password_hash

    def create_user(self, email: str, name: str, password: str,
                   role: str = 'member', **kwargs) -> int:
        """사용자 생성"""
        password_hash = self.hash_password(password)
        return self.user_db.add_user(
            email=email,
            name=name,
            password_hash=password_hash,
            role=role,
            **kwargs
        )

    def authenticate(self, email: str, password: str) -> Optional[Dict]:
        """사용자 인증"""
        user = self.user_db.get_user_by_email(email)

        if user and user.get('is_active'):
            if self.verify_password(password, user.get('password_hash', '')):
                # 마지막 로그인 업데이트
                self.user_db.update_last_login(user['id'])
                return {
                    'id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'role': user['role'],
                    'avatar': user.get('avatar'),
                    'department': user.get('department')
                }

        return None

    def has_permission(self, user_role: str, permission: str) -> bool:
        """권한 확인"""
        # 관리자는 모든 권한 가짐
        if user_role == 'admin':
            return True

        return self.role_db.has_permission(user_role, permission)

    def can_access_project(self, user_id: int, project_id: int) -> bool:
        """프로젝트 접근 권한 확인"""
        # 관리자는 모든 프로젝트 접근 가능
        user = self.user_db.get_user(user_id)
        if user and user.get('role') == 'admin':
            return True

        # TODO: 프로젝트 멤버 테이블 확인 로직 추가
        return True

    def log_activity(self, user_id: int, action_type: str,
                    entity_type: str = None, entity_id: int = None,
                    details: str = None, ip_address: str = None):
        """활동 로그 기록"""
        self.activity_db.log_activity(
            user_id=user_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address
        )


class SessionManager:
    """세션 관리자"""

    def __init__(self):
        self.sessions = {}

    def create_session(self, user_data: Dict) -> str:
        """세션 생성"""
        session_token = secrets.token_urlsafe(32)

        self.sessions[session_token] = {
            'user': user_data,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(hours=24)
        }

        return session_token

    def get_session(self, session_token: str) -> Optional[Dict]:
        """세션 조회"""
        session = self.sessions.get(session_token)

        if session:
            # 만료 확인
            if datetime.now() > session['expires_at']:
                del self.sessions[session_token]
                return None

            return session['user']

        return None

    def refresh_session(self, session_token: str) -> Optional[str]:
        """세션 갱신"""
        session = self.sessions.get(session_token)

        if session:
            # 만료 연장
            session['expires_at'] = datetime.now() + timedelta(hours=24)
            return session_token

        return None

    def destroy_session(self, session_token: str) -> bool:
        """세션 삭제"""
        if session_token in self.sessions:
            del self.sessions[session_token]
            return True
        return False


class PermissionChecker:
    """권한 확인자"""

    # 역할별 권한 정의
    ROLE_PERMISSIONS = {
        'admin': [
            'users.create', 'users.read', 'users.update', 'users.delete',
            'clients.create', 'clients.read', 'clients.update', 'clients.delete',
            'projects.create', 'projects.read', 'projects.update', 'projects.delete',
            'tasks.create', 'tasks.read', 'tasks.update', 'tasks.delete',
            'quotations.create', 'quotations.read', 'quotations.update', 'quotations.delete', 'quotations.approve',
            'contracts.create', 'contracts.read', 'contracts.update', 'contracts.delete', 'contracts.sign',
            'payments.create', 'payments.read', 'payments.update', 'payments.delete',
            'files.create', 'files.read', 'files.update', 'files.delete',
            'reports.read',
            'settings.update',
        ],
        'manager': [
            'clients.create', 'clients.read', 'clients.update',
            'projects.create', 'projects.read', 'projects.update',
            'tasks.create', 'tasks.read', 'tasks.update', 'tasks.delete',
            'quotations.create', 'quotations.read', 'quotations.update', 'quotations.approve',
            'contracts.create', 'contracts.read', 'contracts.update',
            'payments.create', 'payments.read', 'payments.update',
            'files.create', 'files.read', 'files.update', 'files.delete',
            'reports.read',
        ],
        'member': [
            'clients.read',
            'projects.read', 'projects.update',
            'tasks.create', 'tasks.read', 'tasks.update',
            'quotations.read',
            'contracts.read',
            'payments.read',
            'files.create', 'files.read', 'files.update',
            'reports.read',
        ],
        'viewer': [
            'clients.read',
            'projects.read',
            'tasks.read',
            'quotations.read',
            'contracts.read',
            'payments.read',
            'files.read',
            'reports.read',
        ]
    }

    @classmethod
    def get_permissions(cls, role: str) -> List[str]:
        """역할별 권한 조회"""
        return cls.ROLE_PERMISSIONS.get(role, [])

    @classmethod
    def check_permission(cls, role: str, permission: str) -> bool:
        """권한 확인"""
        return permission in cls.get_permissions(role)

    @classmethod
    def can_perform_action(cls, role: str, action: str, entity: str) -> bool:
        """액션 수행 권한 확인

        Args:
            role: 사용자 역할
            action: 액션 (create, read, update, delete, approve, sign 등)
            entity: 엔티티 (users, clients, projects, tasks 등)
        """
        permission = f"{entity}.{action}"
        return cls.check_permission(role, permission)

    @classmethod
    def get_accessible_menus(cls, role: str) -> List[str]:
        """역할별 접근 가능 메뉴 조회"""
        all_menus = {
            'dashboard': 'projects.read',
            'clients': 'clients.read',
            'inquiries': 'clients.read',
            'quotations': 'quotations.read',
            'contracts': 'contracts.read',
            'projects': 'projects.read',
            'tasks': 'tasks.read',
            'payments': 'payments.read',
            'calendar': 'projects.read',
            'time_tracker': 'projects.read',
            'files': 'files.read',
            'reports': 'reports.read',
            'users': 'users.read',
            'teams': 'users.read',
            'settings': 'settings.update',
        }

        accessible = []
        for menu, permission in all_menus.items():
            if cls.check_permission(role, permission):
                accessible.append(menu)

        return accessible


def init_default_permissions():
    """기본 권한 초기화"""
    role_db = RoleDB()

    # 각 역할별 권한 등록
    for role, permissions in PermissionChecker.ROLE_PERMISSIONS.items():
        for permission in permissions:
            role_db.add_permission(role, permission)


def init_admin_user(email: str = 'admin@agency.com',
                   password: str = 'admin1234',
                   name: str = '관리자') -> int:
    """기본 관리자 계정 생성"""
    user_db = UserDB()
    auth = AuthManager()

    # 이미 존재하면 반환
    existing = user_db.get_user_by_email(email)
    if existing:
        return existing['id']

    # 관리자 계정 생성
    return auth.create_user(
        email=email,
        name=name,
        password=password,
        role='admin'
    )
