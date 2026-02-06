"""
전자 계약서 생성 및 관리 유틸리티
계약서 자동 생성, PDF 변환, 서명 검증
"""

import json
from datetime import datetime
from typing import Dict, Optional
import secrets


class ContractGenerator:
    """전자 계약서 생성 클래스"""

    def __init__(self):
        pass

    def generate_contract_from_quotation(self, quotation: Dict, client: Dict,
                                        company_info: Dict = None) -> Dict:
        """
        견적서를 바탕으로 계약서 내용 생성

        Returns:
            {
                "title": str,
                "content": str,  # HTML 형식 계약서 내용
                "amount": int,
                "items": list
            }
        """
        items = quotation.get('items', [])
        total_amount = quotation.get('total_amount', 0)
        vat = int(total_amount * 0.1)
        grand_total = total_amount + vat

        # 계약서 번호 생성
        contract_number = f"CTR-{datetime.now().strftime('%Y%m%d')}-{quotation['id']:04d}"

        # 품목 내용 생성
        items_html = ""
        for i, item in enumerate(items, 1):
            items_html += f"""
            <tr>
                <td>{i}</td>
                <td>{item.get('name', '-')}</td>
                <td>{item.get('description', '-') if 'description' in item else '-'}</td>
                <td>{item.get('quantity', 1)}</td>
                <td>{self._format_currency(item.get('unit_price', item.get('price', 0)))}</td>
            </tr>
            """

        # HTML 계약서 내용
        content = f"""
        <div class="contract-document">
            <h1>프로젝트 개발 의뢰 계약서</h1>

            <div class="contract-info">
                <div class="info-row">
                    <span class="label">계약 번호:</span>
                    <span class="value">{contract_number}</span>
                </div>
                <div class="info-row">
                    <span class="label">계약 일자:</span>
                    <span class="value">{datetime.now().strftime('%Y년 %m월 %d일')}</span>
                </div>
            </div>

            <h2>제1조 [계약의 목적]</h2>
            <p>갑(의뢰인)과 을(수행자)은 프로젝트 개발에 관한 다음 각 호의 사항을 합의하고 본 계약서를 작성한다.</p>

            <h2>제2조 [계약 내용]</h2>
            <table class="items-table">
                <thead>
                    <tr>
                        <th>No</th>
                        <th>품목</th>
                        <th>상세 내용</th>
                        <th>수량</th>
                        <th>단가</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>

            <h2>제3조 [계약 금액]</h2>
            <div class="amount-section">
                <div class="amount-row">
                    <span class="label">공급가액:</span>
                    <span class="value">{self._format_currency(total_amount)}</span>
                </div>
                <div class="amount-row">
                    <span class="label">부가세(10%):</span>
                    <span class="value">{self._format_currency(vat)}</span>
                </div>
                <div class="amount-row total">
                    <span class="label">합계:</span>
                    <span class="value">{self._format_currency(grand_total)}</span>
                </div>
            </div>

            <h2>제4조 [이행 기간]</h2>
            <p>계약일로부터 프로젝트 완료까지의 기간은 협의된 일정에 따른다.</p>

            <h2>제5조 [지급 조건]</h2>
            <ol>
                <li>계약금: 계약 체결 시 {self._format_currency(int(grand_total * 0.3))} (30%)</li>
                <li>중도금: 프로젝트 진행 50% 시 {self._format_currency(int(grand_total * 0.3))} (30%)</li>
                <li>잔금: 프로젝트 완료 및 납품 시 {self._format_currency(int(grand_total * 0.4))} (40%)</li>
            </ol>

            <h2>제6조 [계약의 해지]</h2>
            <p>갑 또는 을이 본 계약을 위반하였을 때, 상대방은 서면으로 계약 해지를 요구할 수 있으며, 이에 따른 손해배상을 청구할 수 있다.</p>

            <h2>제7조 [지적재산권]</h2>
            <p>본 프로젝트를 통해 산출된 모든 결과물에 대한 지적재산권은 잔금 지급 완료 후 갑에게 귀속된다. 단, 을이 개발한 소스코드의 라이브러리 및 공개 모듈은 그러하지 않다.</p>

            <h2>제8조 [기타]</h2>
            <p>본 계약서에 명시되지 않은 사항은 갑과 을이 합의하여 결정하며, 분쟁 발생 시 민사소송법에 따른 관할법원의 판결에 따른다.</p>

            <div class="signature-section">
                <div class="signature-box">
                    <h3>갑 (의뢰인)</h3>
                    <p>성명: {client['name']}</p>
                    <p>서명: <span class="signature-placeholder" id="client_sig">___________</span></p>
                    <p>날짜: <span class="date-placeholder" id="client_date">___________</span></p>
                </div>
                <div class="signature-box">
                    <h3>을 (수행자)</h3>
                    <p>상호: {company_info.get('name', '에이전시') if company_info else '에이전시'}</p>
                    <p>서명: <span class="signature-placeholder" id="admin_sig">___________</span></p>
                    <p>날짜: <span class="date-placeholder" id="admin_date">___________</span></p>
                </div>
            </div>

            <p class="contract-footer">
                본 계약서는 양 당사자가 서명 및 날인한 즉시 효력을 발생한다.<br>
                계약서 작성일: {datetime.now().strftime('%Y년 %m월 %d일')}
            </p>
        </div>
        """

        return {
            "contract_number": contract_number,
            "title": "프로젝트 개발 의뢰 계약서",
            "content": content,
            "amount": grand_total,
            "items": items,
            "total_amount": total_amount,
            "vat": vat
        }

    def _format_currency(self, amount):
        """금액 포맷팅"""
        try:
            amount = int(float(amount))
            if amount >= 10000:
                return f"{amount // 10000:,}만 {amount % 10000:,}원"
            return f"{amount:,}원"
        except:
            return "0원"


class SignatureVerifier:
    """서명 검증 클래스"""

    @staticmethod
    def generate_signature_token() -> str:
        """서명용 토큰 생성 (보안)"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def verify_signature_format(signature_data: str) -> bool:
        """서명 데이터 형식 검증"""
        if not signature_data:
            return False

        # Base64 형식의 PNG 데이터 검증
        if signature_data.startswith("data:image/png;base64,"):
            return True
        if signature_data.startswith("data:image/svg+xml"):
            return True

        return False

    @staticmethod
    def extract_signature_metadata(request_data: Dict) -> Dict:
        """서명 시 메타데이터 추출"""
        return {
            "ip_address": request_data.get("ip_address", "0.0.0.0"),
            "user_agent": request_data.get("user_agent", ""),
            "timestamp": datetime.now().isoformat(),
            "email": request_data.get("email", ""),
        }


def generate_contract_pdf_content(contract: Dict, client: Dict,
                                  company_info: Dict = None) -> str:
    """
    PDF용 계약서 내용 생성 (reportlab용)

    Returns 텍스트 형식 계약서
    """
    items = contract.get('items', [])

    content_lines = [
        "프로젝트 개발 의뢰 계약서",
        "",
        f"계약 번호: {contract.get('contract_number', '-')}",
        f"계약 일자: {datetime.now().strftime('%Y년 %m월 %d일')}",
        "",
        "제1조 [계약의 목적]",
        "갑(의뢰인)과 을(수행자)은 프로젝트 개발에 관한 다음 각 호의 사항을 합의하고 본 계약서를 작성한다.",
        "",
        "제2조 [계약 내용]",
        "",
    ]

    # 품목 목록
    for i, item in enumerate(items, 1):
        content_lines.append(f"{i}. {item.get('name', '-')} - {item.get('description', '-')}")

    content_lines.extend([
        "",
        f"제3조 [계약 금액]",
        f"공급가액: {contract.get('total_amount', 0):,}원",
        f"부가세: {contract.get('vat', 0):,}원",
        f"합계: {contract.get('amount', 0):,}원",
        "",
        "제4조 [지급 조건]",
        f"- 계약금: {int(contract.get('amount', 0) * 0.3):,}원 (30%)",
        f"- 중도금: {int(contract.get('amount', 0) * 0.3):,}원 (30%)",
        f"- 잔금: {int(contract.get('amount', 0) * 0.4):,}원 (40%)",
        "",
        "제5조 [이행 기간]",
        "계약일로부터 프로젝트 완료까지의 기간은 협의된 일정에 따른다.",
        "",
        "제6조 [지적재산권]",
        "본 프로젝트를 통해 산출된 모든 결과물에 대한 지적재산권은 잔금 지급 완료 후 갑에게 귀속된다.",
        "",
        f"갑 (의뢰인): {client.get('name', '-')}",
        f"을 (수행자): {company_info.get('name', '에이전시') if company_info else '에이전시'}",
        "",
        f"작성일: {datetime.now().strftime('%Y년 %m월 %d일')}",
    ])

    return "\n".join(content_lines)
