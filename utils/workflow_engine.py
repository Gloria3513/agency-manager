"""
워크플로우 엔진
이벤트 기반 자동화 시스템
"""

from datetime import datetime
from typing import Callable, Dict, List, Any, Optional
from enum import Enum
import json


class TriggerType(Enum):
    """트리거 유형"""
    QUOTATION_APPROVED = "quotation.approved"
    CONTRACT_SIGNED = "contract.signed"
    PROJECT_CREATED = "project.created"
    TASK_COMPLETED = "task.completed"
    PAYMENT_RECEIVED = "payment.received"
    INQUIRY_CREATED = "inquiry.created"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class WorkflowEngine:
    """워크플로우 엔진"""

    def __init__(self):
        self.workflows = []
        self.triggers = {}
        self.actions = {}

    def register_workflow(self, workflow: 'Workflow'):
        """워크플로우 등록"""
        self.workflows.append(workflow)

    def register_trigger(self, trigger_type: TriggerType, handler: Callable):
        """트리거 핸들러 등록"""
        self.triggers[trigger_type] = handler

    def register_action(self, action_type: str, handler: Callable):
        """액션 핸들러 등록"""
        self.actions[action_type] = handler

    def execute_trigger(self, trigger_type: TriggerType, context: Dict) -> List[Dict]:
        """트리거 실행"""
        results = []

        for workflow in self.workflows:
            if workflow.trigger_type == trigger_type and workflow.is_active:
                if workflow.check_condition(context):
                    result = workflow.execute(context, self.actions)
                    results.append(result)

        return results

    def execute_workflow(self, workflow_id: int, context: Dict) -> Dict:
        """특정 워크플로우 실행"""
        for workflow in self.workflows:
            if workflow.id == workflow_id:
                return workflow.execute(context, self.actions)
        return None


class Workflow:
    """워크플로우"""

    def __init__(self, id: int, name: str, trigger_type: TriggerType,
                 actions: List['Action'], condition: Callable = None,
                 description: str = None):
        self.id = id
        self.name = name
        self.trigger_type = trigger_type
        self.actions = actions
        self.condition = condition
        self.description = description
        self.is_active = True
        self.created_at = datetime.now()

    def check_condition(self, context: Dict) -> bool:
        """조건 확인"""
        if self.condition:
            return self.condition(context)
        return True

    def execute(self, context: Dict, action_handlers: Dict) -> Dict:
        """워크플로우 실행"""
        results = {
            'workflow_id': self.id,
            'workflow_name': self.name,
            'executed_at': datetime.now().isoformat(),
            'actions': [],
            'success': True,
            'errors': []
        }

        for action in self.actions:
            try:
                handler = action_handlers.get(action.type)

                if handler:
                    action_result = handler.execute(context, action.config)
                    results['actions'].append({
                        'action_type': action.type,
                        'result': action_result
                    })
                else:
                    results['errors'].append(f"No handler found for action: {action.type}")

            except Exception as e:
                results['success'] = False
                results['errors'].append(str(e))

        return results


class Action:
    """액션"""

    def __init__(self, type: str, config: Dict = None):
        self.type = type
        self.config = config or {}


class ActionType(Enum):
    """액션 유형"""
    # 프로젝트 관련
    CREATE_PROJECT = "create_project"
    UPDATE_PROJECT_STATUS = "update_project_status"
    ASSIGN_TASK = "assign_task"

    # 알림 관련
    SEND_NOTIFICATION = "send_notification"
    SEND_EMAIL = "send_email"
    SEND_SLACK = "send_slack"

    # 문서 관련
    CREATE_CONTRACT = "create_contract"
    CREATE_INVOICE = "create_invoice"

    # 데이터 관련
    UPDATE_FIELD = "update_field"
    CALCULATE = "calculate"


# 기본 액션 핸들러

class ActionHandler:
    """액션 핸들러 베이스"""

    def execute(self, context: Dict, config: Dict) -> Any:
        """액션 실행"""
        raise NotImplementedError


class SendNotificationAction(ActionHandler):
    """알림 발송 액션"""

    def execute(self, context: Dict, config: Dict) -> Dict:
        from utils.notification_manager import NotificationManager

        manager = NotificationManager()

        return manager.send_notification(
            recipient_type=config.get('recipient_type', 'admin'),
            notification_type=config.get('notification_type', 'info'),
            data={
                'title': config.get('title', '알림'),
                'message': config.get('message', ''),
                'link': config.get('link')
            }
        )


class UpdateStatusAction(ActionHandler):
    """상태 업데이트 액션"""

    def execute(self, context: Dict, config: Dict) -> Dict:
        entity_type = config.get('entity_type')
        entity_id = context.get('entity_id') or config.get('entity_id')
        new_status = config.get('status')

        # 데이터베이스 업데이트
        if entity_type == 'project':
            from database import ProjectDB
            db = ProjectDB()
            db.update_project_progress(entity_id, config.get('progress', 0))
        elif entity_type == 'quotation':
            from database import QuotationDB
            db = QuotationDB()
            db.update_quotation_status(entity_id, new_status)

        return {'updated': True, 'entity_type': entity_type, 'status': new_status}


class CreateTaskAction(ActionHandler):
    """태스크 생성 액션"""

    def execute(self, context: Dict, config: Dict) -> Dict:
        from database import TaskDB

        db = TaskDB()

        task_id = db.add_task(
            project_id=config.get('project_id'),
            title=config.get('title'),
            description=config.get('description'),
            priority=config.get('priority', 'medium'),
            due_date=config.get('due_date')
        )

        return {'created': True, 'task_id': task_id}


class AssignUserAction(ActionHandler):
    """사용자 할당 액션"""

    def execute(self, context: Dict, config: Dict) -> Dict:
        # 사용자 할당 로직
        assignee_id = config.get('assignee_id')

        # 활동 로그 기록
        from utils.activity_logger import get_logger
        logger = get_logger()

        return {'assigned': True, 'assignee_id': assignee_id}


class CalculateValueAction(ActionHandler):
    """값 계산 액션"""

    def execute(self, context: Dict, config: Dict) -> Dict:
        calculation_type = config.get('type')

        if calculation_type == 'project_progress':
            # 프로젝트 진행률 계산
            from database import TaskDB, ProjectDB

            task_db = TaskDB()
            project_db = ProjectDB()

            project_id = config.get('project_id')
            tasks = task_db.get_project_tasks(project_id)

            total_tasks = len(tasks)
            completed_tasks = sum(1 for t in tasks if t['status'] == 'done')

            progress = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
            project_db.update_project_progress(project_id, progress)

            return {'calculated': True, 'progress': progress}

        return {'calculated': False}


# 액션 핸들러 레지스트리

ACTION_HANDLERS = {
    'send_notification': SendNotificationAction,
    'update_status': UpdateStatusAction,
    'create_task': CreateTaskAction,
    'assign_user': AssignUserAction,
    'calculate_value': CalculateValueAction,
}


def get_action_handler(action_type: str) -> ActionHandler:
    """액션 핸들러 조회"""
    handler_class = ACTION_HANDLERS.get(action_type)
    if handler_class:
        return handler_class()
    return None
