"""
포털 인증 모듈
토큰 기반 고객 포털 인증 처리
"""

from datetime import datetime, timedelta
from typing import Optional, Dict
import secrets
from database import PortalTokenDB, PortalActivityDB, ClientDB


class PortalAuth:
    """포털 인증 관리자"""

    def __init__(self):
        self.token_db = PortalTokenDB()
        self.activity_db = PortalActivityDB()
        self.client_db = ClientDB()

    def create_access_token(self, client_id: int, project_id: int = None,
                           expires_days: int = 30) -> str:
        """접속 토큰 생성"""
        token = self.token_db.create_token(
            client_id=client_id,
            project_id=project_id,
            expires_days=expires_days
        )

        # 활동 로그 기록
        self.activity_db.log_activity(
            client_id=client_id,
            activity_type='token_created',
            project_id=project_id
        )

        return token

    def validate_token(self, token: str) -> Optional[Dict]:
        """토큰 유효성 검사"""
        token_data = self.token_db.validate_token(token)

        if token_data:
            # 마지막 접속 시간 업데이트 (DB에 별도 컬럼 필요 시)
            self.activity_db.log_activity(
                client_id=token_data['client_id'],
                activity_type='token_validated'
            )

            return {
                'client_id': token_data['client_id'],
                'client_name': token_data.get('client_name'),
                'project_id': token_data.get('project_id'),
                'expires_at': token_data.get('expires_at')
            }

        return None

    def revoke_token(self, token: str) -> bool:
        """토큰 폐기"""
        return self.token_db.revoke_token(token)

    def revoke_all_client_tokens(self, client_id: int) -> int:
        """고객의 모든 토큰 폐기"""
        tokens = self.token_db.get_client_tokens(client_id)
        revoked_count = 0

        for token_data in tokens:
            if self.token_db.revoke_token(token_data['token']):
                revoked_count += 1

        return revoked_count

    def log_portal_access(self, client_id: int, ip_address: str = None) -> int:
        """포털 접속 로그 기록"""
        return self.activity_db.log_activity(
            client_id=client_id,
            activity_type='portal_access',
            ip_address=ip_address
        )

    def get_client_activities(self, client_id: int, limit: int = 50) -> list:
        """고객 활동 로그 조회"""
        return self.activity_db.get_client_activities(client_id, limit)

    def is_token_expired(self, token: str) -> bool:
        """토큰 만료 확인"""
        token_data = self.token_db.validate_token(token)
        return token_data is None


class PortalSession:
    """포털 세션 관리"""

    def __init__(self):
        self.auth = PortalAuth()

    def login(self, token: str, ip_address: str = None) -> Optional[Dict]:
        """토큰으로 로그인"""
        user_data = self.auth.validate_token(token)

        if user_data:
            # 접속 로그 기록
            self.auth.log_portal_access(
                client_id=user_data['client_id'],
                ip_address=ip_address
            )

            return {
                'authenticated': True,
                'client_id': user_data['client_id'],
                'client_name': user_data['client_name'],
                'project_id': user_data.get('project_id'),
                'expires_at': user_data.get('expires_at')
            }

        return {
            'authenticated': False,
            'error': 'Invalid or expired token'
        }

    def logout(self, token: str) -> bool:
        """로그아웃 (토큰 폐기)"""
        return self.auth.revoke_token(token)

    def refresh_token(self, old_token: str, expires_days: int = 30) -> Optional[str]:
        """토큰 갱신"""
        token_data = self.auth.validate_token(old_token)

        if token_data:
            # 이전 토큰 폐기
            self.auth.revoke_token(old_token)

            # 새 토큰 발급
            return self.auth.create_access_token(
                client_id=token_data['client_id'],
                project_id=token_data.get('project_id'),
                expires_days=expires_days
            )

        return None


def generate_portal_link(client_id: int, base_url: str = "http://localhost:8501/portal") -> str:
    """포털 접속 링크 생성"""
    auth = PortalAuth()
    token = auth.create_access_token(client_id)
    return f"{base_url}?token={token}"


def validate_portal_token(token: str) -> Optional[Dict]:
    """포털 토큰 검사 (편의 함수)"""
    auth = PortalAuth()
    return auth.validate_token(token)
