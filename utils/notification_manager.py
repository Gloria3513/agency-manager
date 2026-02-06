"""
알림 관리자
알림 생성, 전송, 처리
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from database import NotificationDB, NotificationPreferenceDB, TaskDB, ProjectDB
import inspect


class NotificationManager:
    """알림 관리자"""

    def __init__(self):
        self.db = NotificationDB()
        self.pref_db = NotificationPreferenceDB()

    def create_notification(self, recipient_type: str = 'admin',
                           recipient_id: int = None,
                           title: str = None,
                           message: str = None,
                           notification_type: str = 'info',
                           link: str = None,
                           metadata: Dict = None) -> int:
        """알림 생성"""
        import json
        metadata_json = json.dumps(metadata) if metadata else None

        return self.db.create_notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
            metadata=metadata_json
        )

    def get_unread_count(self, recipient_type: str = 'admin') -> int:
        """안 읽은 알림 수 조회"""
        notifications = self.db.get_notifications(recipient_type, unread_only=True)
        return len(notifications)

    def get_notifications(self, recipient_type: str = 'admin',
                         unread_only: bool = False,
                         limit: int = 50) -> List[Dict]:
        """알림 목록 조회"""
        notifications = self.db.get_notifications(recipient_type, unread_only)
        return notifications[:limit]

    def mark_as_read(self, notification_id: int) -> bool:
        """알림 읽음 표시"""
        return self.db.mark_as_read(notification_id)

    def mark_all_as_read(self, recipient_type: str = 'admin') -> int:
        """모든 알림 읽음 표시"""
        return self.db.mark_all_as_read(recipient_type)

    def delete_notification(self, notification_id: int) -> bool:
        """알림 삭제"""
        return self.db.delete_notification(notification_id)

    def send_notification(self, recipient_type: str,
                         notification_type: str,
                         data: Dict) -> Optional[int]:
        """알림 전송 (이메일/푸시)"""
        # 설정 확인
        preference = self.pref_db.get_preference(user_id=1, notification_type=notification_type)

        if not preference:
            # 기본 설정 사용
            email_enabled = True
            push_enabled = True
        else:
            email_enabled = preference.get('email_enabled', True)
            push_enabled = preference.get('push_enabled', True)

        # 인앱 알림 생성
        notification_id = self.create_notification(
            recipient_type=recipient_type,
            title=data.get('title'),
            message=data.get('message'),
            notification_type=notification_type,
            link=data.get('link'),
            metadata=data.get('metadata')
        )

        # 이메일 발송
        if email_enabled:
            self._send_email_notification(data)

        return notification_id

    def _send_email_notification(self, data: Dict):
        """이메일 알림 발송"""
        try:
            from utils import EmailSender
            from database import SettingsDB

            settings_db = SettingsDB()
            smtp_settings = settings_db.get_all_settings()
            sender = EmailSender.create_from_settings(smtp_settings)

            if sender and data.get('email'):
                sender.send_email(
                    to_email=data['email'],
                    subject=data.get('title', '알림'),
                    body=data.get('message', ''),
                    from_name=smtp_settings.get('company_name')
                )
        except Exception as e:
            print(f"이메일 발송 실패: {e}")

    def check_and_send_reminders(self):
        """리마인더 알림 확인 및 전송"""
        task_db = TaskDB()
        project_db = ProjectDB()

        # 마감일 임박 태스크
        projects = project_db.get_all_projects()
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        today = datetime.now().date()

        for project in projects:
            tasks = task_db.get_project_tasks(project['id'])

            for task in tasks:
                if task.get('due_date'):
                    due_date = datetime.fromisoformat(task['due_date']).date()

                    # 마감일이 내일이면 알림
                    if due_date == tomorrow and task['status'] != 'done':
                        self.send_notification(
                            recipient_type='admin',
                            notification_type='task_due',
                            data={
                                'title': f"태스크 마감 임박: {task['title']}",
                                'message': f"프로젝트 '{project['name']}'의 태스크 '{task['title']}'이 내일 마감됩니다.",
                                'link': f"/projects?project_id={project['id']}",
                                'metadata': {'task_id': task['id'], 'project_id': project['id']}
                            }
                        )

                    # 마감일이 지난 미완료 태스크
                    if due_date < today and task['status'] != 'done':
                        self.send_notification(
                            recipient_type='admin',
                            notification_type='task_overdue',
                            data={
                                'title': f"태스크 연체: {task['title']}",
                                'message': f"프로젝트 '{project['name']}'의 태스크 '{task['title']}'이 마감일을 지났습니다.",
                                'link': f"/projects?project_id={project['id']}",
                                'metadata': {'task_id': task['id'], 'project_id': project['id']}
                            }
                        )


class NotificationTemplate:
    """알림 템플릿"""

    @staticmethod
    def task_due(task_title: str, project_name: str, due_date: str) -> Dict:
        return {
            'title': f"📋 태스크 마감 임박: {task_title}",
            'message': f"프로젝트 '{project_name}'의 태스크 '{task_title}' 마감일이 {due_date}입니다.",
            'notification_type': 'task_due'
        }

    @staticmethod
    def payment_reminder(client_name: str, amount: float, due_date: str) -> Dict:
        return {
            'title': f"💳 결제 리마인더: {client_name}",
            'message': f"{client_name}님에게서 {amount:,.0f}원을 받아야 합니다. (마감: {due_date})",
            'notification_type': 'payment_reminder'
        }

    @staticmethod
    def project_milestone(project_name: str, milestone: str) -> Dict:
        return {
            'title': f"🎉 프로젝트 마일스톤: {project_name}",
            'message': f"프로젝트 '{project_name}'에서 {milestone}을(를) 달성했습니다!",
            'notification_type': 'milestone'
        }

    @staticmethod
    def new_inquiry(client_name: str, project_type: str) -> Dict:
        return {
            'title': f"📝 새 문의: {client_name}",
            'message': f"{client_name}님으로부터 새로운 '{project_type}' 문의가 도착했습니다.",
            'notification_type': 'new_inquiry'
        }

    @staticmethod
    def contract_signed(client_name: str, project_name: str) -> Dict:
        return {
            'title': f"✍️ 계약서 서명 완료: {client_name}",
            'message': f"{client_name}님이 '{project_name}' 프로젝트 계약서에 서명했습니다.",
            'notification_type': 'contract_signed'
        }


def send_bulk_notifications(recipients: List[str],
                           notification_type: str,
                           data: Dict) -> List[int]:
    """일괄 알림 발송"""
    manager = NotificationManager()
    notification_ids = []

    for recipient in recipients:
        notification_id = manager.send_notification(
            recipient_type=recipient,
            notification_type=notification_type,
            data=data
        )
        notification_ids.append(notification_id)

    return notification_ids
