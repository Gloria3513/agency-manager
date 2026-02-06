"""
분석 유틸리티
매출, 고객, 프로젝트, AI 사용 비용 분석기
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
from database import ProjectDB, ClientDB, QuotationDB, InquiryDB, SettingsDB


class RevenueAnalyzer:
    """매출 분석기"""

    def __init__(self, db: ProjectDB = None):
        self.db = db or ProjectDB()

    def get_monthly_revenue(self, years: int = 1) -> Dict[str, float]:
        """월별 매출 조회"""
        projects = self.db.get_all_projects()
        monthly_data = {}

        cutoff_date = datetime.now() - timedelta(days=365 * years)

        for project in projects:
            if project['created_at']:
                created = datetime.fromisoformat(project['created_at'])
                if created >= cutoff_date:
                    month_key = created.strftime("%Y-%m")
                    amount = project.get('total_contract_amount', 0) or 0
                    monthly_data[month_key] = monthly_data.get(month_key, 0) + amount

        return monthly_data

    def get_yoy_comparison(self) -> Dict:
        """전년 대비 매출 비교"""
        this_year = datetime.now().year
        last_year = this_year - 1

        projects = self.db.get_all_projects()

        this_year_revenue = 0
        last_year_revenue = 0

        for project in projects:
            if project['created_at']:
                created = datetime.fromisoformat(project['created_at'])
                amount = project.get('total_contract_amount', 0) or 0

                if created.year == this_year:
                    this_year_revenue += amount
                elif created.year == last_year:
                    last_year_revenue += amount

        growth_rate = 0
        if last_year_revenue > 0:
            growth_rate = ((this_year_revenue - last_year_revenue) / last_year_revenue) * 100

        return {
            'this_year': this_year_revenue,
            'last_year': last_year_revenue,
            'growth_rate': growth_rate,
            'trend': 'up' if growth_rate >= 0 else 'down'
        }

    def get_revenue_by_project_type(self) -> Dict[str, float]:
        """프로젝트 유형별 매출 (문의 기준)"""
        inquiry_db = InquiryDB()
        inquiries = inquiry_db.get_all_inquiries()

        revenue_by_type = {}

        for inquiry in inquiries:
            # 해당 문의와 연결된 프로젝트 찾기
            projects = self.db.get_all_projects()
            for project in projects:
                # (실제로는 project_id가 연결되어 있어야 함)
                amount = project.get('total_contract_amount', 0) or 0
                project_type = inquiry.get('project_type', 'other')
                revenue_by_type[project_type] = revenue_by_type.get(project_type, 0) + amount

        return revenue_by_type


class CustomerAnalyzer:
    """고객 분석기"""

    def __init__(self, db: ClientDB = None):
        self.db = db or ClientDB()

    def get_conversion_funnel(self) -> Dict:
        """고객 유입 퍼널 분석"""
        inquiry_db = InquiryDB()
        quotation_db = QuotationDB()
        project_db = ProjectDB()

        total_clients = len(self.db.get_all_clients())
        total_inquiries = len(inquiry_db.get_all_inquiries())
        total_quotations = len(quotation_db.get_all_quotations())
        total_projects = len(project_db.get_all_projects())

        # 승인된 견적서
        approved_quotations = sum(1 for q in quotation_db.get_all_quotations()
                                  if q['status'] == 'approved')

        return {
            'clients': total_clients,
            'inquiries': total_inquiries,
            'quotations': total_quotations,
            'approved_quotations': approved_quotations,
            'projects': total_projects,
            'conversion_rates': {
                'inquiry_to_quotation': (total_quotations / total_inquiries * 100) if total_inquiries > 0 else 0,
                'quotation_to_approval': (approved_quotations / total_quotations * 100) if total_quotations > 0 else 0,
                'approval_to_project': (total_projects / approved_quotations * 100) if approved_quotations > 0 else 0,
            }
        }

    def get_customer_source_breakdown(self) -> Dict[str, int]:
        """고객 유입 경로 분석"""
        clients = self.db.get_all_clients()

        source_counts = {}
        for client in clients:
            source = client.get('source', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1

        # 한글 라벨 변환
        label_map = {
            'direct': '직접',
            'survey': '설문',
            'referral': '소개',
            'sns': 'SNS',
            'unknown': '기타'
        }

        return {label_map.get(k, k): v for k, v in source_counts.items()}

    def get_repeat_customers(self) -> Tuple[int, float]:
        """재계약 고객 수 및 비율"""
        project_db = ProjectDB()
        projects = project_db.get_all_projects()

        # 고객별 프로젝트 수
        client_projects = {}
        for project in projects:
            client_id = project.get('client_id')
            if client_id:
                client_projects[client_id] = client_projects.get(client_id, 0) + 1

        repeat_clients = sum(1 for count in client_projects.values() if count > 1)
        total_active_clients = len(client_projects)

        repeat_rate = (repeat_clients / total_active_clients * 100) if total_active_clients > 0 else 0

        return repeat_clients, repeat_rate


class ProjectAnalyzer:
    """프로젝트 분석기"""

    def __init__(self, db: ProjectDB = None):
        self.db = db or ProjectDB()

    def get_completion_rate(self) -> Dict:
        """프로젝트 완료율 분석"""
        projects = self.db.get_all_projects()

        status_counts = {}
        for project in projects:
            status = project.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        total = len(projects)
        completed = status_counts.get('completed', 0)
        on_hold = status_counts.get('on_hold', 0)
        active = status_counts.get('active', 0)
        planning = status_counts.get('planning', 0)

        return {
            'total': total,
            'completed': completed,
            'active': active,
            'planning': planning,
            'on_hold': on_hold,
            'completion_rate': (completed / total * 100) if total > 0 else 0,
            'status_breakdown': status_counts
        }

    def get_average_project_duration(self) -> Dict[str, float]:
        """프로젝트 평균 수행 기간"""
        projects = self.db.get_all_projects()

        durations = []
        for project in projects:
            if project.get('start_date') and project.get('end_date'):
                try:
                    start = datetime.fromisoformat(project['start_date'])
                    end = datetime.fromisoformat(project['end_date'])
                    duration = (end - start).days
                    if duration > 0:
                        durations.append(duration)
                except:
                    pass

        if durations:
            return {
                'average_days': sum(durations) / len(durations),
                'min_days': min(durations),
                'max_days': max(durations),
                'total_projects': len(durations)
            }

        return {'average_days': 0, 'min_days': 0, 'max_days': 0, 'total_projects': 0}

    def get_project_value_distribution(self) -> Dict:
        """프로젝트 금액 분포"""
        projects = self.db.get_all_projects()

        amounts = [p.get('total_contract_amount', 0) or 0 for p in projects]
        amounts = [a for a in amounts if a > 0]

        if amounts:
            return {
                'total': sum(amounts),
                'average': sum(amounts) / len(amounts),
                'median': sorted(amounts)[len(amounts) // 2],
                'min': min(amounts),
                'max': max(amounts),
                'count': len(amounts)
            }

        return {'total': 0, 'average': 0, 'median': 0, 'min': 0, 'max': 0, 'count': 0}


class AIUsageAnalyzer:
    """AI 사용 비용 분석기"""

    def __init__(self, db: SettingsDB = None):
        self.db = db or SettingsDB()

    def get_usage_summary(self, days: int = 30) -> Dict:
        """기간별 AI 사용 요약"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT
                COUNT(*) as request_count,
                SUM(tokens_used) as total_tokens,
                SUM(cost) as total_cost,
                model
            FROM ai_logs
            WHERE created_at >= ?
            GROUP BY model
        """, (cutoff_date,))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        total_requests = sum(r['request_count'] for r in results)
        total_tokens = sum(r['total_tokens'] or 0 for r in results)
        total_cost = sum(r['total_cost'] or 0 for r in results)

        return {
            'total_requests': total_requests,
            'total_tokens': total_tokens,
            'total_cost': total_cost,
            'by_model': results
        }

    def get_cost_by_type(self, days: int = 30) -> Dict[str, float]:
        """요청 유형별 비용"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT
                request_type,
                COUNT(*) as count,
                SUM(cost) as total_cost
            FROM ai_logs
            WHERE created_at >= ?
            GROUP BY request_type
        """, (cutoff_date,))

        results = {row['request_type']: {
            'count': row['count'],
            'cost': row['total_cost'] or 0
        } for row in cursor.fetchall()}

        conn.close()
        return results

    def get_daily_usage(self, days: int = 30) -> List[Dict]:
        """일별 사용량 추이"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as request_count,
                SUM(tokens_used) as total_tokens,
                SUM(cost) as total_cost
            FROM ai_logs
            WHERE created_at >= ?
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """, (cutoff_date,))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results


class DashboardAnalytics:
    """대시보드 통합 분석"""

    def __init__(self):
        self.revenue = RevenueAnalyzer()
        self.customer = CustomerAnalyzer()
        self.project = ProjectAnalyzer()
        self.ai = AIUsageAnalyzer()

    def get_overview(self) -> Dict:
        """전체 개요"""
        return {
            'revenue_yoy': self.revenue.get_yoy_comparison(),
            'conversion_funnel': self.customer.get_conversion_funnel(),
            'project_completion': self.project.get_completion_rate(),
            'ai_usage': self.ai.get_usage_summary(),
        }

    def get_date_range_data(self, start_date: str, end_date: str) -> Dict:
        """날짜 범위별 데이터"""
        conn = SettingsDB().get_connection()
        cursor = conn.cursor()

        # 기간 내 프로젝트 매출
        cursor.execute("""
            SELECT SUM(total_contract_amount) as total
            FROM projects
            WHERE created_at >= ? AND created_at <= ?
        """, (start_date, end_date))
        revenue = cursor.fetchone()['total'] or 0

        # 기간 내 신규 고객
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM clients
            WHERE created_at >= ? AND created_at <= ?
        """, (start_date, end_date))
        new_clients = cursor.fetchone()['count']

        # 기간内 완료 프로젝트
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM projects
            WHERE updated_at >= ? AND updated_at <= ? AND status = 'completed'
        """, (start_date, end_date))
        completed_projects = cursor.fetchone()['count']

        conn.close()

        return {
            'revenue': revenue,
            'new_clients': new_clients,
            'completed_projects': completed_projects,
        }
