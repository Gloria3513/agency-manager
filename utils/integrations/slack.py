"""
Slack 연동
Slack 웹훅을 통한 알림 발송
"""

import requests
from typing import Dict, List, Optional
import json


class SlackNotifier:
    """Slack 알림 발송"""

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url

    def send_message(self, text: str, blocks: List[Dict] = None,
                    channel: str = None, username: str = "Agency Bot",
                    icon_emoji: str = ":rocket:") -> Dict:
        """Slack 메시지 발송"""
        if not self.webhook_url:
            return {"success": False, "error": "Webhook URL not configured"}

        payload = {
            "text": text,
            "username": username,
            "icon_emoji": icon_emoji
        }

        if blocks:
            payload["blocks"] = blocks

        if channel:
            payload["channel"] = channel

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            return {
                "success": True,
                "status_code": response.status_code
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def send_quotation_notification(self, client_name: str,
                                   quotation_number: str,
                                   amount: float) -> Dict:
        """견적 발송 알림"""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📄 새 견적서 발송"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*고객:*\n{client_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*견적번호:*\n{quotation_number}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*금액:*\n{amount:,.0f}원"
                    }
                ]
            }
        ]

        return self.send_message(
            text=f"새 견적서가 발송되었습니다 - {client_name}",
            blocks=blocks
        )

    def send_payment_notification(self, client_name: str,
                                  amount: float, payment_type: str) -> Dict:
        """결제 알림"""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "💳 결제 입금"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*고객:*\n{client_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*유형:*\n{payment_type}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*금액:*\n{amount:,.0f}원"
                    }
                ]
            }
        ]

        return self.send_message(
            text=f"결제가 입금되었습니다 - {client_name}: {amount:,.0f}원",
            blocks=blocks
        )

    def send_project_update(self, project_name: str,
                           progress: int, status: str) -> Dict:
        """프로젝트 업데이트 알림"""
        status_emoji = {
            "planning": "📋",
            "active": "🚧",
            "completed": "✅",
            "on_hold": "⏸️"
        }

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji.get(status, '📊')} 프로젝트 업데이트"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*프로젝트:*\n{project_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*진행률:*\n{progress}%"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*상태:*\n{status}"
                    }
                ]
            }
        ]

        return self.send_message(
            text=f"프로젝트 업데이트: {project_name} ({progress}%)",
            blocks=blocks
        )

    def send_task_reminder(self, task_title: str,
                          project_name: str, due_date: str) -> Dict:
        """태스크 마감 리마인더"""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⏰ 태스크 마감 임박"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*태스크:*\n{task_title}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*프로젝트:*\n{project_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*마감일:*\n{due_date}"
                    }
                ]
            }
        ]

        return self.send_message(
            text=f"태스크 마감 임박: {task_title}",
            blocks=blocks,
            icon_emoji=":alarm_clock:"
        )

    def send_new_inquiry(self, client_name: str,
                        project_type: str) -> Dict:
        """새 문의 알림"""
        type_labels = {
            "website": "🌐 웹사이트",
            "landing": "📄 랜딩페이지",
            "web_app": "💻 웹앱",
            "mobile_app": "📱 모바일앱",
            "maintenance": "🔧 유지보수",
            "consulting": "💡 컨설팅",
            "other": "📦 기타"
        }

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📝 새 문의 도착"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*고객:*\n{client_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*프로젝트:*\n{type_labels.get(project_type, project_type)}"
                    }
                ]
            }
        ]

        return self.send_message(
            text=f"새 문의가 도착했습니다 - {client_name}",
            blocks=blocks,
            icon_emoji=":incoming_envelope:"
        )


def get_slack_notifier(webhook_url: str = None) -> SlackNotifier:
    """Slack 알림 발송자 인스턴스 반환"""
    return SlackNotifier(webhook_url)
