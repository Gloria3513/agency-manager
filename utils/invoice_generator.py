"""
시간 기반 청구서 생성기
"""

from datetime import datetime
from typing import List, Dict, Optional
from database import TimeEntryDB, ProjectDB, ClientDB


class InvoiceGenerator:
    """청구서 생성기"""

    def __init__(self):
        self.time_db = TimeEntryDB()
        self.project_db = ProjectDB()
        self.client_db = ClientDB()

    def generate_invoice_from_time(self, project_id: int,
                                   start_date: str, end_date: str) -> Dict:
        """시간 기록으로 청구서 생성"""
        entries = self.time_db.get_entries_by_date_range(start_date, end_date)
        project_entries = [e for e in entries if e['project_id'] == project_id]

        if not project_entries:
            return None

        project = self.project_db.get_project(project_id)
        client = self.client_db.get_client(project['client_id']) if project else None

        # 청구 가능 항목 필터링
        billable_entries = [e for e in project_entries if e.get('billable', 1)]

        # 항목 그룹화
        items = []
        total_hours = 0
        total_amount = 0

        for entry in billable_entries:
            hours = entry['duration_minutes'] / 60
            rate = entry.get('hourly_rate', 0)
            amount = hours * rate if rate > 0 else 0

            items.append({
                'date': entry['entry_date'],
                'description': entry['title'],
                'hours': hours,
                'rate': rate,
                'amount': amount
            })

            total_hours += hours
            total_amount += amount

        return {
            'project': project,
            'client': client,
            'period': {'start': start_date, 'end': end_date},
            'items': items,
            'summary': {
                'total_hours': total_hours,
                'total_amount': total_amount,
                'entry_count': len(items)
            }
        }

    def calculate_invoice_totals(self, entries: List[Dict],
                                default_hourly_rate: float = 0) -> Dict:
        """청구서 합계 계산"""
        billable_entries = [e for e in entries if e.get('billable', 1)]

        total_minutes = sum(e['duration_minutes'] for e in billable_entries)
        total_hours = total_minutes / 60

        # 각 항목의 금액 계산
        subtotal = 0
        for entry in billable_entries:
            rate = entry.get('hourly_rate', default_hourly_rate)
            hours = entry['duration_minutes'] / 60
            subtotal += hours * rate

        tax = subtotal * 0.1  # 부가세 10%
        grand_total = subtotal + tax

        return {
            'total_hours': total_hours,
            'subtotal': subtotal,
            'tax': tax,
            'grand_total': grand_total,
            'item_count': len(billable_entries)
        }

    def format_invoice_items(self, entries: List[Dict]) -> List[Dict]:
        """청구서 항목 포맷팅"""
        items = []

        for entry in entries:
            if entry.get('billable', 1):
                hours = entry['duration_minutes'] / 60
                rate = entry.get('hourly_rate', 0)

                items.append({
                    'date': entry['entry_date'],
                    'description': entry['title'] or '작업',
                    'quantity': round(hours, 2),
                    'unit': '시간',
                    'unit_price': rate,
                    'amount': hours * rate
                })

        return items


def generate_timesheet_report(project_id: int, start_date: str,
                             end_date: str) -> Dict:
    """타임시트 리포트 생성"""
    time_db = TimeEntryDB()
    project_db = ProjectDB()

    entries = time_db.get_entries_by_date_range(start_date, end_date)
    project_entries = [e for e in entries if e['project_id'] == project_id]

    project = project_db.get_project(project_id)

    # 날짜별 그룹화
    daily_totals = {}
    for entry in project_entries:
        date = entry['entry_date']
        if date not in daily_totals:
            daily_totals[date] = {'billable': 0, 'non_billable': 0}

        if entry.get('billable', 1):
            daily_totals[date]['billable'] += entry['duration_minutes']
        else:
            daily_totals[date]['non_billable'] += entry['duration_minutes']

    # 전체 합계
    total_billable = sum(d['billable'] for d in daily_totals.values())
    total_non_billable = sum(d['non_billable'] for d in daily_totals.values())

    return {
        'project': project,
        'period': {'start': start_date, 'end': end_date},
        'daily_breakdown': daily_totals,
        'totals': {
            'billable_hours': total_billable / 60,
            'non_billable_hours': total_non_billable / 60,
            'total_hours': (total_billable + total_non_billable) / 60
        }
    }
