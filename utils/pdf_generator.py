"""
PDF 견적서 생성기
reportlab을 사용하여 전문적인 견적서 PDF 생성
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
from typing import Dict, Optional
import io
import os


class PDFQuotationGenerator:
    """PDF 견적서 생성 클래스"""

    def __init__(self):
        self.page_size = A4
        self.width, self.height = A4
        self.margin = 2 * cm
        self.font_registered = False  # 폰트 등록 상태 초기화

        # 한글 폰트 설정 (시스템 폰트 사용)
        self._setup_fonts()

    def _setup_fonts(self):
        """한글 폰트 설정"""
        # macOS 기본 한글 폰트
        font_paths = [
            "/System/Library/Fonts/Supplemental/AppleSDGothicNeo.ttc",
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
        ]

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('Korean', font_path))
                    self.font_registered = True  # 폰트 등록 성공
                    return
                except:
                    continue

        # 폰트를 찾지 못한 경우 기본 폰트 사용 (이미 False로 초기화됨)
        pass
    def generate_quotation_pdf(self, quotation: Dict, client: Dict,
                              company_info: Dict = None) -> bytes:
        """
        견적서 PDF 생성

        Args:
            quotation: 견적서 정보
            client: 고객 정보
            company_info: 회사 정보

        Returns:
            PDF 바이너리 데이터
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )

        # 문서 구성 요소
        story = []
        styles = getSampleStyleSheet()

        # 커스텀 스타일
        if self.font_registered:
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName='Korean',
                fontSize=24,
                textColor=colors.HexColor('#2563eb'),
                spaceAfter=0.5 * cm,
                alignment=TA_CENTER
            )
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontName='Korean',
                fontSize=10,
                leading=14
            )
            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Normal'],
                fontName='Korean',
                fontSize=12,
                leading=18
            )
        else:
            title_style = styles['Heading1']
            normal_style = styles['Normal']
            header_style = styles['Normal']

        # ===== 헤더 =====
        story.append(Spacer(1, 1 * cm))

        # 견적서 제목
        title = Paragraph("견 적 서", title_style)
        story.append(title)
        story.append(Spacer(1, 0.5 * cm))

        # ===== 회사 정보 =====
        company_data = []
        if company_info:
            company_name = company_info.get('name', '에이전시')
            company_addr = company_info.get('address', '')
            company_phone = company_info.get('phone', '')

            company_data = [
                [Paragraph(f"<b>{company_name}</b>", header_style)],
                [Paragraph(f"주소: {company_addr}", normal_style)] if company_addr else [],
                [Paragraph(f"연락처: {company_phone}", normal_style)] if company_phone else [],
            ]

        if company_data:
            company_table = Table(company_data, colWidths=[15 * cm])
            company_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(company_table)
            story.append(Spacer(1, 0.5 * cm))

        # ===== 견적서 정보 테이블 =====
        quotation_info = [
            ["견적번호", quotation.get('quotation_number', ''), "견적일자", format_date(quotation.get('created_at'))],
            ["고객명", client.get('name', ''), "유효기간", f"{quotation.get('validity_days', 30)}일"],
            ["연락처", client.get('phone', ''), "이메일", client.get('email', '')],
        ]

        info_table = Table(quotation_info, colWidths=[3 * cm, 5 * cm, 2 * cm, 5 * cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f1f5f9')),
            ('FONTNAME', (0, 0), (-1, -1), 'Korean' if self.font_registered else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 1 * cm))

        # ===== 품목 테이블 =====
        items = quotation.get('items', [])

        # 테이블 헤더
        item_headers = ["No", "품목명", "상세 설명", "수량", "단가", "금액"]
        item_data = [item_headers]

        # 품목 데이터
        for i, item in enumerate(items, 1):
            item_data.append([
                str(i),
                item.get('name', ''),
                item.get('description', ''),
                f"{item.get('quantity', 1)}{item.get('unit', '건')}",
                format_currency(item.get('unit_price', 0)),
                format_currency(item.get('amount', item.get('unit_price', 0) * item.get('quantity', 1)))
            ])

        # 합계 행
        total_amount = quotation.get('total_amount', 0)
        item_data.append(["", "", "", "", "합계", format_currency(total_amount)])
        item_data.append(["", "", "", "", "부가세(VAT)", format_currency(int(total_amount * 0.1))])
        item_data.append(["", "", "", "", "총액", format_currency(int(total_amount * 1.1))])

        # 테이블 생성
        item_table = Table(item_data, colWidths=[0.8 * cm, 3 * cm, 5 * cm, 1.5 * cm, 2.5 * cm, 2.2 * cm])
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Korean' if self.font_registered else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (4, -3), (-1, -1), 'RIGHT'),
            ('FONTNAME', (4, -3), (-1, -1), 'Korean' if self.font_registered else 'Helvetica-Bold'),
        ]))
        story.append(item_table)
        story.append(Spacer(1, 1 * cm))

        # ===== 비고 =====
        notes = quotation.get('notes', '')
        if notes:
            story.append(Paragraph("<b>비고:</b>", header_style))
            story.append(Paragraph(notes, normal_style))
            story.append(Spacer(1, 0.5 * cm))

        # ===== 약관 =====
        terms = [
            "1. 본 견적서는 제시된 유효기간 내에 한하여 유효합니다.",
            "2. 견적 금액은 프로젝트 범위에 따라 변동될 수 있습니다.",
            "3. 계약 진행 시 상세 일정과 내용을 협의하여 확정합니다.",
            "4. 기술적 요구사항 변경 시 추가 비용이 발생할 수 있습니다.",
        ]

        story.append(Paragraph("<b>견적 약관:</b>", header_style))
        for term in terms:
            story.append(Paragraph(term, normal_style))

        # ===== 푸터 =====
        story.append(Spacer(1, 2 * cm))

        if company_info:
            footer_text = f"""
            위와 같이 견적을 제출합니다.

            {datetime.now().strftime("%Y년 %m월 %d일")}

            {company_info.get('name', '에이전시')} 귀중
            """
            story.append(Paragraph(footer_text, normal_style))

        # PDF 생성
        doc.build(story)

        pdf_data = buffer.getvalue()
        buffer.close()

        return pdf_data


def format_date(date_str):
    """날짜 포맷팅"""
    if date_str:
        try:
            dt = datetime.fromisoformat(str(date_str).replace("T", " "))
            return dt.strftime("%Y.%m.%d")
        except:
            pass
    return "-"


def format_currency(amount):
    """금액 포맷팅"""
    try:
        amount = int(float(amount))
        if amount >= 10000:
            return f"{amount // 10000:,}만 {amount % 10000:,}원"
        return f"{amount:,}원"
    except:
        return "0원"
