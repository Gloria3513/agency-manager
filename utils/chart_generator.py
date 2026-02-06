"""
차트 생성 유틸리티
고급 차트 및 시각화 생성
"""

import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Optional
import pandas as pd


class ChartGenerator:
    """차트 생성기"""

    @staticmethod
    def create_revenue_trend_chart(monthly_data: Dict[str, float],
                                    title: str = "월별 매출 추이") -> go.Figure:
        """매출 추세 차트"""
        if not monthly_data:
            # 빈 차트
            fig = go.Figure()
            fig.update_layout(
                title=title,
                xaxis_title="월",
                yaxis_title="매출 (원)",
                template="plotly_white"
            )
            return fig

        months = sorted(monthly_data.keys())
        revenues = [monthly_data[m] for m in months]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=months,
            y=revenues,
            mode='lines+markers',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=8),
            fill='tozeroy',
            fillcolor='rgba(59, 130, 246, 0.1)',
            name='매출'
        ))

        fig.update_layout(
            title=title,
            xaxis_title="월",
            yaxis_title="매출 (원)",
            template="plotly_white",
            hovermode='x unified'
        )

        return fig

    @staticmethod
    def create_funnel_chart(funnel_data: Dict[str, int],
                            labels: Dict[str, str] = None) -> go.Figure:
        """깔때기 차트 (고객 유입 퍼널)"""
        if labels is None:
            labels = {
                'clients': '총 고객',
                'inquiries': '문의',
                'quotations': '견적',
                'approved_quotations': '승인',
                'projects': '프로젝트'
            }

        values = [
            funnel_data.get('clients', 0),
            funnel_data.get('inquiries', 0),
            funnel_data.get('quotations', 0),
            funnel_data.get('approved_quotations', 0),
            funnel_data.get('projects', 0)
        ]

        stage_labels = [labels.get(k, k) for k in
                       ['clients', 'inquiries', 'quotations', 'approved_quotations', 'projects']]

        fig = go.Figure(go.Funnel(
            y=stage_labels,
            x=values,
            textinfo="value+percent initial",
            marker=dict(
                color=['#3b82f6', '#6366f1', '#8b5cf6', '#a855f7', '#d946ef'],
                line=dict(width=2, color="white")
            )
        ))

        fig.update_layout(
            title="고객 유입 퍼널",
            template="plotly_white"
        )

        return fig

    @staticmethod
    def create_project_status_chart(status_data: Dict[str, int]) -> go.Figure:
        """프로젝트 상태 도넛 차트"""
        status_labels = {
            'planning': '기획중',
            'active': '진행중',
            'completed': '완료',
            'on_hold': '보류',
            'lost': '계약실패'
        }

        colors = {
            'planning': '#3b82f6',
            'active': '#f59e0b',
            'completed': '#10b981',
            'on_hold': '#ef4444',
            'lost': '#64748b'
        }

        labels = []
        values = []
        color_list = []

        for status, count in status_data.items():
            if count > 0:
                labels.append(status_labels.get(status, status))
                values.append(count)
                color_list.append(colors.get(status, '#64748b'))

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=.4,
            marker=dict(colors=color_list)
        )])

        fig.update_layout(
            title="프로젝트 상태 분포",
            template="plotly_white"
        )

        return fig

    @staticmethod
    def create_ai_cost_chart(daily_usage: List[Dict]) -> go.Figure:
        """AI 사용 비용 차트"""
        if not daily_usage:
            fig = go.Figure()
            fig.update_layout(
                title="AI 사용 비용 추이",
                xaxis_title="날짜",
                yaxis_title="비용 (USD)",
                template="plotly_white"
            )
            return fig

        dates = [d['date'] for d in daily_usage]
        costs = [d.get('total_cost', 0) for d in daily_usage]
        tokens = [d.get('total_tokens', 0) for d in daily_usage]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=dates,
            y=costs,
            mode='lines+markers',
            name='비용 (USD)',
            yaxis='y',
            line=dict(color='#ef4444', width=2)
        ))

        fig.add_trace(go.Scatter(
            x=dates,
            y=tokens,
            mode='lines+markers',
            name='토큰 수',
            yaxis='y2',
            line=dict(color='#3b82f6', width=2)
        ))

        fig.update_layout(
            title="AI 사용 비용 추이",
            xaxis_title="날짜",
            yaxis=dict(title="비용 (USD)", side="left"),
            yaxis2=dict(title="토큰 수", side="right", overlaying="y"),
            template="plotly_white",
            hovermode='x unified',
            legend=dict(x=0.01, y=0.99)
        )

        return fig

    @staticmethod
    def create_source_breakdown_chart(source_data: Dict[str, int]) -> go.Figure:
        """고객 유입 경로 분포 차트"""
        labels = list(source_data.keys())
        values = list(source_data.values())

        colors = ['#3b82f6', '#6366f1', '#8b5cf6', '#a855f7', '#d946ef']

        fig = go.Figure(data=[go.Bar(
            x=values,
            y=labels,
            orientation='h',
            marker=dict(color=colors[:len(labels)])
        )])

        fig.update_layout(
            title="고객 유입 경로",
            xaxis_title="고객 수",
            yaxis_title="유입 경로",
            template="plotly_white"
        )

        return fig

    @staticmethod
    def create_time_comparison_chart(current_period: Dict, last_period: Dict,
                                    metric_name: str = "매출") -> go.Figure:
        """기간 비교 차트"""
        categories = list(current_period.keys())
        current_values = list(current_period.values())
        last_values = list(last_period.values())

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=categories,
            y=current_values,
            name='현재 기간',
            marker_color='#3b82f6'
        ))

        fig.add_trace(go.Bar(
            x=categories,
            y=last_values,
            name='이전 기간',
            marker_color='#94a3b8'
        ))

        fig.update_layout(
            title=f"{metric_name} 기간 비교",
            barmode='group',
            template="plotly_white"
        )

        return fig

    @staticmethod
    def create_gauge_chart(value: float, title: str = "완료율",
                          max_value: int = 100) -> go.Figure:
        """게이지 차트"""
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = value,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': title},
            gauge = {
                'axis': {'range': [None, max_value]},
                'bar': {'color': "#3b82f6"},
                'steps': [
                    {'range': [0, max_value * 0.33], 'color': "#fee2e2"},
                    {'range': [max_value * 0.33, max_value * 0.66], 'color': "#fef3c7"},
                    {'range': [max_value * 0.66, max_value], 'color': "#dcfce7"},
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': max_value * 0.9
                }
            }
        ))

        fig.update_layout(
            template="plotly_white",
            height=300
        )

        return fig

    @staticmethod
    def create_stacked_area_chart(data: Dict[str, Dict[str, float]],
                                  title: str = "추이 비교") -> go.Figure:
        """스택 영역 차트"""
        fig = go.Figure()

        # 데이터 정리
        if data:
            first_key = list(data.keys())[0]
            dates = sorted(data[first_key].keys())

            colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

            for i, (category, values) in enumerate(data.items()):
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=[values.get(d, 0) for d in dates],
                    name=category,
                    mode='lines',
                    line=dict(width=0),
                    stackgroup='one',
                    fillcolor=colors[i % len(colors)]
                ))

        fig.update_layout(
            title=title,
            template="plotly_white",
            hovermode='x unified'
        )

        return fig


def create_dashboard_charts(analytics_data: Dict) -> Dict[str, go.Figure]:
    """대시보드용 차트 세트 생성"""
    generator = ChartGenerator()

    charts = {}

    # 매출 추세
    if 'monthly_revenue' in analytics_data:
        charts['revenue_trend'] = generator.create_revenue_trend_chart(
            analytics_data['monthly_revenue']
        )

    # 고객 퍼널
    if 'conversion_funnel' in analytics_data:
        charts['funnel'] = generator.create_funnel_chart(
            analytics_data['conversion_funnel']
        )

    # 프로젝트 상태
    if 'project_status' in analytics_data:
        charts['project_status'] = generator.create_project_status_chart(
            analytics_data['project_status']
        )

    # 유입 경로
    if 'source_breakdown' in analytics_data:
        charts['source_breakdown'] = generator.create_source_breakdown_chart(
            analytics_data['source_breakdown']
        )

    # AI 사용 비용
    if 'ai_daily_usage' in analytics_data:
        charts['ai_cost'] = generator.create_ai_cost_chart(
            analytics_data['ai_daily_usage']
        )

    return charts
