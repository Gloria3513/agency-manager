"""
스마택트(Smartact) 에듀테크 교육 프로그램 견적 설문조사
고객이 교육 프로그램을 선택하고 자동으로 견적을 확인할 수 있는 페이지
"""

import streamlit as st
from datetime import datetime
from database import ClientDB, InquiryDB

# 페이지 설정
st.set_page_config(
    page_title="스마택트 교육 프로그램 견적",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS 스타일
st.markdown("""
    <style>
        .survey-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }

        .survey-header {
            text-align: center;
            padding: 50px 30px;
            background: linear-gradient(135deg, #4ADE80 0%, #059669 100%);
            border-radius: 20px;
            color: white;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(5, 150, 105, 0.2);
        }

        .survey-header h1 {
            margin: 0;
            font-size: 36px;
            font-weight: 700;
        }

        .survey-header p {
            margin: 15px 0 0 0;
            opacity: 0.95;
            font-size: 18px;
        }

        .stForm {
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 35px;
            background: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }

        .section-title {
            font-size: 20px;
            font-weight: 700;
            color: #1e293b;
            margin: 25px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 3px solid #059669;
        }

        .estimate-box {
            background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
            border: 2px solid #059669;
            border-radius: 16px;
            padding: 30px;
            margin: 20px 0;
        }

        .estimate-total {
            font-size: 36px;
            font-weight: 800;
            color: #059669;
            text-align: center;
            margin: 20px 0;
        }

        div[data-baseweb="select"] > div {
            background-color: white;
        }

        .stButton > button {
            width: 100%;
            margin-top: 15px;
            border-radius: 10px;
        }

        .program-card {
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            padding: 20px;
            margin: 10px 0;
            transition: all 0.3s;
        }

        .program-card:hover {
            border-color: #059669;
            box-shadow: 0 4px 15px rgba(5, 150, 105, 0.15);
        }

        .info-badge {
            display: inline-block;
            background: #059669;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 13px;
            margin: 3px;
        }
    </style>
""", unsafe_allow_html=True)


# ===== 헤더 =====

st.markdown("""
    <div class="survey-header">
        <h1>🎓 스마택트 교육 프로그램</h1>
        <p>미래를 여는 AI·코딩 교육, 맞춤형 견적을 확인하세요</p>
    </div>
""", unsafe_allow_html=True)


# ===== 진행 상태 바 =====

if "survey_step" not in st.session_state:
    st.session_state.survey_step = 1

steps = ["👤 신청자 정보", "📚 교육 프로그램 선택", "💵 견적 확인", "✅ 제출 완료"]
progress = (st.session_state.survey_step - 1) / (len(steps) - 1)

st.progress(progress)
st.markdown(f"<p style='text-align: center; color: #059669; font-weight: 600;'>{steps[st.session_state.survey_step - 1]}</p>",
           unsafe_allow_html=True)


# ===== DB 초기화 =====

client_db = ClientDB()
inquiry_db = InquiryDB()


# ===== 견적 계산 함수 =====

def calculate_estimate(program_type, target_audience, participants, sessions, include_kit=None):
    """
    스마택트 교육 프로그램 견적 계산

    강사료 기준 (시간당):
    - Type A (성인/전문가): 150,000원 (학부모 교육, 교사 연수)
    - Type B (학생 주강사-고급): 80,000원 (AI/SW 심화)
    - Type C (학생 주강사-일반): 40,000원 (기초 디지털 리터러시)
    - Type D (보조강사/튜터): 30,000원 (20명 초과 시 필수)

    교구 및 장비비:
    - 마이크로비트 장비셋: 100,000원 (1개 클래스/20명 기준)
    - 마이크로비트 시계 키트: 인당 10,000원 (소장용)
    - 큐트봇(AI자동차) 키트: 인당 15,000원 (소장용)
    - 워크북/활동지: 인당 5,000원
    """
    items = []
    total = 0

    # 프로그램 유형별 기본 설정
    program_configs = {
        "ai_cutebot": {
            "name": "🤖 AI 자율주동차 (큐트봇)",
            "description": "큐트봇을 활용한 AI 자율주행차 코딩 교육",
            "instructor_type": "B",
            "requires_equipment": True,
            "kit_type": "cutebot",
            "base_kit_price": 15000
        },
        "microbit_maker": {
            "name": "⌚ 마이크로비트 메이커",
            "description": "마이크로비트로 시계 및 각종 기 만들기",
            "instructor_type": "C",
            "requires_equipment": True,
            "kit_type": "microbit_watch",
            "base_kit_price": 10000
        },
        "coding_basic": {
            "name": "💻 엔트리/스크래치 코딩",
            "description": "블록 코딩 입문 및 기초",
            "instructor_type": "C",
            "requires_equipment": False,
            "kit_type": None,
            "base_kit_price": 0
        },
        "digital_literacy": {
            "name": "📱 디지털 리터러시",
            "description": "탭, 로노 등 공공 디지털 기초",
            "instructor_type": "C",
            "requires_equipment": False,
            "kit_type": None,
            "base_kit_price": 0
        },
        "parent_lecture": {
            "name": "👨‍👩‍👧 학부모 특강",
            "description": "우리 아이 AI·코딩 교육법",
            "instructor_type": "A",
            "requires_equipment": False,
            "kit_type": None,
            "base_kit_price": 0
        },
        "teacher_training": {
            "name": "👨‍🏫 교사 연수",
            "description": "교육 현장 활용 SW·AI 연수",
            "instructor_type": "A",
            "requires_equipment": False,
            "kit_type": None,
            "base_kit_price": 0
        }
    }

    config = program_configs.get(program_type, program_configs["coding_basic"])
    instructor_type = config["instructor_type"]

    # 강사료 단가
    instructor_prices = {
        "A": 150000,
        "B": 80000,
        "C": 40000,
        "D": 30000
    }

    instructor_price = instructor_prices[instructor_type]
    instructor_label = {
        "A": "전문 강사 (성인/전문가)",
        "B": "주강사 (고급)",
        "C": "주강사 (일반)",
        "D": "보조 강사"
    }[instructor_type]

    # 강사료 계산
    instructor_cost = instructor_price * sessions
    items.append({
        "category": "강사료",
        "name": f"{instructor_label} × {sessions}차시",
        "price": instructor_price,
        "quantity": sessions,
        "total": instructor_cost
    })
    total += instructor_cost

    # 보조강사 (20명 초과 시)
    assistant_cost = 0
    if target_audience in ["elementary", "middle", "high"] and participants > 20:
        assistant_sessions = sessions
        assistant_cost = instructor_prices["D"] * assistant_sessions
        items.append({
            "category": "강사료",
            "name": f"보조 강사 × {assistant_sessions}차시 (인원 {participants}명 초과로 추가)",
            "price": instructor_prices["D"],
            "quantity": assistant_sessions,
            "total": assistant_cost
        })
        total += assistant_cost

    # 장비비 (마이크로비트 장비셋)
    if config["requires_equipment"]:
        equipment_cost = 100000
        items.append({
            "category": "장비비",
            "name": "마이크로비트 장비셋 (대여)",
            "price": equipment_cost,
            "quantity": 1,
            "total": equipment_cost
        })
        total += equipment_cost

    # 키트비 (선택사항)
    kit_cost = 0
    if include_kit and config["kit_type"]:
        kit_price = config["base_kit_price"]
        kit_cost = kit_price * participants
        kit_name = {
            "cutebot": "큐트봇(AI자동차) 키트",
            "microbit_watch": "마이크로비트 시계 키트"
        }[config["kit_type"]]

        items.append({
            "category": "교구비",
            "name": f"{kit_name} (소장용) × {participants}명",
            "price": kit_price,
            "quantity": participants,
            "total": kit_cost
        })
        total += kit_cost

    # 워크북/활동지
    workbook_cost = 5000 * participants
    items.append({
        "category": "교구비",
        "name": f"워크북/활동지 × {participants}명",
        "price": 5000,
        "quantity": participants,
        "total": workbook_cost
    })
    total += workbook_cost

    return {
        "program_name": config["name"],
        "program_description": config["description"],
        "items": items,
        "total": total,
        "instructor_type": instructor_type,
        "participants": participants,
        "sessions": sessions
    }


# ===== 1단계: 신청자 정보 =====

if st.session_state.survey_step == 1:
    st.markdown('<div class="section-title">👤 신청자 정보</div>', unsafe_allow_html=True)

    with st.form("basic_info"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("신청자 이름 *", placeholder="홍길동")

        with col2:
            phone = st.text_input("연락처 *", placeholder="010-0000-0000")

        email = st.text_input("이메일 *", placeholder="example@email.com")

        col1, col2 = st.columns(2)
        with col1:
            organization_type = st.selectbox(
                "소속 기관 유형 *",
                ["school", "academy", "company", "community", "individual"],
                format_func=lambda x: {
                    "school": "🏫 학교 (유치장/초/중/고)",
                    "academy": "📚 학원/교육기관",
                    "company": "🏢 기업/공공기관",
                    "community": "👥 동호회/모임",
                    "individual": "👤 개인"
                }[x]
            )

        with col2:
            organization_name = st.text_input("기관명 (선택)", placeholder="OO초등학교")

        col1, col2 = st.columns(2)

        with col1:
            submit = st.form_submit_button("다음 →", type="primary")

        with col2:
            if st.form_submit_button("초기화"):
                for key in list(st.session_state.keys()):
                    if key.startswith('survey_'):
                        del st.session_state[key]
                st.rerun()

        if submit:
            if not name or not phone or not email:
                st.error("이름, 연락처, 이메일은 필수 항목입니다.")
            else:
                st.session_state.survey_data = {
                    'name': name,
                    'phone': phone,
                    'email': email,
                    'organization_type': organization_type,
                    'organization_name': organization_name
                }
                st.session_state.survey_step = 2
                st.rerun()


# ===== 2단계: 교육 프로그램 선택 =====

elif st.session_state.survey_step == 2:
    st.markdown('<div class="section-title">📚 교육 프로그램 선택</div>', unsafe_allow_html=True)

    with st.form("program_selection"):
        # 교육 대상
        target_audience = st.selectbox(
            "교육 대상 *",
            ["elementary", "middle", "high", "parent", "teacher", "adult"],
            format_func=lambda x: {
                "elementary": "👦👧 초등학생",
                "middle": "🧑‍🎓 중학생",
                "high": "👨‍🎓 고등학생",
                "parent": "👨‍👩‍👧 학부모",
                "teacher": "👨‍🏫 교사",
                "adult": "👨‍💼 일반 성인"
            }[x]
        )

        # 프로그램 유형 (대상에 따라 다르게 표시)
        st.markdown("### 프로그램 유형 선택")

        # 대상별 적합한 프로그램 필터링
        if target_audience in ["parent", "teacher", "adult"]:
            program_options = [
                "parent_lecture",
                "teacher_training",
                "digital_literacy"
            ]
        else:
            program_options = [
                "ai_cutebot",
                "microbit_maker",
                "coding_basic",
                "digital_literacy"
            ]

        program_type = st.selectbox(
            "교육 프로그램 *",
            program_options,
            format_func=lambda x: {
                "ai_cutebot": "🤖 **AI 자율주동차 (큐트봇)** - AI 자율주행차 코딩",
                "microbit_maker": "⌚ **마이크로비트 메이커** - 시계 및 기 만들기",
                "coding_basic": "💻 **엔트리/스크래치 코딩** - 블록 코딩 입문",
                "digital_literacy": "📱 **디지털 리터러시** - 공공 디지털 기초",
                "parent_lecture": "👨‍👩‍👧 **학부모 특강** - 우리 아이 AI·코딩 교육법",
                "teacher_training": "👨‍🏫 **교사 연수** - 교육 현장 활용 SW·AI"
            }[x]
        )

        # 프로그램 상세 설명
        program_descriptions = {
            "ai_cutebot": """
                <div style='background: #f0fdf4; padding: 15px; border-radius: 10px; border-left: 4px solid #059669;'>
                    <h4>🤖 AI 자율주동차 (큐트봇)</h4>
                    <p>• 큐트봇을 활용한 AI 자율주행차 원리 및 코딩</p>
                    <p>• 센서와 AI의 기초를 체험하고 배움</p>
                    <p>• 실습 키트 소장 가능 (별도)</p>
                </div>
            """,
            "microbit_maker": """
                <div style='background: #f0fdf4; padding: 15px; border-radius: 10px; border-left: 4px solid #059669;'>
                    <h4>⌚ 마이크로비트 메이커</h4>
                    <p>• 마이크로비트로 시계, 게임기 등 만들기</p>
                    <p>• 하드웨어와 소프트웨어의 융합 체험</p>
                    <p>• 완성 작품 키트로 소장 가능 (별도)</p>
                </div>
            """,
            "coding_basic": """
                <div style='background: #f0fdf4; padding: 15px; border-radius: 10px; border-left: 4px solid #059669;'>
                    <h4>💻 엔트리/스크래치 코딩</h4>
                    <p>• 블록 코딩으로 알고리즘 사고력 배양</p>
                    <p>• 게임 및 애니메이션 만들기 실습</p>
                    <p>• 코딩 입문자에게 최적</p>
                </div>
            """,
            "digital_literacy": """
                <div style='background: #f0fdf4; padding: 15px; border-radius: 10px; border-left: 4px solid #059669;'>
                    <h4>📱 디지털 리터러시</h4>
                    <p>• 탭, 로노 등 공공서비스 이용법</p>
                    <p>• 스마트폰 기초 활용 교육</p>
                    <p>• 모든 연령대 가능</p>
                </div>
            """,
            "parent_lecture": """
                <div style='background: #f0fdf4; padding: 15px; border-radius: 10px; border-left: 4px solid #059669;'>
                    <h4>👨‍👩‍👧 학부모 특강</h4>
                    <p>• 우리 아이 AI·코딩 교육 가이드</p>
                    <p>• 미래 교육 트렌드 소개</p>
                    <p>• 2시간 특강 형태</p>
                </div>
            """,
            "teacher_training": """
                <div style='background: #f0fdf4; padding: 15px; border-radius: 10px; border-left: 4px solid #059669;'>
                    <h4>👨‍🏫 교사 연수</h4>
                    <p>• SW·AI 교육 연수 및 커리큘럼 안내</p>
                    <p>• 현장 활용 팁 및 노하우 공유</p>
                    <p>• 맞춤형 연수 설계 가능</p>
                </div>
            """
        }

        st.markdown(program_descriptions[program_type], unsafe_allow_html=True)

        # 인원 및 차시
        col1, col2 = st.columns(2)

        with col1:
            participants = st.number_input(
                "참여 인원수 *",
                min_value=1,
                max_value=100,
                value=20,
                step=1
            )

        with col2:
            sessions = st.number_input(
                "교육 차시 *",
                min_value=1,
                max_value=20,
                value=2,
                step=1,
                help="1차시 = 50분 기준"
            )

        # 키트 포함 여부 (해당 프로그램만)
        include_kit = False
        if program_type in ["ai_cutebot", "microbit_maker"]:
            include_kit = st.checkbox(
                "🎁 키트 포함 (소장용)",
                value=False,
                help="수업 후 개인이 소장할 수 있는 키트를 포함합니다."
            )
            if include_kit:
                kit_price = 15000 if program_type == "ai_cutebot" else 10000
                st.info(f"💡 키트 비용: 인당 {kit_price:,}원 추가")

        # 희망 일정
        col1, col2 = st.columns(2)

        with col1:
            preferred_date = st.date_input("희망 교육일", value=None)

        with col2:
            urgency = st.selectbox(
                "희망 진행 속도",
                ["flexible", "normal", "fast", "urgent"],
                format_func=lambda x: {
                    "flexible": "📅 유동적",
                    "normal": "🐢 평소대로 (2주 이내)",
                    "fast": "🚕 빠르게 (1주 이내)",
                    "urgent": "🚒 긴급 (3일 이내)"
                }[x],
                index=0
            )

        # 추가 요청사항
        additional_info = st.text_area(
            "추가 요청사항 (선택)",
            placeholder="특별히 원하시는 내용이 있다면 적어주세요.\n예) 특정 주제 집중, 현장 여건 등",
            height=100
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.form_submit_button("← 이전"):
                st.session_state.survey_step = 1
                st.rerun()

        with col2:
            submit = st.form_submit_button("견적 계산하기 →", type="primary")

        if submit:
            if participants <= 0 or sessions <= 0:
                st.error("인원수와 차시는 1 이상이어야 합니다.")
            else:
                st.session_state.survey_data.update({
                    'target_audience': target_audience,
                    'program_type': program_type,
                    'participants': participants,
                    'sessions': sessions,
                    'include_kit': include_kit,
                    'preferred_date': preferred_date.isoformat() if preferred_date else None,
                    'urgency': urgency,
                    'additional_info': additional_info
                })

                # 견적 계산
                estimate = calculate_estimate(
                    program_type, target_audience, participants, sessions, include_kit
                )
                st.session_state.estimate = estimate
                st.session_state.survey_step = 3
                st.rerun()


# ===== 3단계: 견적 확인 =====

elif st.session_state.survey_step == 3:
    st.markdown('<div class="section-title">💵 견적 내역 확인</div>', unsafe_allow_html=True)

    estimate = st.session_state.estimate
    data = st.session_state.survey_data

    # 프로그램 요약
    st.markdown(f"""
        <div style='background: white; padding: 25px; border-radius: 16px; border: 2px solid #e2e8f0; margin-bottom: 25px;'>
            <h3 style='margin: 0 0 15px 0; color: #059669;'>{estimate['program_name']}</h3>
            <p style='color: #64748b; margin: 0;'>{estimate['program_description']}</p>
            <div style='margin-top: 15px;'>
                <span class='info-badge'>👥 {estimate['participants']}명</span>
                <span class='info-badge'>⏱️ {estimate['sessions']}차시</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 견적 상세
    st.markdown("### 📋 상세 견적 내역")

    for item in estimate['items']:
        st.markdown(f"""
            <div style='display: flex; justify-content: space-between; padding: 15px; border-bottom: 1px solid #e2e8f0;'>
                <div>
                    <div style='font-weight: 600;'>{item['name']}</div>
                    <div style='font-size: 13px; color: #64748b;'>{item['category']}</div>
                </div>
                <div style='text-align: right;'>
                    <div style='font-weight: 600;'>{item['price']:,}원 × {item['quantity']}</div>
                    <div style='color: #059669; font-weight: 700;'>{item['total']:,}원</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 총계
    st.markdown(f"""
        <div class='estimate-box'>
            <div style='text-align: center;'>
                <div style='font-size: 18px; color: #64748b; margin-bottom: 10px;'>총 견적 금액 (VAT 별도)</div>
                <div class='estimate-total'>{estimate['total']:,}원</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 추가 안내
    st.markdown("""
        <div style='background: #fffbeb; padding: 20px; border-radius: 12px; border-left: 4px solid #f59e0b; margin: 20px 0;'>
            <h4 style='margin: 0 0 10px 0;'>📌 안내 사항</h4>
            <ul style='margin: 0; padding-left: 20px; color: #92400e;'>
                <li>상 견적은 기준 단가에 따른 산출물로, 실제 계약 시 조정될 수 있습니다.</li>
                <li>20명 초과 시 보조 강사가 추가 배치됩니다.</li>
                <li>장비 대여료는 1개 클래스(20명 기준)입니다.</li>
                <li>지방 및 도서 지역의 경우 여비가 별도 발생할 수 있습니다.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("← 이전"):
            st.session_state.survey_step = 2
            st.rerun()

    with col2:
        if st.button("수정하기", type="secondary"):
            st.session_state.survey_step = 2
            st.rerun()

    with col3:
        if st.button("제출하기", type="primary", width='stretch'):
            st.session_state.survey_step = 4
            st.rerun()


# ===== 4단계: 제출 완료 =====

elif st.session_state.survey_step == 4:
    survey_data = st.session_state.survey_data
    estimate = st.session_state.estimate

    try:
        # 고객 정보 저장
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
                company=survey_data.get('organization_name'),
                source='survey'
            )

        # 상세 설명 생성
        target_labels = {
            "elementary": "초등학생",
            "middle": "중학생",
            "high": "고등학생",
            "parent": "학부모",
            "teacher": "교사",
            "adult": "성인"
        }

        description = f"""
[교육 프로그램 견적 요청]

프로그램: {estimate['program_name']}
대상: {target_labels[survey_data['target_audience']]} ({survey_data['participants']}명)
차시: {survey_data['sessions']}차시
예상 견적: {estimate['total']:,}원 (VAT 별도)

키트 포함: {'예' if survey_data.get('include_kit') else '아니오'}
희망 일자: {survey_data.get('preferred_date', '미정')}
긴급도: {survey_data.get('urgency', 'flexible')}
""".strip()

        if survey_data.get('organization_name'):
            description = f"소속: {survey_data['organization_name']}\n\n{description}"

        if survey_data.get('additional_info'):
            description += f"\n\n추가 요청사항:\n{survey_data['additional_info']}"

        # 견적 내역 추가
        description += "\n\n[상세 견적 내역]\n"
        for item in estimate['items']:
            description += f"- {item['name']}: {item['price']:,}원 × {item['quantity']} = {item['total']:,}원\n"
        description += f"\n총계: {estimate['total']:,}원"

        # 문의 저장
        inquiry_id = inquiry_db.add_inquiry(
            client_id=client_id,
            project_type=survey_data['program_type'],
            budget=str(estimate['total']),
            duration=str(survey_data['sessions']) + "차시",
            description=description,
            urgency=survey_data.get('urgency', 'flexible')
        )

        # 성공 메시지
        st.markdown(f"""
            <div style='text-align: center; padding: 60px 30px;'>
                <div style='font-size: 80px;'>✅</div>
                <h2 style='color: #059669; margin: 20px 0;'>견적 요청이 접수되었습니다!</h2>
                <p style='color: #64748b; font-size: 17px;'>
                    담당자가 **영업일 1일 이내**에 연락드리겠습니다.<br>
                    감사합니다.
                </p>
            </div>

            <div class='estimate-box'>
                <div style='text-align: center;'>
                    <div style='font-size: 16px; color: #64748b;'>예상 견적 금액</div>
                    <div style='font-size: 42px; font-weight: 800; color: #059669; margin: 15px 0;'>{estimate['total']:,}원</div>
                    <div style='font-size: 14px; color: #64748b;'>VAT 별도</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # 접수 내역 확인
        with st.expander("📋 접수 내역 확인", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**👤 신청자 정보**")
                st.markdown(f"- 이름: {survey_data['name']}")
                st.markdown(f"- 연락처: {survey_data['phone']}")
                st.markdown(f"- 이메일: {survey_data['email']}")
                if survey_data.get('organization_name'):
                    st.markdown(f"- 소속: {survey_data['organization_name']}")

            with col2:
                st.markdown("**📚 교육 프로그램**")
                st.markdown(f"- 프로그램: {estimate['program_name']}")
                st.markdown(f"- 대상: {target_labels[survey_data['target_audience']]}")
                st.markdown(f"- 인원: {survey_data['participants']}명")
                st.markdown(f"- 차시: {survey_data['sessions']}차시")

            st.markdown("**💵 상세 견적**")
            for item in estimate['items']:
                st.markdown(f"- {item['name']}: **{item['total']:,}원**")
            st.markdown(f"---\n**총계: {estimate['total']:,}원** (VAT 별도)")

        # 새 의뢰 버튼
        if st.button("📝 새 견적 요청하기", type="primary", width='stretch'):
            for key in list(st.session_state.keys()):
                if key.startswith('survey_') or key == 'estimate':
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
        <p style='font-weight: 600; color: #059669;'>🎓 스마택트 (Smartact)</p>
        <p style='font-size: 13px; margin-top: 10px;'>
            미래를 여는 AI·코딩 교육의 파트너
        </p>
        <p style='font-size: 12px; margin-top: 15px;'>
            문의: contact@smartact.com | 전화: 02-1234-5678
        </p>
    </div>
""", unsafe_allow_html=True)
