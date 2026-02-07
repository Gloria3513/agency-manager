# Agency Manager - Claude 작업 가이드

## 프로젝트 개요
1인 에이전시 운영자를 위한 올인원 관리 시스템입니다.

## 기술 스택
- **프레임워크**: Streamlit (Python)
- **데이터베이스**: SQLite
- **AI**: Gemini API (견적서 자동 생성)
- **PDF**: ReportLab (한글 폰트: AppleGothic)

## 📁 주요 파일

| 파일 | 설명 |
|------|------|
| `app.py` | 메인 앱 (관리자 대시보드) |
| `portal.py` | 고객 포털 |
| `survey.py` | 공개 설문조사 |
| `database.py` | DB 모델 (19개 테이블) |
| `utils/pdf_generator.py` | PDF 생성 |
| `utils/email_sender.py` | 이메일 발송 |
| `utils/ai_generator.py` | AI 견적 생성 |

## ⚠️ 중요 주의사항 (버그 수정 내역)

### PDF 다운로드 관련
**문제**: `st.button()` 콜백 내부에 `st.download_button()`을 넣으면 다운로드가 작동하지 않음
**해결**: PDF를 미리 생성해서 `data` 파라미터에 직접 전달

```python
# ❌ 잘못된 방법
if st.button("PDF 생성"):
    pdf_data = generate_pdf()
    st.download_button(data=pdf_data, ...)  # 작동 안 함

# ✅ 올바른 방법
pdf_data = generate_pdf()  # 미리 생성
st.download_button(data=pdf_data, ...)
```

### 한글 폰트 관련
**문제**: `Korean-Bold` 폰트가 등록되지 않아 오류 발생
**해결**: `Korean` 폰트만 사용

```python
# utils/pdf_generator.py
self.font_registered = False  # __init__에서 초기화 필수
# Korean-Bold 사용 ❌, Korean만 사용 ✅
```

### 세션 상태 관련
- `st.session_state.selected_quotation_id`: 견적서 자동 선택
- `st.session_state.preview_quotation`: 견적서 미리보기 데이터

## 🚀 실행 방법

```bash
# 메인 앱
streamlit run app.py --server.port 8501

# 설문조사
streamlit run survey.py --server.port 8505
```

## 📋 구현된 기능 (2026-02-07 기준)

### ✅ 완료
- 고객 관리 (CRM)
- 스프레드시트 일괄 등록 (CSV/엑셀)
- AI 견적서 자동 생성 (Gemini API)
- 견적서 미리보기
- PDF 다운로드 (한글 지원)
- 이메일 발송 (SMTP)
- 전자 계약서
- 전자 서명
- 프로젝트 관리 (칸반 보드)
- 캘린더 동기화

### 🔄 다음에 할 것
- [ ] 입금 관리 강화
- [ ] 대시보드/리포트 개선
- [ ] Slack 알림 연동
- [ ] 결제대시보드(PG) 연동

## 🎨 사용자 선호 스타일
- ✨ 기능 추가 후 바로 테스트
- 📸 스크린샷으로 오류 공유
- 🚀 빠르게 반복 개발 선호

## 📞 연락처
- 이메일: smatact@gmail.com
- 전화: 010-4782-3513
