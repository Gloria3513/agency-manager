"""
워크플로우 템플릿
자주 사용되는 워크플로우 사전 정의
"""

from typing import Dict, List
from utils.workflow_engine import (
    Workflow, Action, TriggerType,
    get_action_handler
)


class WorkflowTemplates:
    """워크플로우 템플릿 모음"""

    @staticmethod
    def quotation_to_contract() -> Workflow:
        """견적 승인 → 계약 생성 워크플로우"""
        return Workflow(
            id=1,
            name="견적 승인 시 계약서 생성",
            trigger_type=TriggerType.QUOTATION_APPROVED,
            actions=[
                Action(
                    type="send_notification",
                    config={
                        "title": "견적 승인 알림",
                        "message": "견적이 승인되었습니다. 계약서를 생성하세요.",
                        "notification_type": "quotation_approved"
                    }
                ),
                Action(
                    type="update_status",
                    config={
                        "entity_type": "quotation",
                        "status": "ready_for_contract"
                    }
                )
            ],
            description="견적이 승인되면 계약서 생성을 알리고 상태를 변경합니다."
        )

    @staticmethod
    def contract_signed_to_project() -> Workflow:
        """계약 서명 → 프로젝트 시작 워크플로우"""
        return Workflow(
            id=2,
            name="계약 서명 시 프로젝트 시작",
            trigger_type=TriggerType.CONTRACT_SIGNED,
            actions=[
                Action(
                    type="create_task",
                    config={
                        "title": "프로젝트 킥오프 미팅",
                        "description": "고객과 프로젝트 시작 미팅 진행",
                        "priority": "high"
                    }
                ),
                Action(
                    type="send_notification",
                    config={
                        "title": "프로젝트 시작 알림",
                        "message": "계약이 체결되었습니다. 프로젝트를 시작하세요.",
                        "notification_type": "project_start"
                    }
                )
            ],
            description="계약이 서명되면 킥오프 태스크를 생성하고 알림을 보냅니다."
        )

    @staticmethod
    def payment_received() -> Workflow:
        """결제 수령 → 알림 워크플로우"""
        return Workflow(
            id=3,
            name="결제 입금 알림",
            trigger_type=TriggerType.PAYMENT_RECEIVED,
            actions=[
                Action(
                    type="send_notification",
                    config={
                        "title": "결제 입금 확인",
                        "message": "결제가 입금되었습니다.",
                        "notification_type": "payment_received"
                    }
                ),
                Action(
                    type="update_status",
                    config={
                        "entity_type": "payment",
                        "status": "paid"
                    }
                )
            ],
            description="결제가 입금되면 상태를 변경하고 알림을 보냅니다."
        )

    @staticmethod
    def inquiry_auto_reply() -> Workflow:
        """문의 자동 응대 워크플로우"""
        return Workflow(
            id=4,
            name="문의 자동 응대",
            trigger_type=TriggerType.INQUIRY_CREATED,
            actions=[
                Action(
                    type="send_notification",
                    config={
                        "title": "새 문의 도착",
                        "message": "새로운 프로젝트 문의가 도착했습니다.",
                        "notification_type": "new_inquiry"
                    }
                )
            ],
            description="새 문의가 도착하면 담당자에게 알림을 보냅니다."
        )

    @staticmethod
    def task_progress_calculation() -> Workflow:
        """태스크 완료 → 진행률 계산 워크플로우"""
        return Workflow(
            id=5,
            name="프로젝트 진행률 자동 계산",
            trigger_type=TriggerType.TASK_COMPLETED,
            actions=[
                Action(
                    type="calculate_value",
                    config={
                        "type": "project_progress"
                    }
                )
            ],
            description="태스크가 완료되면 프로젝트 진행률을 자동으로 계산합니다."
        )

    @staticmethod
    def project_completion_workflow() -> Workflow:
        """프로젝트 완료 워크플로우"""
        return Workflow(
            id=6,
            name="프로젝트 완료 처리",
            trigger_type=TriggerType.PROJECT_CREATED,
            actions=[],
            condition=lambda ctx: ctx.get('progress', 0) >= 100,
            description="프로젝트가 100% 완료되면 완료 처리를 합니다."
        )

    @staticmethod
    def all_templates() -> List[Workflow]:
        """모든 템플릿 반환"""
        return [
            WorkflowTemplates.quotation_to_contract(),
            WorkflowTemplates.contract_signed_to_project(),
            WorkflowTemplates.payment_received(),
            WorkflowTemplates.inquiry_auto_reply(),
            WorkflowTemplates.task_progress_calculation(),
            WorkflowTemplates.project_completion_workflow(),
        ]


def init_default_workflows() -> List[Workflow]:
    """기본 워크플로우 초기화"""
    return WorkflowTemplates.all_templates()


class WorkflowBuilder:
    """워크플로우 빌더"""

    def __init__(self):
        self.name = None
        self.description = None
        self.trigger_type = None
        self.actions = []
        self.condition = None

    def set_name(self, name: str):
        self.name = name
        return self

    def set_description(self, description: str):
        self.description = description
        return self

    def set_trigger(self, trigger_type: TriggerType):
        self.trigger_type = trigger_type
        return self

    def add_action(self, action_type: str, config: Dict = None):
        self.actions.append(Action(type=action_type, config=config or {}))
        return self

    def set_condition(self, condition):
        self.condition = condition
        return self

    def build(self, workflow_id: int) -> Workflow:
        if not self.name or not self.trigger_type:
            raise ValueError("Name and trigger_type are required")

        return Workflow(
            id=workflow_id,
            name=self.name,
            trigger_type=self.trigger_type,
            actions=self.actions,
            condition=self.condition,
            description=self.description
        )


# 사용 예제
def create_custom_workflow() -> Workflow:
    """사용자 정의 워크플로우 생성 예제"""
    return (WorkflowBuilder()
            .set_name("사용자 정의 워크플로우")
            .set_description("견적 승인 시 여러 작업 자동화")
            .set_trigger(TriggerType.QUOTATION_APPROVED)
            .add_action("send_notification", {
                "title": "알림",
                "message": "견적이 승인되었습니다."
            })
            .add_action("create_task", {
                "title": "계약서 준비",
                "priority": "high"
            })
            .build(workflow_id=999))
