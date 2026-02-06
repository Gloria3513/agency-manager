"""
캘린더 관리 유틸리티
이벤트 CRUD, 동기화, 자동 이벤트 생성 기능
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database import CalendarDB, TaskDB, ProjectDB


class CalendarManager:
    """캘린더 관리자"""

    def __init__(self, db: CalendarDB = None):
        self.db = db or CalendarDB()

    def create_event(self, title: str, start_date: str, end_date: str = None,
                     event_type: str = 'general', **kwargs) -> int:
        """이벤트 생성"""
        return self.db.add_event(
            title=title,
            start_date=start_date,
            end_date=end_date,
            event_type=event_type,
            **kwargs
        )

    def sync_from_tasks(self, project_id: int = None) -> int:
        """태스크에서 캘린더 이벤트 동기화"""
        task_db = TaskDB()
        project_db = ProjectDB()

        if project_id:
            tasks = task_db.get_project_tasks(project_id)
        else:
            # 모든 프로젝트의 태스크 가져오기
            projects = project_db.get_all_projects()
            tasks = []
            for project in projects:
                tasks.extend(task_db.get_project_tasks(project['id']))

        synced_count = 0

        for task in tasks:
            # 마감일이 있는 태스크만
            if task.get('due_date'):
                # 이미 이벤트가 있는지 확인
                existing_events = self.db.get_events_by_type('task')
                event_exists = any(
                    e.get('task_id') == task['id'] for e in existing_events
                )

                if not event_exists:
                    # 색상 결정 (우선순위별)
                    color_map = {
                        'high': '#ef4444',
                        'medium': '#f59e0b',
                        'low': '#10b981'
                    }
                    color = color_map.get(task.get('priority', 'medium'), '#3b82f6')

                    self.db.add_event(
                        title=f"📋 {task['title']}",
                        start_date=task['due_date'],
                        event_type='task',
                        task_id=task['id'],
                        project_id=task['project_id'],
                        description=task.get('description'),
                        all_day=True,
                        color=color
                    )
                    synced_count += 1

        return synced_count

    def sync_from_payments(self) -> int:
        """결제일에서 캘린더 이벤트 동기화"""
        import sqlite3
        from database import Database

        base_db = Database()
        conn = base_db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM payments
            WHERE due_date IS NOT NULL AND status != 'paid'
            ORDER BY due_date ASC
        """)
        payments = [dict(row) for row in cursor.fetchall()]
        conn.close()

        synced_count = 0

        for payment in payments:
            # 이미 이벤트가 있는지 확인
            existing_events = self.db.get_events_by_type('payment')
            event_exists = any(
                e.get('payment_id') == payment['id'] for e in existing_events
            )

            if not event_exists:
                self.db.add_event(
                    title=f"💳 {payment['payment_type']} - {payment.get('invoice_number', '')}",
                    start_date=payment['due_date'],
                    event_type='payment',
                    payment_id=payment['id'],
                    project_id=payment['project_id'],
                    description=f"금액: {payment['amount']:,}원",
                    all_day=True,
                    color='#8b5cf6'
                )
                synced_count += 1

        return synced_count

    def get_month_events(self, year: int, month: int) -> List[Dict]:
        """월간 이벤트 조회"""
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1}-01-01"
        else:
            end_date = f"{year}-{month+1:02d}-01"

        return self.db.get_all_events(start_date, end_date)

    def get_week_events(self, date: datetime) -> List[Dict]:
        """주간 이벤트 조회"""
        start_of_week = date - timedelta(days=date.weekday())
        end_of_week = start_of_week + timedelta(days=7)

        return self.db.get_all_events(
            start_of_week.strftime("%Y-%m-%d"),
            end_of_week.strftime("%Y-%m-%d")
        )

    def get_upcoming_events(self, days: int = 7) -> List[Dict]:
        """다가오는 이벤트 조회"""
        today = datetime.now().date()
        end_date = today + timedelta(days=days)

        return self.db.get_all_events(
            today.isoformat(),
            end_date.isoformat()
        )

    def get_events_by_date(self, date: str) -> List[Dict]:
        """특정 날짜의 이벤트 조회"""
        start = f"{date} 00:00:00"
        end = f"{date} 23:59:59"

        return self.db.get_all_events(start, end)

    def update_event(self, event_id: int, **kwargs) -> bool:
        """이벤트 업데이트"""
        return self.db.update_event(event_id, **kwargs)

    def delete_event(self, event_id: int) -> bool:
        """이벤트 삭제"""
        return self.db.delete_event(event_id)

    def get_event_statistics(self, start_date: str, end_date: str) -> Dict:
        """기간별 이벤트 통계"""
        events = self.db.get_all_events(start_date, end_date)

        stats = {
            'total': len(events),
            'by_type': {},
            'by_project': {}
        }

        for event in events:
            # 타입별 집계
            event_type = event.get('event_type', 'general')
            type_label = {
                'general': '일반',
                'task': '태스크',
                'payment': '결제',
                'meeting': '회의',
                'deadline': '마감'
            }.get(event_type, event_type)

            stats['by_type'][type_label] = stats['by_type'].get(type_label, 0) + 1

            # 프로젝트별 집계
            if event.get('project_id'):
                project_id = event['project_id']
                stats['by_project'][project_id] = stats['by_project'].get(project_id, 0) + 1

        return stats


def create_recurring_event(title: str, start_date: str, recurrence: str,
                           recurrence_end: str = None, **kwargs) -> List[int]:
    """반복 이벤트 생성

    Args:
        title: 이벤트 제목
        start_date: 시작 날짜 (YYYY-MM-DD)
        recurrence: 반복 주기 ('daily', 'weekly', 'monthly', 'yearly')
        recurrence_end: 반복 종료 날짜 (YYYY-MM-DD)
        **kwargs: add_event의 추가 인자

    Returns:
        생성된 이벤트 ID 리스트
    """
    db = CalendarDB()
    event_ids = []

    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(recurrence_end) if recurrence_end else start + timedelta(days=365)

    current = start

    if recurrence == 'daily':
        delta = timedelta(days=1)
    elif recurrence == 'weekly':
        delta = timedelta(weeks=1)
    elif recurrence == 'monthly':
        # 월별 처리는 별도
        delta = None
    elif recurrence == 'yearly':
        delta = timedelta(days=365)
    else:
        delta = None

    if delta:
        while current <= end:
            event_id = db.add_event(
                title=title,
                start_date=current.isoformat(),
                **kwargs
            )
            event_ids.append(event_id)
            current += delta

    return event_ids


class EventConflictChecker:
    """이벤트 충돌 확인"""

    def __init__(self, db: CalendarDB = None):
        self.db = db or CalendarDB()

    def check_conflict(self, start_date: str, end_date: str = None,
                      exclude_event_id: int = None) -> List[Dict]:
        """시간 충돌 확인"""
        events = self.db.get_all_events()

        conflicts = []
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date) if end_date else start

        for event in events:
            if exclude_event_id and event['id'] == exclude_event_id:
                continue

            if not event.get('start_date'):
                continue

            event_start = datetime.fromisoformat(event['start_date'])
            event_end = datetime.fromisoformat(event['end_date']) if event.get('end_date') else event_start

            # 시간 중복 확인
            if not (end < event_start or start > event_end):
                conflicts.append(event)

        return conflicts

    def find_available_slots(self, date: str, duration_minutes: int = 60,
                            work_start: int = 9, work_end: int = 18) -> List[str]:
        """가용 시간대 찾기"""
        events = self.db.get_events_by_date(date)

        # 하루 시간대 (30분 단위)
        slots = []
        for hour in range(work_start, work_end):
            for minute in [0, 30]:
                slot_time = f"{date} {hour:02d}:{minute:02d}:00"
                slots.append({
                    'time': slot_time,
                    'available': True
                })

        # 이벤트가 있는 시간대 마크
        for event in events:
            if event.get('all_day'):
                continue

            event_start = datetime.fromisoformat(event['start_date'])
            event_end = datetime.fromisoformat(event.get('end_date', event['start_date']))

            for slot in slots:
                slot_time = datetime.fromisoformat(slot['time'])
                slot_end = slot_time + timedelta(minutes=30)

                if slot_time < event_end and slot_end > event_start:
                    slot['available'] = False

        # 연속된 가용 시간대 그룹화
        available_slots = []
        current_slot_start = None

        for slot in slots:
            if slot['available']:
                if current_slot_start is None:
                    current_slot_start = slot['time']
            else:
                if current_slot_start:
                    slot_duration = (datetime.fromisoformat(slot['time']) -
                                   datetime.fromisoformat(current_slot_start)).total_seconds() / 60
                    if slot_duration >= duration_minutes:
                        available_slots.append(current_slot_start)
                    current_slot_start = None

        # 마지막 슬롯 확인
        if current_slot_start:
            slot_duration = (datetime.fromisoformat(slots[-1]['time']) +
                           timedelta(minutes=30) - datetime.fromisoformat(current_slot_start)).total_seconds() / 60
            if slot_duration >= duration_minutes:
                available_slots.append(current_slot_start)

        return available_slots
