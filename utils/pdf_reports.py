"""
PDF 리포트 생성기
고급 리포트를 PDF 형식으로 생성
"""

from datetime import datetime, timedelta
from typing import List, Dict
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, KeepInFrame
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io


class PDFReportGenerator:
    """PDF 리포트 생성기"""

    def __init__(self, page_size=A4):
        self.page_size = page_size
        self.width, self.height = page_size
        self.margin = 2 * cm
        self.styles = getSampleStyleSheet()

        # 한글 폰트 설정
        self._setup_fonts()

    def _setup_fonts(self):
        """한글 폰트 설정"""
        try:
            # 시스템 폰트 사용
            pdfmetrics.registerFont(TTFont('Malgun', '/System/Library/Fonts/Supplemental/Malgun Gothic.ttf'))
            pdfmetrics.registerFont(TTFont('AppleGothic', '/System/Library/Fonts/AppleGothic.ttf'))
        except:
            pass

    def add_custom_styles(self):
        """사용자 정의 스타일 추가"""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))

        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#334155'),
            spaceBefore=20,
            spaceAfter=12
        ))

        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#64748b')
        ))

    def generate_monthly_report(self, report_data: Dict) -> bytes:
        """월간 리포트 생성"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )

        self.add_custom_styles()

        story = []

        # 제목
        story.append(Paragraph(f"{report_data.get('month')} 월간 보고서", self.styles['ReportTitle']))
        story.append(Spacer(1*cm))

        # 생성일
        story.append(Paragraph(
            f"생성일: {datetime.now().strftime('%Y년 %m월 %d일')}",
            self.styles['Subtitle']
        ))
        story.append(Spacer(2*cm))

        # 요약 통계
        story.append(Paragraph("요약 통계", self.styles['SectionTitle']))

        summary_data = [
            ["항목", "값"],
            ["신규 고객", str(report_data.get('new_clients', 0)) + "명"],
            ["진행 프로젝트", str(report_data.get('active_projects', 0)) + "개"],
            ["완료 프로젝트", str(report_data.get('completed_projects', 0)) + "개"],
            ["총 매출", f"{report_data.get('total_revenue', 0):,.0f}원"],
        ]

        summary_table = Table(summary_data, colWidths=[8*cm, 8*cm], hAlign='LEFT')
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, -1), 'Malgun'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))

        story.append(summary_table)
        story.append(Spacer(2*cm))

        # 월별 매출 차트 (테이블로 대체)
        story.append(Paragraph("월별 매출", self.styles['SectionTitle']))

        revenue_data = [["월", "매출액(원)"]]
        for month, revenue in report_data.get('monthly_revenue', {}).items():
            revenue_data.append([month, f"{revenue:,.0f}"])

        revenue_table = Table(revenue_data, colWidths=[6*cm, 10*cm], hAlign='LEFT')
        revenue_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, -1), 'Malgun'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))

        story.append(revenue_table)
        story.append(Spacer(2*cm))

        # 프로젝트 목록
        story.append(Paragraph("프로젝트 목록", self.styles['SectionTitle']))

        project_data = [["프로젝트명", "고객", "상태", "진행률"]]
        for project in report_data.get('projects', [])[:10]:
            project_data.append([
                project.get('name', ''),
                project.get('client_name', ''),
                project.get('status', ''),
                f"{project.get('progress', 0)}%"
            ])

        project_table = Table(project_data, colWidths=[6*cm, 5*cm, 3*cm, 3*cm], hAlign='LEFT')
        project_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, -1), 'Malgun'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))

        story.append(project_table)

        # PDF 생성
        doc.build(story)

        pdf_data = buffer.getvalue()
        buffer.close()

        return pdf_data

    def generate_project_report(self, project: Dict, tasks: List[Dict],
                               time_entries: List[Dict] = None) -> bytes:
        """프로젝트 상세 리포트 생성"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )

        self.add_custom_styles()

        story = []

        # 제목
        story.append(Paragraph(f"프로젝트 리포트: {project.get('name', '')}", self.styles['ReportTitle']))
        story.append(Spacer(1*cm))

        # 프로젝트 정보
        story.append(Paragraph("프로젝트 정보", self.styles['SectionTitle']))

        info_data = [
            ["항목", "내용"],
            ["프로젝트명", project.get('name', '')],
            ["고객", project.get('client_name', '')],
            ["상태", project.get('status', '')],
            ["진행률", f"{project.get('progress', 0)}%"],
            ["시작일", project.get('start_date', '') or '-'],
            ["종료일", project.get('end_date', '') or '-'],
            ["계약 금액", f"{project.get('total_contract_amount', 0):,.0f}원"],
        ]

        info_table = Table(info_data, colWidths=[6*cm, 10*cm], hAlign='LEFT')
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, -1), 'Malgun'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))

        story.append(info_table)
        story.append(Spacer(2*cm))

        # 태스크 목록
        if tasks:
            story.append(Paragraph("태스크 목록", self.styles['SectionTitle']))

            task_data = [["태스크명", "상태", "우선순위", "마감일"]]
            for task in tasks:
                task_data.append([
                    task.get('title', ''),
                    task.get('status', ''),
                    task.get('priority', ''),
                    task.get('due_date', '') or '-'
                ])

            task_table = Table(task_data, colWidths=[8*cm, 3*cm, 3*cm, 3*cm], hAlign='LEFT')
            task_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, -1), 'Malgun'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ]))

            story.append(task_table)

        # PDF 생성
        doc.build(story)

        pdf_data = buffer.getvalue()
        buffer.close()

        return pdf_data


def generate_monthly_report_pdf(report_data: Dict) -> bytes:
    """월간 리포트 PDF 생성 (편의 함수)"""
    generator = PDFReportGenerator()
    return generator.generate_monthly_report(report_data)


def generate_project_report_pdf(project: Dict, tasks: List[Dict]) -> bytes:
    """프로젝트 리포트 PDF 생성 (편의 함수)"""
    generator = PDFReportGenerator()
    return generator.generate_project_report(project, tasks)
