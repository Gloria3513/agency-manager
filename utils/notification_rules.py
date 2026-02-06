"""
알림 규칙 정의
각 이벤트 유형별 알림 발생 조건과 대상 정의
"""

from typing import List, Dict, Callable, Optional
from enum import Enum


class NotificationEventType(Enum):
    """알림 이벤트 유형"""
    TASK_DUE = "task_due"                    # 태스크 마감 임박
    TASK_OVERDUE = "task_overdue"            # 태스크 연체
    PAYMENT_DUE = "payment_due"              # 결제일 도래
    PAYMENT_OVERDUE = "payment_overdue"      # 결제 연체
    NEW_INQUIRY = "new_inquiry"              # 새 문의
    QUOTATION_APPROVED = "quotation_approved" # 견적 승인
    CONTRACT_SIGNED = "contract_signed"       # 계약 서명
    PROJECT_MILESTONE = "project_milestone"   # 프로젝트 마일스톤
    AI_USAGE_LIMIT = "ai_usage_limit"         # AI 사용량 한계


class NotificationRule:
    """알림 규칙"""

    def __init__(self, event_type: NotificationEventType,
                 name: str,
                 description: str,
                 default_enabled: bool = True,
                 email_default: bool = True,
                 push_default: bool = True,
                 reminder_hours: List[int] = None,
                 handler: Callable = None):
        self.event_type = event_type
        self.name = name
        self.description = description
        self.default_enabled = default_enabled
        self.email_default = email_default
        self.push_default = push_default
        self.reminder_hours = reminder_hours or []
        self.handler = handler

    def should_notify(self, context: Dict) -> bool:
        """알림 발생 조건 확인"""
        if self.handler:
            return self.handler(context)
        return True


# 기본 알림 규칙 정의
DEFAULT_RULES: List[NotificationRule] = [
    NotificationRule(
        event_type=NotificationEventType.TASK_DUE,
        name="태스크 마감 알림",
        description="태스크 마감일 1일 전, 당일 알림",
        email_default=False,
        push_default=True,
        reminder_hours=[24, 0],  # 24시간 전, 당일
        handler=lambda ctx: ctx.get('status') != 'done'
    ),

    NotificationRule(
        event_type=NotificationEventType.TASK_OVERDUE,
        name="태스크 연체 알림",
        description="마감일 지난 미완료 태스크 알림",
        email_default=True,
        push_default=True,
        handler=lambda ctx: (
            ctx.get('due_date') and
            ctx.get('status') not in ['done', 'completed']
        )
    ),

    NotificationRule(
        event_type=NotificationEventType.PAYMENT_DUE,
        name="결제일 알림",
        description="결제일 3일 전, 당일 알림",
        email_default=True,
        push_default=True,
        reminder_hours=[72, 24, 0],
        handler=lambda ctx: ctx.get('status') == 'pending'
    ),

    NotificationRule(
        event_type=NotificationEventType.PAYMENT_OVERDUE,
        name="결제 연체 알림",
        description="결제일 지난 미납 알림",
        email_default=True,
        push_default=True,
        handler=lambda ctx: ctx.get('status') == 'pending'
    ),

    NotificationRule(
        event_type=NotificationEventType.NEW_INQUIRY,
        name="새 문의 알림",
        description="새로운 고객 문의 도착 시 알림",
        email_default=True,
        push_default=True,
        handler=lambda ctx: ctx.get('status') == 'new'
    ),

    NotificationRule(
        event_type=NotificationEventType.QUOTATION_APPROVED,
        name="견적 승인 알림",
        description="고객이 견적을 승인했을 때 알림",
        email_default=True,
        push_default=True,
        handler=lambda ctx: ctx.get('status') == 'approved'
    ),

    NotificationRule(
        event_type=NotificationEventType.CONTRACT_SIGNED,
        name="계약 서명 알림",
        description="계약서가 서명되었을 때 알림",
        email_default=True,
        push_default=True,
        handler=lambda ctx: ctx.get('client_signature') is not None
    ),

    NotificationRule(
        event_type=NotificationEventType.PROJECT_MILESTONE,
        name="프로젝트 마일스톤 알림",
        description="프로젝트 진행률 25%, 50%, 75%, 100% 도달 시 알림",
        email_default=False,
        push_default=True,
        handler=lambda ctx: ctx.get('progress', 0) in [25, 50, 75, 100]
    ),

    NotificationRule(
        event_type=NotificationEventType.AI_USAGE_LIMIT,
        name="AI 사용량 알림",
        description="월간 AI 사용량 $50 도달 시 알림",
        email_default=True,
        push_default=False,
        handler=lambda ctx: ctx.get('monthly_cost', 0) >= 50
    ),
]


def get_rule(event_type: NotificationEventType) -> Optional[NotificationRule]:
    """이벤트 타입에 해당하는 규칙 조회"""
    for rule in DEFAULT_RULES:
        if rule.event_type == event_type:
            return rule
    return None


def get_all_rules() -> List[NotificationRule]:
    """모든 알림 규칙 조회"""
    return DEFAULT_RULES.copy()


def check_and_notify(event_type: NotificationEventType, context: Dict) -> bool:
    """규칙 확인 후 알림 발생"""
    rule = get_rule(event_type)

    if not rule or not rule.default_enabled:
        return False

    if rule.should_notify(context):
        from utils.notification_manager import NotificationManager
        manager = NotificationManager()

        # 이벤트 타입별 알림 데이터 생성
        notification_data = create_notification_data(event_type, context)

        manager.send_notification(
            recipient_type='admin',
            notification_type=event_type.value,
            data=notification_data
        )
        return True

    return False


def create_notification_data(event_type: NotificationEventType,
                            context: Dict) -> Dict:
    """이벤트 타입별 알림 데이터 생성"""
    if event_type == NotificationEventType.TASK_DUE:
        return {
            'title': f"📋 태스크 마감: {context.get('title', '')}",
            'message': f"프로젝트 '{context.get('project_name', '')}'의 태스크가 마감일 {context.get('due_date', '')}입니다.",
            'link': f"/projects?project_id={context.get('project_id')}",
            'metadata': context
        }

    elif event_type == NotificationEventType.TASK_OVERDUE:
        return {
            'title': f"⚠️ 태스크 연체: {context.get('title', '')}",
            'message': f"마감일을 지난 태스크입니다.",
            'link': f"/projects?project_id={context.get('project_id')}",
            'metadata': context
        }

    elif event_type == NotificationEventType.PAYMENT_DUE:
        return {
            'title': f"💳 결제 예정: {context.get('invoice_number', '')}",
            'message': f"{context.get('amount', 0):,.0f}원 결제 예정 (마감: {context.get('due_date', '')})",
            'link': f"/payments",
            'metadata': context
        }

    elif event_type == NotificationEventType.PAYMENT_OVERDUE:
        return {
            'title': f"⚠️ 결제 연체: {context.get('invoice_number', '')}",
            'message': f"결제일이 지난 미납금이 있습니다.",
            'link': f"/payments",
            'metadata': context
        }

    elif event_type == NotificationEventType.NEW_INQUIRY:
        return {
            'title': f"📝 새 문의: {context.get('client_name', '')}",
            'message': f"{context.get('project_type', '')} 유형의 새로운 문의가 도착했습니다.",
            'link': f"/inquiries",
            'metadata': context
        }

    else:
        return {
            'title': '알림',
            'message': str(context),
            'metadata': context
        }
