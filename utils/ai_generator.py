"""
AI 견적서 생성기
Google Gemini API를 사용하여 고객 문의 내용과 단가 지침을 참조하여 자동 견적서 생성
"""

import json
import re
from typing import List, Dict, Optional

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class AIQuotationGenerator:
    """AI 기반 견적서 생성 클래스 - Gemini API 사용"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.model = "gemini-2.0-flash-exp"  # 빠르고 저렴한 모델

        if api_key and GEMINI_AVAILABLE:
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(self.model)
        else:
            self.client = None

    def generate_quotation(self, inquiry: Dict, pricing_guideline: str,
                          company_info: Dict = None) -> Dict:
        """
        문의 내용과 단가 지침을 바탕으로 AI가 견적서를 자동 생성

        Args:
            inquiry: 고객 문의 정보
            pricing_guideline: 단가 지침 텍스트
            company_info: 회사 정보 (선택)

        Returns:
            {
                "items": List[Dict],  # 품목 목록
                "total_amount": int,  # 총액
                "notes": str,         # 견적 메모
                "tokens_used": int,   # 사용 토큰
                "estimated_cost": float  # 예상 비용(USD)
            }
        """
        if not self.client:
            return self._fallback_quotation(inquiry)

        # 프롬프트 구성
        prompt = self._build_prompt(inquiry, pricing_guideline, company_info)

        try:
            response = self.client.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=2048,
                    response_mime_type="application/json"
                )
            )

            # 응답 파싱
            content = response.text
            result = json.loads(content)

            # 토큰 사용량 및 비용 계산
            tokens_used = response.usage_metadata.total_token_count if hasattr(response.usage_metadata, 'total_token_count') else 0
            estimated_cost = self._calculate_cost(tokens_used)

            result["tokens_used"] = tokens_used
            result["estimated_cost"] = estimated_cost

            return result

        except Exception as e:
            print(f"AI generation error: {e}")
            return self._fallback_quotation(inquiry)

    def _build_prompt(self, inquiry: Dict, pricing_guideline: str,
                     company_info: Dict = None) -> str:
        """프롬프트 생성"""
        prompt = f"""당신은 전문적인 견적 전문가입니다.
고객의 문의 내용과 단가 지침을 바탕으로 상세하고 실현 가능한 견적서를 작성하세요.

# 고객 문의 내용

## 고객 정보
- 이름: {inquiry.get('client_name', '-')}
- 이메일: {inquiry.get('client_email', '-')}

## 프로젝트 요청사항
- 프로젝트 유형: {inquiry.get('project_type', '-')}
- 예산: {inquiry.get('budget', '-')}
- 희망 기간: {inquiry.get('duration', '-')}
- 상세 내용:
{inquiry.get('description', '-')}

---

# 단가 지침

{pricing_guideline}

---

# 요청사항

위 정보를 바탕으로 상세한 견적서를 작성해주세요.

주의사항:
1. 고객의 예산 범위를 고려하세요
2. 희망 기간에 맞춰 일정을 계획에 포함하세요
3. 각 품목에 대해 명확한 근거를 제시하세요
4. 총액은 고객 예산의 80-120% 범위가 이상적입니다

---

# 출력 형식

반드시 다음 JSON 형식으로만 출력하세요:
{{
  "items": [
    {{"name": "품목명", "description": "상세 설명", "quantity": 1, "unit": "건", "unit_price": 1000000}},
    ...
  ],
  "total_amount": 5000000,
  "notes": "견적 관련 메모",
  "rationale": "견적 산출 근거"
}}

금액은 원화(원) 단위로, 숫자만 입력하세요. (콤마, "원" 등 제외)
"""

        if company_info:
            prompt += f"""

# 회사 정보
- 회사명: {company_info.get('name', '-')}
- 연락처: {company_info.get('phone', '-')}
"""

        return prompt

    def _calculate_cost(self, tokens: int) -> float:
        """토큰 사용량을 USD 비용으로 변환 (Gemini Flash 기준)"""
        # Gemini 2.0 Flash: 입력 $0.075/1M tokens, 출력 $0.30/1M tokens
        # 평균적으로 입력:출력 = 1:2 가정
        input_cost = (tokens / 3) * 0.075 / 1_000_000
        output_cost = (tokens * 2 / 3) * 0.30 / 1_000_000
        return input_cost + output_cost

    def _fallback_quotation(self, inquiry: Dict) -> Dict:
        """AI가 unavailable일 때의 fallback 견적서"""
        project_type = inquiry.get('project_type', 'other')

        # 기본 견적 템플릿
        items = [
            {
                "name": "프로젝트 기획 및 설계",
                "description": "요구사항 분석, 와이어프레임, UI/UX 설계",
                "quantity": 1,
                "unit": "건",
                "unit_price": 1000000
            },
            {
                "name": "개발",
                "description": f"{project_type} 유형에 따른 개발 작업",
                "quantity": 1,
                "unit": "건",
                "unit_price": 3000000
            },
            {
                "name": "테스트 및 배포",
                "description": "기능 테스트, 버그 수정, 서버 배포",
                "quantity": 1,
                "unit": "건",
                "unit_price": 500000
            }
        ]

        total_amount = sum(item['unit_price'] for item in items)

        return {
            "items": items,
            "total_amount": total_amount,
            "notes": "AI를 사용할 수 없어 기본 견적서가 생성되었습니다. 내용을 검토 후 수정하세요.",
            "rationale": "기본 견적 템플릿 사용",
            "tokens_used": 0,
            "estimated_cost": 0
        }


class AIEmailGenerator:
    """AI 기반 이메일 생성 클래스 - Gemini API 사용"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.model = "gemini-2.0-flash-exp"

        if api_key and GEMINI_AVAILABLE:
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(self.model)
        else:
            self.client = None

    def generate_quotation_email(self, client_name: str, quotation_number: str,
                                 quotation_url: str, company_info: Dict = None) -> str:
        """견적서 발송용 이메일 생성"""

        if not self.client:
            return self._fallback_email(client_name, quotation_number, quotation_url)

        company_name = company_info.get('name', '스마택트') if company_info else '스마택트'

        prompt = f"""다음 정보를 바탕으로 정중한 견적서 발송 이메일을 작성해주세요.

# 정보
- 고객명: {client_name}
- 견적서 번호: {quotation_number}
- 견적서 확인 링크: {quotation_url}
- 회사명: {company_name}

# 요청사항
- 정중하고 전문적인 톤
- 견적서 확인 요청
- 문의 있을 시 연락처 안내 (smatact@gmail.com / 010-4782-3513)
- HTML 형식이 아닌 일반 텍스트로 작성

이메일 제목과 본문을 각각 "제목:"과 "본문:"으로 구분하여 작성해주세요."""

        try:
            response = self.client.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.5,
                    max_output_tokens=500
                )
            )

            content = response.text

            # subject와 body 분리
            subject_match = re.search(r"제목:\s*(.+?)(?:\n|$)", content, re.IGNORECASE)
            body_match = re.search(r"본문:\s*(.+)", content, re.IGNORECASE | re.DOTALL)

            subject = subject_match.group(1).strip() if subject_match else f"[견적서] {quotation_number}"
            body = body_match.group(1).strip() if body_match else content

            return {"subject": subject, "body": body}

        except Exception as e:
            print(f"Email generation error: {e}")
            return self._fallback_email(client_name, quotation_number, quotation_url)

    def _fallback_email(self, client_name: str, quotation_number: str,
                       quotation_url: str) -> Dict:
        """Fallback 이메일 템플릿"""
        return {
            "subject": f"[견적서] {quotation_number} - {client_name}님",
            "body": f"""{client_name}님 안녕하세요,

스마택트입니다.

요청하신 프로젝트에 대한 견적서를 보내드립니다.

아래 링크에서 견적서 내용을 확인하실 수 있습니다.
{quotation_url}

궁금한 점이 있으시면 언제든지 연락 주시기 바랍니다.
이메일: smatact@gmail.com
전화: 010-4782-3513

감사합니다.
"""
        }


# AI 사용 로그 저장
def log_ai_usage(db, request_type: str, prompt: str, response: str,
                tokens_used: int, cost: float, model: str):
    """AI 사용 로그를 데이터베이스에 저장"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_logs (request_type, prompt, response, tokens_used, cost, model)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (request_type, prompt[:5000], str(response)[:5000], tokens_used, cost, model))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"AI log error: {e}")
