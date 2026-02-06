"""
공개 프로젝트 의뢰 설문조사 페이지
고객이 접속하여 프로젝트 의뢰를 작성할 수 있는 별도 Streamlit 페이지
"""

import streamlit as st
from datetime import datetime
from database import ClientDB, InquiryDB

# 페이지 설정
st.set_page_config(
    page_title="프로젝트 의뢰",
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS 스타일
st.markdown("""
    <style>
        .survey-container {
            max-width: 700px;
            margin: 0 auto;
            padding: 20px;
        }

        .survey-header {
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            color: white;
            margin-bottom: 30px;
        }

        .survey-header h1 {
            margin: 0;
            font-size: 32px;
        }

        .survey-header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
        }

        .stForm {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 30px;
            background: white;
        }

        .section-title {
            font-size: 18px;
            font-weight: 600;
            color: #1e293b;
            margin: 20px 0 10px 0;
            padding-bottom: 8px;
            border-bottom: 2px solid #667eea;
        }

        div[data-baseweb="select"] > div {
            background-color: white;
        }

        .stButton > button {
            width: 100%;
            margin-top: 20px;
        }
    </style>
""", unsafe_allow_html=True)


# ===== 헤더 =====

st.markdown("""
    <div class="survey-header">
        <h1>🚀 프로젝트 의뢰</h1>
        <p>여러분의 프로젝트를 함께 만들어 가겠습니다</p>
    </div>
""", unsafe_allow_html=True)


# ===== 진행 상태 바 =====

if "survey_step" not in st.session_state:
    st.session_state.survey_step = 1

steps = ["기본 정보", "프로젝트 상세", "예산 및 일정", "완료"]
progress = (st.session_state.survey_step - 1) / (len(steps) - 1) * 100

st.progress(progress / 100)
st.markdown(f"<p style='text-align: center; color: #64748b;'>{steps[st.session_state.survey_step - 1]}</p>",
           unsafe_allow_html=True)


# ===== DB 초기화 =====

client_db = ClientDB()
inquiry_db = InquiryDB()


# ===== 1단계: 기본 정보 =====

if st.session_state.survey_step == 1:
    st.markdown('<div class="section-title">👤 담당자 정보</div>', unsafe_allow_html=True)

    with st.form("basic_info"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("이름 *", placeholder="홍길동")

        with col2:
            phone = st.text_input("연락처 *", placeholder="010-0000-0000")

        email = st.text_input("이메일 *", placeholder="example@email.com")
        company = st.text_input("회사명 (선택)", placeholder="(주)회사명")

        col1, col2 = st.columns(2)

        with col1:
            submit = st.form_submit_button("다음 →", type="primary")

        with col2:
            if st.form_submit_button("초기화"):
                st.rerun()

        if submit:
            if not name or not phone or not email:
                st.error("이름, 연락처, 이메일은 필수 항목입니다.")
            else:
                st.session_state.survey_data = {
                    'name': name,
                    'phone': phone,
                    'email': email,
                    'company': company
                }
                st.session_state.survey_step = 2
                st.rerun()


# ===== 2단계: 프로젝트 상세 =====

elif st.session_state.survey_step == 2:
    st.markdown('<div class="section-title">💡 프로젝트 정보</div>', unsafe_allow_html=True)

    with st.form("project_info"):
        project_type = st.selectbox(
            "프로젝트 유형 *",
            ["website", "landing", "web_app", "mobile_app", "maintenance", "consulting", "other"],
            format_func=lambda x: {
                "website": "🌐 웹사이트 제작",
                "landing": "📄 랜딩페이지",
                "web_app": "💻 웹 애플리케이션",
                "mobile_app": "📱 모바일 앱",
                "maintenance": "🔧 유지보수",
                "consulting": "💡 기술 컨설팅",
                "other": "📦 기타"
            }[x]
        )

        urgency = st.selectbox(
            "희망 진행 속도",
            ["normal", "fast", "urgent"],
            format_func=lambda x: {
                "normal": "🐢 평소대로 (4-6주)",
                "fast": "🚕 빠르게 (2-4주)",
                "urgent": "🚒 긴급 (1-2주)"
            }[x],
            index=0
        )

        description = st.text_area(
            "프로젝트 설명 *",
            placeholder="만들고자 하는 서비스에 대해 자유롭게 설명해주세요.\n\n예시) \n- 홈페이지 리뉴얼\n- 상품 관리 기능이 필요한 쇼핑몰\n- 회원가입/로그인 시스템",
            height=200
        )

        reference = st.text_input(
            "참고 사이트 (선택)",
            placeholder="https://example.com"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.form_submit_button("← 이전"):
                st.session_state.survey_step = 1
                st.rerun()

        with col2:
            submit = st.form_submit_button("다음 →", type="primary")

        if submit:
            if not description:
                st.error("프로젝트 설명을 입력해주세요.")
            else:
                st.session_state.survey_data.update({
                    'project_type': project_type,
                    'urgency': urgency,
                    'description': description,
                    'reference': reference
                })
                st.session_state.survey_step = 3
                st.rerun()


# ===== 3단계: 예산 및 일정 =====

elif st.session_state.survey_step == 3:
    st.markdown('<div class="section-title">💰 예산 및 일정</div>', unsafe_allow_html=True)

    with st.form("budget_schedule"):
        budget = st.selectbox(
            "예상 예산",
            ["under_500", "500_1000", "1000_3000", "3000_5000", "over_5000"],
            format_func=lambda x: {
                "under_500": "500만원 미만",
                "500_1000": "500만원 ~ 1,000만원",
                "1000_3000": "1,000만원 ~ 3,000만원",
                "3000_5000": "3,000만원 ~ 5,000만원",
                "over_5000": "5,000만원 이상"
            }[x],
            index=2
        )

        duration = st.selectbox(
            "희망 완료일",
            ["1month", "2month", "3month", "ongoing"],
            format_func=lambda x: {
                "1month": "1개월 이내",
                "2month": "2개월 이내",
                "3month": "3개월 이내",
                "ongoing": "협의 가능"
            }[x],
            index=2
        )

        start_date = st.date_input("희망 시작일", value=None)

        additional_info = st.text_area(
            "추가 요청사항 (선택)",
            placeholder="특별히 요청하시는 기능이나 조건이 있다면 적어주세요.",
            height=100
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.form_submit_button("← 이전"):
                st.session_state.survey_step = 2
                st.rerun()

        with col2:
            submit = st.form_submit_button("제출하기", type="primary")

        if submit:
            st.session_state.survey_data.update({
                'budget': budget,
                'duration': duration,
                'start_date': start_date.isoformat() if start_date else None,
                'additional_info': additional_info
            })
            st.session_state.survey_step = 4
            st.rerun()


# ===== 4단계: 완료 =====

elif st.session_state.survey_step == 4:
    # 데이터 저장
    survey_data = st.session_state.survey_data

    try:
        # 고객 정보 저장 (중복 체크)
        all_clients = client_db.get_all_clients()
        existing_client = next(
            (c for c in all_clients if c['email'] == survey_data['email']),
            None
        )

        if existing_client:
            client_id = existing_client['id']
        else:
            client_id = client_db.add_client(
                name=survey_data['name'],
                email=survey_data['email'],
                phone=survey_data['phone'],
                company=survey_data.get('company'),
                source='survey'
            )

        # 문의 저장
        full_description = survey_data['description']
        if survey_data.get('reference'):
            full_description += f"\n\n참고 사이트: {survey_data['reference']}"
        if survey_data.get('additional_info'):
            full_description += f"\n\n추가 요청사항:\n{survey_data['additional_info']}"

        inquiry_id = inquiry_db.add_inquiry(
            client_id=client_id,
            project_type=survey_data['project_type'],
            budget=survey_data['budget'],
            duration=survey_data['duration'],
            description=full_description,
            urgency=survey_data.get('urgency', 'normal')
        )

        # 성공 메시지
        st.markdown("""
            <div style='text-align: center; padding: 60px 20px;'>
                <div style='font-size: 64px;'>✅</div>
                <h2 style='color: #10b981; margin: 20px 0;'>의뢰가 접수되었습니다!</h2>
                <p style='color: #64748b; font-size: 16px;'>
                    빠른 시일 내에 담당자가 연락드리겠습니다.<br>
                    감사합니다.
                </p>
            </div>
        """, unsafe_allow_html=True)

        # 요약 정보
        with st.expander("📋 접수 내역 확인", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**담당자 정보**")
                st.markdown(f"- 이름: {survey_data['name']}")
                st.markdown(f"- 연락처: {survey_data['phone']}")
                st.markdown(f"- 이메일: {survey_data['email']}")
                if survey_data.get('company'):
                    st.markdown(f"- 회사: {survey_data['company']}")

            with col2:
                st.markdown("**프로젝트 정보**")
                type_labels = {
                    "website": "웹사이트",
                    "landing": "랜딩페이지",
                    "web_app": "웹 앱",
                    "mobile_app": "모바일 앱",
                    "maintenance": "유지보수",
                    "consulting": "컨설팅",
                    "other": "기타"
                }
                st.markdown(f"- 프로젝트: {type_labels.get(survey_data['project_type'], survey_data['project_type'])}")
                st.markdown(f"- 예산: {survey_data['budget']}")
                st.markdown(f"- 일정: {survey_data['duration']}")

            st.markdown("**설명**")
            st.text(survey_data['description'][:200] + "..." if len(survey_data['description']) > 200 else survey_data['description'])

        # 새 의뢰 버튼
        if st.button("📝 새 의뢰 작성하기", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key.startswith('survey_'):
                    del st.session_state[key]
            st.rerun()

    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
        if st.button("다시 시도"):
            st.session_state.survey_step = 1
            st.rerun()


# ===== 푸터 =====

st.markdown("""
    <div style='text-align: center; padding: 40px 20px; color: #94a3b8; font-size: 14px;'>
        <p>🚀 에이전시 관리 시스템</p>
        <p style='font-size: 12px; margin-top: 10px;'>
            문의: contact@agency.com | 전화: 02-1234-5678
        </p>
    </div>
""", unsafe_allow_html=True)
