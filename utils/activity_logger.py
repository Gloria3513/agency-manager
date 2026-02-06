"""
활동 로거
모든 사용자 활동을 자동으로 기록
"""

from functools import wraps
from typing import Callable, Optional
from database import ActivityLogDB


class ActivityLogger:
    """활동 로거"""

    def __init__(self):
        self.db = ActivityLogDB()

    def log(self, user_id: int, action: str, entity_type: str = None,
           entity_id: int = None, details: str = None, ip_address: str = None):
        """활동 로그 기록"""
        self.db.log_activity(
            user_id=user_id,
            action_type=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address
        )

    def log_creation(self, user_id: int, entity_type: str, entity_id: int,
                    entity_name: str = None):
        """생성 활동 로그"""
        details = f"{entity_type} 생성"
        if entity_name:
            details += f": {entity_name}"

        self.log(
            user_id=user_id,
            action=f"{entity_type}.created",
            entity_type=entity_type,
            entity_id=entity_id,
            details=details
        )

    def log_update(self, user_id: int, entity_type: str, entity_id: int,
                  changes: dict = None):
        """수정 활동 로그"""
        details = f"{entity_type} 수정"
        if changes:
            changed_fields = ", ".join(changes.keys())
            details += f" ({changed_fields})"

        self.log(
            user_id=user_id,
            action=f"{entity_type}.updated",
            entity_type=entity_type,
            entity_id=entity_id,
            details=details
        )

    def log_deletion(self, user_id: int, entity_type: str, entity_id: int,
                    entity_name: str = None):
        """삭제 활동 로그"""
        details = f"{entity_type} 삭제"
        if entity_name:
            details += f": {entity_name}"

        self.log(
            user_id=user_id,
            action=f"{entity_type}.deleted",
            entity_type=entity_type,
            entity_id=entity_id,
            details=details
        )

    def log_status_change(self, user_id: int, entity_type: str, entity_id: int,
                         old_status: str, new_status: str):
        """상태 변경 로그"""
        details = f"{entity_type} 상태 변경: {old_status} → {new_status}"

        self.log(
            user_id=user_id,
            action=f"{entity_type}.status_changed",
            entity_type=entity_type,
            entity_id=entity_id,
            details=details
        )

    def log_login(self, user_id: int, success: bool = True, ip_address: str = None):
        """로그인 로그"""
        action = "user.login_success" if success else "user.login_failed"
        details = "로그인 성공" if success else "로그인 실패"

        self.log(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address
        )

    def log_logout(self, user_id: int):
        """로그아웃 로그"""
        self.log(
            user_id=user_id,
            action="user.logout",
            details="로그아웃"
        )


# 전역 로거 인스턴스
_logger = None


def get_logger() -> ActivityLogger:
    """활동 로거 인스턴스 반환"""
    global _logger
    if _logger is None:
        _logger = ActivityLogger()
    return _logger


def log_activity(action: str, entity_type: str = None, entity_id: int = None,
                details: str = None):
    """데코레이터용 활동 로그 함수"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 함수 실행
            result = func(*args, **kwargs)

            # 활동 로그 (세션에서 user_id 가져오기)
            try:
                import streamlit as st
                if 'user' in st.session_state:
                    user_id = st.session_state.user.get('id')
                    logger = get_logger()
                    logger.log(
                        user_id=user_id,
                        action=action,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        details=details
                    )
            except:
                pass

            return result
        return wrapper
    return decorator


def auto_log(entity_type: str, action_type: str = 'created'):
    """자동 활동 로깅 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)

            # 결과에서 ID 추출
            entity_id = None
            if isinstance(result, int):
                entity_id = result
            elif isinstance(result, dict) and 'id' in result:
                entity_id = result['id']

            # 로그 기록
            try:
                import streamlit as st
                if 'user' in st.session_state:
                    logger = get_logger()

                    if action_type == 'created':
                        logger.log_creation(
                            user_id=st.session_state.user.get('id'),
                            entity_type=entity_type,
                            entity_id=entity_id
                        )
                    elif action_type == 'updated':
                        logger.log_update(
                            user_id=st.session_state.user.get('id'),
                            entity_type=entity_type,
                            entity_id=entity_id
                        )
                    elif action_type == 'deleted':
                        logger.log_deletion(
                            user_id=st.session_state.user.get('id'),
                            entity_type=entity_type,
                            entity_id=entity_id
                        )
            except:
                pass

            return result
        return wrapper
    return decorator
