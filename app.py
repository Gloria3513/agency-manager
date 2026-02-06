"""
올인원 에이전시 관리 시스템
Streamlit 기반 관리자 대시보드
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os

# 데이터베이스 모델 임포트
from database import (
    ClientDB, InquiryDB, QuotationDB, ProjectDB, TaskDB, SettingsDB,
    CalendarDB, TimeEntryDB, TimeSessionDB, FileDB, NotificationDB,
    UserDB, TeamDB, RoleDB, ActivityLogDB, CommentDB
)

# 유틸리티 임포트
from utils import (
    AIQuotationGenerator, PDFQuotationGenerator, EmailSender,
    ContractGenerator, SignatureVerifier
)
from utils.calendar_manager import CalendarManager
from utils.ical_generator import ICalGenerator, generate_ical_from_events
from utils.auth_manager import AuthManager, SessionManager, PermissionChecker, init_admin_user
from utils.activity_logger import ActivityLogger, get_logger
import time
import secrets

# 페이지 설정
st.set_page_config(
    page_title="에이전시 관리 시스템",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 로드
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "static", "css", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# 로그인 상태 초기화 (먼저 해야 함)
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user" not in st.session_state:
    st.session_state.user = None

if "current_page" not in st.session_state:
    st.session_state.current_page = "login"

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# 세션 상태 초기화
if "db" not in st.session_state:
    st.session_state.db = {
        "client": ClientDB(),
        "inquiry": InquiryDB(),
        "quotation": QuotationDB(),
        "project": ProjectDB(),
        "task": TaskDB(),
        "settings": SettingsDB(),
        "calendar": CalendarDB(),
        "time_entry": TimeEntryDB(),
        "time_session": TimeSessionDB(),
        "file": FileDB(),
        "notification": NotificationDB(),
        "user": UserDB(),
        "team": TeamDB(),
        "role": RoleDB(),
        "activity": ActivityLogDB(),
        "comment": CommentDB()
    }

# 기본 관리자 계정 초기화 (직접 구현)
def init_default_admin():
    """기본 관리자 계정 생성"""
    user_db = st.session_state.db["user"]

    try:
        # 이미 존재하는지 확인
        existing = user_db.get_user_by_email("admin@agency.com")
        if existing:
            return existing['id']

        # 관리자 계정 생성
        import hashlib
        password_hash = hashlib.sha256("admin1234".encode()).hexdigest()

        conn = user_db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (email, name, password_hash, role, is_active)
            VALUES (?, ?, ?, 'admin', 1)
        """, ("admin@agency.com", "관리자", password_hash))
        admin_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return admin_id
    except Exception as e:
        print(f"Admin init error: {e}")
        return None

# 기본 관리자 생성
try:
    init_default_admin()
except:
    pass

# 인증 관리자 (지연 로딩)
auth_manager = None
session_manager = None
activity_logger = None

try:
    from utils.auth_manager import AuthManager, SessionManager
    from utils.activity_logger import ActivityLogger
    auth_manager = AuthManager()
    session_manager = SessionManager()
    activity_logger = ActivityLogger()
except Exception as e:
    print(f"Auth manager init error: {e}")

if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False


# ===== 유틸리티 함수 =====

def format_currency(amount):
    """금액 포맷팅"""
    if amount >= 10000:
        return f"{amount/10000:.1f}만원"
    return f"{amount:,}원"


def format_date(date_str):
    """날짜 포맷팅"""
    if date_str:
        try:
            dt = datetime.fromisoformat(str(date_str).replace("T", " "))
            return dt.strftime("%Y.%m.%d")
        except:
            return str(date_str)
    return "-"


def get_status_badge(status):
    """상태 배지 HTML"""
    badges = {
        "new": '<span class="badge badge-info">신규</span>',
        "contacted": '<span class="badge badge-warning">연락중</span>',
        "quoted": '<span class="badge badge-neutral">견적발송</span>',
        "converted": '<span class="badge badge-success">계약완료</span>',
        "lost": '<span class="badge badge-danger">계약실패</span>',
        "draft": '<span class="badge badge-neutral">초안</span>',
        "sent": '<span class="badge badge-info">발송</span>',
        "approved": '<span class="badge badge-success">승인</span>',
        "rejected": '<span class="badge badge-danger">거절</span>',
        "pending": '<span class="badge badge-warning">대기</span>',
        "signed": '<span class="badge badge-success">서명완료</span>',
        "todo": '<span class="badge badge-neutral">할일</span>',
        "in_progress": '<span class="badge badge-info">진행중</span>',
        "done": '<span class="badge badge-success">완료</span>',
        "planning": '<span class="badge badge-info">기획</span>',
        "active": '<span class="badge badge-warning">진행중</span>',
        "completed": '<span class="badge badge-success">완료</span>',
        "on_hold": '<span class="badge badge-danger">보류</span>',
    }
    return badges.get(status, f'<span class="badge badge-neutral">{status}</span>')


def show_metric_card(title, value, subtitle="", color="blue"):
    """메트릭 카드 표시"""
    colors = {
        "blue": "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)",
        "green": "linear-gradient(135deg, #10b981 0%, #059669 100%)",
        "purple": "linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)",
        "orange": "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)",
        "red": "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
    }

    st.markdown(f"""
        <div style="background: {colors[color]}; border-radius: 16px; padding: 20px; color: white;">
            <div style="font-size: 14px; opacity: 0.9;">{title}</div>
            <div style="font-size: 32px; font-weight: 700; margin: 8px 0;">{value}</div>
            <div style="font-size: 12px; opacity: 0.8;">{subtitle}</div>
        </div>
    """, unsafe_allow_html=True)


# ===== 사이드바 =====

def render_sidebar():
    """사이드바 렌더링"""
    with st.sidebar:
        st.markdown("""
            <div style="text-align: center; padding: 20px 0;">
                <h1 style="font-size: 24px; margin: 0;">🚀 에이전시 관리</h1>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # 다크 모드 토글
        dark_mode = st.checkbox("🌙 다크 모드", value=st.session_state.dark_mode)
        st.session_state.dark_mode = dark_mode

        if dark_mode:
            st.markdown("""
                <style>
                    .stApp { background-color: #0f172a; }
                    .main { background-color: #0f172a; }
                    blockquote { background-color: #1e293b; color: #e2e8f0; }
                </style>
            """, unsafe_allow_html=True)

        # 로그인 상태에 따른 UI
        if not st.session_state.authenticated:
            st.info("로그인이 필요합니다.")
        else:
            # 사용자 정보
            user = st.session_state.user
            if user:
                role_labels = {
                    'admin': '관리자',
                    'manager': '매니저',
                    'member': '팀원',
                    'viewer': '게스트'
                }
                role_badge_colors = {
                    'admin': 'badge-danger',
                    'manager': 'badge-warning',
                    'member': 'badge-info',
                    'viewer': 'badge-neutral'
                }

                role = user.get('role', 'member')
                role_badge_color = role_badge_colors.get(role, 'badge-neutral')
                role_label = role_labels.get(role, '팀원')

                st.markdown(f"""
                    <div style="background: #f8fafc; padding: 15px; border-radius: 12px; margin-bottom: 15px;">
                        <div style="font-weight: 600;">👤 {user.get('name', '사용자')}</div>
                        <div style="font-size: 12px; color: #64748b;">{user.get('email', '')}</div>
                        <div style="margin-top: 5px;">
                            <span class="badge {role_badge_color}">{role_label}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # 네비게이션 메뉴
        st.markdown("### 📁 메뉴")

        # 로그인되지 않은 경우에는 기본 메뉴만
        if not st.session_state.authenticated:
            basic_menus = {
                "login": "🔐 로그인"
            }
            for key, label in basic_menus.items():
                if st.button(label, key=f"nav_{key}", width='stretch'):
                    st.session_state.current_page = key
                    st.rerun()
        else:
            # 로그인된 경우 권한별 메뉴
            user_role = st.session_state.user.get('role', 'member') if st.session_state.user else 'member'

            try:
                accessible_menus = PermissionChecker.get_accessible_menus(user_role)
            except:
                accessible_menus = ["dashboard", "calendar", "time_tracker", "files"]

            menu_items = {
                "dashboard": "📊 대시보드",
                "clients": "👥 고객 관리",
                "inquiries": "📝 문의 관리",
                "quotations": "💰 견적 관리",
                "contracts": "📄 계약 관리",
                "projects": "🚧 프로젝트 관리",
                "tasks": "✅ 태스크",
                "payments": "💳 정산 관리",
                "calendar": "📅 캘린더",
                "time_tracker": "⏱️ 시간 추적",
                "files": "📁 파일 관리",
                "reports": "📊 리포트",
                "users": "👥 팀원 관리",
                "activity": "📜 활동 로그",
                "settings": "⚙️ 설정",
            }

            for key, label in menu_items.items():
                if key in accessible_menus:
                    if st.button(label, key=f"nav_{key}", width='stretch',
                                icon=None, disabled=st.session_state.current_page == key):
                        st.session_state.current_page = key
                        st.rerun()

        st.markdown("---")

        # 로그아웃 버튼 (로그인된 경우)
        if st.session_state.authenticated and st.button("🚪 로그아웃", width='stretch'):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.current_page = "login"
            st.rerun()

        st.markdown("---")

        # 공개 설문 링크
        st.markdown("### 🔗 공유 링크")
        st.code("http://localhost:8503/survey", language="text")

        st.markdown("---")
        st.markdown(f"""
            <div style="text-align: center; font-size: 12px; opacity: 0.6;">
                버전 2.0.0
            </div>
        """, unsafe_allow_html=True)


# ===== 대시보드 페이지 =====

def render_dashboard():
    """대시보드 페이지"""
    st.markdown("## 📊 대시보드")

    # 데이터 로드
    clients = st.session_state.db["client"].get_all_clients()
    inquiries = st.session_state.db["inquiry"].get_all_inquiries()
    quotations = st.session_state.db["quotation"].get_all_quotations()
    projects = st.session_state.db["project"].get_all_projects()

    # 메트릭 계산
    new_clients = sum(1 for c in clients if c["status"] == "lead")
    active_projects = sum(1 for p in projects if p["status"] in ["planning", "active"])
    pending_quotations = sum(1 for q in quotations if q["status"] == "sent")

    # 총 매출 계산 (계약된 프로젝트)
    total_revenue = sum(p["total_contract_amount"] or 0 for p in projects if p["status"] != "lost")

    # 메트릭 카드
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        show_metric_card("신규 고객", new_clients, f"총 {len(clients)}명", "blue")
    with col2:
        show_metric_card("진행 프로젝트", active_projects, f"총 {len(projects)}개", "green")
    with col3:
        show_metric_card("견적 대기", pending_quotations, f"총 {len(quotations)}건", "orange")
    with col4:
        show_metric_card("총 매출", format_currency(int(total_revenue)), "누적 기준", "purple")

    st.markdown("")

    # 차트 영역
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📈 월별 매출 추이")
        # 월별 매출 데이터 생성
        monthly_data = {}
        for project in projects:
            if project["created_at"]:
                month = project["created_at"][:7]  # YYYY-MM
                amount = project["total_contract_amount"] or 0
                monthly_data[month] = monthly_data.get(month, 0) + amount

        if monthly_data:
            df_monthly = pd.DataFrame([
                {"월": k, "매출": v}
                for k, v in sorted(monthly_data.items())
            ])
            fig = px.bar(df_monthly, x="월", y="매출",
                        color_discrete_sequence=["#3b82f6"])
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("데이터가 없습니다.")

    with col2:
        st.markdown("### 📊 프로젝트 상태 분포")
        project_statuses = {}
        for p in projects:
            status = p["status"]
            project_statuses[status] = project_statuses.get(status, 0) + 1

        if project_statuses:
            status_labels = {
                "planning": "기획중",
                "active": "진행중",
                "completed": "완료",
                "on_hold": "보류",
                "lost": "계약실패"
            }
            df_status = pd.DataFrame([
                {"상태": status_labels.get(k, k), "수": v}
                for k, v in project_statuses.items()
            ])
            colors = ["#3b82f6", "#f59e0b", "#10b981", "#ef4444", "#64748b"]
            fig = px.pie(df_status, values="수", names="상태",
                        color_discrete_sequence=colors)
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("데이터가 없습니다.")

    st.markdown("")

    # 최근 활동
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📝 최근 문의")
        if inquiries:
            df_inquiries = pd.DataFrame(inquiries[:5])
            df_inquiries_display = df_inquiries[["client_name", "project_type", "created_at"]] if "client_name" in df_inquiries.columns else df_inquiries
            st.dataframe(df_inquiries_display, width='stretch', hide_index=True)
        else:
            st.info("등록된 문의가 없습니다.")

    with col2:
        st.markdown("### 🚧 진행 중인 프로젝트")
        active = [p for p in projects if p["status"] in ["planning", "active"]]
        if active:
            df_active = pd.DataFrame(active[:5])
            df_display = df_active[["name", "progress", "status"]] if "name" in df_active.columns else df_active
            st.dataframe(df_display, width='stretch', hide_index=True)
        else:
            st.info("진행 중인 프로젝트가 없습니다.")


# ===== 고객 관리 페이지 =====

def render_clients():
    """고객 관리 페이지"""
    st.markdown("## 👥 고객 관리")

    # 고객 추가/편집 모드
    with st.expander("➕ 새 고객 추가", expanded=False):
        with st.form("add_client_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("이름 *", key="client_name")
                email = st.text_input("이메일 *", key="client_email")
            with col2:
                phone = st.text_input("연락처", key="client_phone")
                company = st.text_input("회사명", key="client_company")

            notes = st.text_area("메모", key="client_notes")
            source = st.selectbox("유입 경로", ["direct", "survey", "referral", "sns"],
                               format_func=lambda x: {"direct": "직접", "survey": "설문", "referral": "소개", "sns": "SNS"}[x])

            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("고객 추가", width='stretch')
            with col2:
                st.write("")

            if submit and name and email:
                client_id = st.session_state.db["client"].add_client(
                    name=name, email=email, phone=phone, company=company,
                    source=source, notes=notes
                )
                st.success(f"고객이 추가되었습니다. (ID: {client_id})")
                st.rerun()

    # 고객 목록
    st.markdown("### 고객 목록")

    clients = st.session_state.db["client"].get_all_clients()

    if clients:
        # 검색/필터
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search = st.text_input("🔍 검색", placeholder="이름, 이메일, 회사명...")
        with col2:
            status_filter = st.selectbox("상태 필터", ["all", "lead", "contacted", "quoted", "converted", "lost"],
                                       format_func=lambda x: {"all": "전체", "lead": "리드", "contacted": "연락중",
                                                             "quoted": "견적발송", "converted": "계약완료", "lost": "계약실패"}[x])
        with col3:
            st.write("")

        # 필터링
        filtered_clients = clients
        if search:
            filtered_clients = [c for c in filtered_clients
                              if search.lower() in c["name"].lower()
                              or search.lower() in c.get("email", "").lower()
                              or search.lower() in c.get("company", "").lower()]
        if status_filter != "all":
            filtered_clients = [c for c in filtered_clients if c["status"] == status_filter]

        # 테이블 표시
        df_clients = pd.DataFrame(filtered_clients)
        display_df = df_clients[["id", "name", "email", "phone", "company", "status", "created_at"]]

        # 상태 배지 적용
        for idx, row in display_df.iterrows():
            display_df.at[idx, "status"] = get_status_badge(row["status"])

        st.dataframe(display_df, width='stretch', hide_index=True)

        # 선택된 고객 상세 보기
        st.markdown("### 고객 상세")
        client_ids = [c["id"] for c in filtered_clients]
        if client_ids:
            selected_id = st.selectbox("고객 선택", [""] + client_ids,
                                     format_func=lambda x: "선택하세요" if x == "" else f"{x}번 고객")

            if selected_id:
                client = st.session_state.db["client"].get_client(selected_id)
                if client:
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown("#### 기본 정보")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown(f"**이름:** {client['name']}")
                            st.markdown(f"**이메일:** {client['email']}")
                        with c2:
                            st.markdown(f"**연락처:** {client.get('phone', '-')}")
                            st.markdown(f"**회사:** {client.get('company', '-')}")

                        st.markdown(f"**메모:** {client.get('notes', '-')}")

                    with col2:
                        st.markdown("#### 상태 변경")
                        new_status = st.selectbox("고객 상태",
                                                ["lead", "contacted", "quoted", "converted", "lost"],
                                                index=["lead", "contacted", "quoted", "converted", "lost"].index(client["status"]),
                                                format_func=lambda x: {"lead": "리드", "contacted": "연락중",
                                                                     "quoted": "견적발송", "converted": "계약완료", "lost": "계약실패"}[x])

                        if st.button("상태 업데이트", width='stretch'):
                            st.session_state.db["client"].update_client(selected_id, status=new_status)
                            st.success("상태가 업데이트되었습니다.")
                            st.rerun()

                        if st.button("고객 삭제", width='stretch', type="primary"):
                            st.session_state.db["client"].delete_client(selected_id)
                            st.success("고객이 삭제되었습니다.")
                            st.rerun()

    else:
        st.info("등록된 고객이 없습니다. 새 고객을 추가해주세요.")


# ===== 문의 관리 페이지 =====

def render_inquiries():
    """문의 관리 페이지"""
    st.markdown("## 📝 문의 관리")

    inquiries = st.session_state.db["inquiry"].get_all_inquiries()

    if inquiries:
        df_inquiries = pd.DataFrame(inquiries)

        # 표시할 컬럼 선택
        display_cols = ["id", "client_name", "project_type", "budget", "status", "created_at"]
        available_cols = [c for c in display_cols if c in df_inquiries.columns]

        display_df = df_inquiries[available_cols].copy()

        # 프로젝트 유형 한글화
        type_map = {
            "website": "웹사이트", "landing": "랜딩페이지", "web_app": "웹앱",
            "mobile_app": "모바일앱", "maintenance": "유지보수", "consulting": "컨설팅", "other": "기타"
        }
        if "project_type" in display_df.columns:
            display_df["project_type"] = display_df["project_type"].map(type_map).fillna(display_df["project_type"])

        st.dataframe(display_df, width='stretch', hide_index=True)

        # 상세 보기
        st.markdown("### 문의 상세")
        inquiry_ids = [str(i["id"]) for i in inquiries]
        selected_id = st.selectbox("문의 선택", [""] + inquiry_ids, format_func=lambda x: "선택하세요" if x == "" else f"{x}번 문의")

        if selected_id:
            inquiry = st.session_state.db["inquiry"].get_inquiry(int(selected_id))
            if inquiry:
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"#### 고객 정보")
                    st.markdown(f"- **이름:** {inquiry.get('client_name', '-')}")
                    st.markdown(f"- **이메일:** {inquiry.get('client_email', '-')}")

                    st.markdown(f"#### 문의 내용")
                    st.markdown(f"- **프로젝트 유형:** {inquiry.get('project_type', '-')}")
                    st.markdown(f"- **예산:** {inquiry.get('budget', '-')}")
                    st.markdown(f"- **희망 기간:** {inquiry.get('duration', '-')}")
                    st.markdown(f"- **내용:** {inquiry.get('description', '-')}")

                with col2:
                    st.markdown("#### 빠른 작업")
                    if st.button("📄 견적서 생성", width='stretch'):
                        # 견적서 페이지로 이동 및 문의 ID 전달
                        st.session_state.selected_inquiry = inquiry
                        st.session_state.current_page = "quotations"
                        st.rerun()

                    if st.button("👤 고객 정보 보기", width='stretch'):
                        st.session_state.current_page = "clients"
                        st.rerun()
    else:
        st.info("등록된 문의가 없습니다.")


# ===== 견적 관리 페이지 =====

def render_quotations():
    """견적 관리 페이지"""
    st.markdown("## 💰 견적 관리")

    # AI 자동 생성 탭
    tab1, tab2, tab3 = st.tabs(["🤖 AI 자동 생성", "➕ 수동 생성", "📋 견적서 목록"])

    # ===== AI 자동 생성 =====
    with tab1:
        st.markdown("### 🤖 AI 견적서 자동 생성")
        st.info("고객 문의 내용과 설정된 단가 지침을 바탕으로 AI가 자동으로 견적서를 생성합니다.")

        # API 키 확인
        api_key = st.session_state.db["settings"].get_setting("gemini_api_key")

        if not api_key:
            st.warning("⚠️ Gemini API 키가 설정되지 않았습니다. 설정 페이지에서 API 키를 입력하세요.")
        else:
            # 문의 선택
            inquiries = st.session_state.db["inquiry"].get_all_inquiries()

            if inquiries:
                inquiry_options = {
                    f"{i['id']} - {i.get('client_name', '-')} ({i.get('project_type', '-')})": i
                    for i in inquiries
                }

                selected_inquiry_option = st.selectbox("문의 선택", list(inquiry_options.keys()))

                if selected_inquiry_option:
                    inquiry = inquiry_options[selected_inquiry_option]

                    # 문의 내용 표시
                    with st.expander("📄 문의 내용 보기", expanded=False):
                        st.markdown(f"**고객:** {inquiry.get('client_name', '-')}")
                        st.markdown(f"**프로젝트 유형:** {inquiry.get('project_type', '-')}")
                        st.markdown(f"**예산:** {inquiry.get('budget', '-')}")
                        st.markdown(f"**상세 내용:**")
                        st.text(inquiry.get('description', '-'))

                    col1, col2 = st.columns([1, 1])

                    with col1:
                        use_ai = st.checkbox("🤖 AI 사용", value=True)

                    with col2:
                        company_info = {
                            'name': st.session_state.db["settings"].get_setting("company_name"),
                            'phone': st.session_state.db["settings"].get_setting("company_phone"),
                            'address': st.session_state.db["settings"].get_setting("company_address"),
                        }
                        if not company_info['name']:
                            st.warning("회사 정보를 설정하세요")

                    if st.button("🚀 견적서 생성", width='stretch', type="primary"):
                        with st.spinner("AI가 견적서를 생성 중입니다..."):
                            pricing_guideline = st.session_state.db["settings"].get_setting("pricing_guideline")

                            if use_ai:
                                # AI로 견적서 생성
                                generator = AIQuotationGenerator(api_key=api_key)
                                result = generator.generate_quotation(
                                    inquiry=inquiry,
                                    pricing_guideline=pricing_guideline,
                                    company_info=company_info
                                )

                                # AI 사용 로그 저장
                                from utils import log_ai_usage
                                log_ai_usage(
                                    db=st.session_state.db["settings"],
                                    request_type="quotation_generation",
                                    prompt=f"Inquiry: {inquiry.get('description', '')}",
                                    response=result,
                                    tokens_used=result.get('tokens_used', 0),
                                    cost=result.get('estimated_cost', 0),
                                    model="gpt-4o-mini"
                                )

                                items = result.get('items', [])
                                total_amount = result.get('total_amount', 0)
                                notes = result.get('notes', '')

                                st.success(f"✅ AI가 견적서를 생성했습니다!")
                                st.info(f"💰 예상 비용: ${result.get('estimated_cost', 0):.4f} USD ({result.get('tokens_used', 0)} 토큰)")
                            else:
                                # Fallback
                                items = [
                                    {"name": "프로젝트 개발", "quantity": 1, "unit": "건", "unit_price": 3000000}
                                ]
                                total_amount = 3000000
                                notes = "기본 견적서"

                            # 견적서 저장
                            client_id = inquiry.get('client_id')
                            quotation_id = st.session_state.db["quotation"].add_quotation(
                                client_id=client_id,
                                items=items,
                                total_amount=total_amount,
                                inquiry_id=inquiry['id'],
                                notes=notes
                            )

                            st.success(f"🎉 견적서가 저장되었습니다! (ID: {quotation_id})")
                            st.rerun()
            else:
                st.info("등록된 문의가 없습니다.")

    # ===== 수동 생성 =====
    with tab2:
        with st.expander("➕ 새 견적서 생성", expanded=False):
            with st.form("new_quotation"):
                clients = st.session_state.db["client"].get_all_clients()
                if clients:
                    client_options = {f"{c['id']} - {c['name']} ({c.get('company', '')})": c['id'] for c in clients}
                    selected_client = st.selectbox("고객 선택 *", list(client_options.keys()))

                    col1, col2 = st.columns(2)
                    with col1:
                        item_name = st.text_input("품목명")
                        item_qty = st.number_input("수량", min_value=1, value=1)
                    with col2:
                        item_price = st.number_input("단가 (원)", min_value=0, value=0)

                    add_item = st.form_submit_button("품목 추가")

                    # 품목 리스트 세션 상태
                    if "quotation_items" not in st.session_state:
                        st.session_state.quotation_items = []

                    if add_item and item_name:
                        st.session_state.quotation_items.append({
                            "name": item_name,
                            "quantity": item_qty,
                            "price": item_price,
                            "amount": item_qty * item_price
                        })

                    # 품목 목록 표시
                    if st.session_state.quotation_items:
                        st.markdown("**품목 목록:**")
                        for i, item in enumerate(st.session_state.quotation_items):
                            st.markdown(f"- {item['name']} x {item['quantity']} = {format_currency(item['amount'])}")

                        total = sum(item['amount'] for item in st.session_state.quotation_items)
                        st.markdown(f"**합계: {format_currency(total)}**")

                        if st.form_submit_button("견적서 저장", width='stretch'):
                            client_id = client_options[selected_client]
                            quotation_id = st.session_state.db["quotation"].add_quotation(
                                client_id=client_id,
                                items=st.session_state.quotation_items,
                                total_amount=total
                            )
                            st.session_state.quotation_items = []
                            st.success(f"견적서가 생성되었습니다. (ID: {quotation_id})")
                            st.rerun()
                else:
                    st.warning("먼저 고객을 등록해주세요.")

    # ===== 견적서 목록 =====
    with tab3:
        quotations = st.session_state.db["quotation"].get_all_quotations()

        if quotations:
            df_quotations = pd.DataFrame(quotations)

            # 표시용 데이터프레임
            display_data = []
            for q in quotations:
                display_data.append({
                    "ID": q["id"],
                    "견적번호": q["quotation_number"],
                    "고객": q.get("client_name", "-"),
                    "금액": format_currency(int(q["total_amount"])),
                    "상태": get_status_badge(q["status"]),
                    "생성일": format_date(q["created_at"])
                })

            st.dataframe(pd.DataFrame(display_data), width='stretch', hide_index=True)

            # 상세 보기
            st.markdown("### 견적서 상세")
            quotation_ids = [str(q["id"]) for q in quotations]
            selected_id = st.selectbox("견적서 선택", [""] + quotation_ids,
                                     format_func=lambda x: "선택하세요" if x == "" else f"{x}번 견적서")

            if selected_id:
                quotation = st.session_state.db["quotation"].get_quotation(int(selected_id))
                if quotation:
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"#### {quotation['quotation_number']}")
                        st.markdown(f"**고객:** {quotation.get('client_name', '-')}")
                        st.markdown(f"**이메일:** {quotation.get('client_email', '-')}")

                        st.markdown("**품목 목록:**")
                        items = quotation.get('items', [])
                        if items:
                            # 품목 테이블 표시
                            item_data = []
                            for item in items:
                                item_data.append({
                                    "품목": item.get('name', '-'),
                                    "수량": item.get('quantity', 1),
                                    "단가": format_currency(item.get('unit_price', item.get('price', 0))),
                                    "금액": format_currency(item.get('amount', item.get('unit_price', 0) * item.get('quantity', 1)))
                                })
                            st.dataframe(pd.DataFrame(item_data), width='stretch', hide_index=True)

                        total = int(quotation['total_amount'])
                        vat = int(total * 0.1)
                        grand_total = total + vat

                        st.markdown(f"**공급가액:** {format_currency(total)}")
                        st.markdown(f"**부가세(10%):** {format_currency(vat)}")
                        st.markdown(f"**합계:** {format_currency(grand_total)}")

                    with col2:
                        st.markdown("#### 작업")

                        # 상태 변경
                        statuses = ["draft", "sent", "approved", "rejected"]
                        status_labels = {"draft": "초안", "sent": "발송", "approved": "승인", "rejected": "거절"}
                        current_status = quotation["status"]

                        new_status = st.selectbox("견적 상태", statuses,
                                                index=statuses.index(current_status) if current_status in statuses else 0,
                                                format_func=lambda x: status_labels[x])

                        if st.button("🔄 상태 변경", width='stretch'):
                            st.session_state.db["quotation"].update_quotation_status(int(selected_id), new_status)
                            st.success("상태가 변경되었습니다.")
                            st.rerun()

                        st.markdown("---")

                        # PDF 다운로드
                        if st.button("📄 PDF 다운로드", width='stretch'):
                            with st.spinner("PDF를 생성 중입니다..."):
                                try:
                                    pdf_gen = PDFQuotationGenerator()

                                    # 고객 정보 가져오기
                                    client = st.session_state.db["client"].get_client(quotation['client_id'])

                                    # 회사 정보
                                    company_info = {
                                        'name': st.session_state.db["settings"].get_setting("company_name"),
                                        'phone': st.session_state.db["settings"].get_setting("company_phone"),
                                        'address': st.session_state.db["settings"].get_setting("company_address"),
                                    }

                                    # PDF 생성
                                    pdf_data = pdf_gen.generate_quotation_pdf(
                                        quotation=quotation,
                                        client=client,
                                        company_info=company_info if company_info['name'] else None
                                    )

                                    # 다운로드 버튼
                                    st.download_button(
                                        label="⬇️ PDF 파일 다운로드",
                                        data=pdf_data,
                                        file_name=f"견적서_{quotation['quotation_number']}.pdf",
                                        mime="application/pdf",
                                        width='stretch'
                                    )
                                except Exception as e:
                                    st.error(f"PDF 생성 오류: {str(e)}")

                        # 이메일 발송
                        if st.button("📧 이메일 발송", width='stretch'):
                            # SMTP 설정 확인
                            smtp_settings = st.session_state.db["settings"].get_all_settings()
                            sender = EmailSender.create_from_settings(smtp_settings)

                            if not sender:
                                st.error("SMTP 설정이 되어 있지 않습니다. 설정 페이지에서 이메일을 구성하세요.")
                            else:
                                with st.spinner("이메일을 발송 중입니다..."):
                                    try:
                                        # PDF 생성
                                        pdf_gen = PDFQuotationGenerator()
                                        client = st.session_state.db["client"].get_client(quotation['client_id'])
                                        company_info = {
                                            'name': smtp_settings.get('company_name', '에이전시'),
                                            'phone': smtp_settings.get('company_phone'),
                                            'address': smtp_settings.get('company_address'),
                                        }

                                        pdf_data = pdf_gen.generate_quotation_pdf(
                                            quotation=quotation,
                                            client=client,
                                            company_info=company_info if company_info['name'] else None
                                        )

                                        # 이메일 발송
                                        result = sender.send_quotation(
                                            to_email=quotation.get('client_email', ''),
                                            client_name=quotation.get('client_name', ''),
                                            quotation_number=quotation['quotation_number'],
                                            quotation_url=f"http://localhost:8501/quotation/{quotation['id']}",
                                            pdf_data=pdf_data,
                                            company_name=company_info['name']
                                        )

                                        if result['success']:
                                            st.success("✅ " + result['message'])
                                            # 상태를 'sent'로 변경
                                            st.session_state.db["quotation"].update_quotation_status(int(selected_id), "sent")
                                        else:
                                            st.error("❌ " + result['message'])

                                    except Exception as e:
                                        st.error(f"이메일 발송 오류: {str(e)}")
        else:
            st.info("등록된 견적서가 없습니다.")


# ===== 프로젝트 관리 페이지 =====

def render_projects():
    """프로젝트 관리 페이지"""
    st.markdown("## 🚧 프로젝트 관리")

    # 새 프로젝트 생성
    with st.expander("➕ 새 프로젝트 생성", expanded=False):
        with st.form("new_project"):
            clients = st.session_state.db["client"].get_all_clients()
            if clients:
                client_options = {f"{c['id']} - {c['name']}": c['id'] for c in clients}
                selected_client = st.selectbox("고객 선택 *", list(client_options.keys()))

                project_name = st.text_input("프로젝트명 *")
                project_desc = st.text_area("프로젝트 설명")

                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("시작 예정일")
                with col2:
                    end_date = st.date_input("종료 예정일")

                contract_amount = st.number_input("계약 금액 (원)", min_value=0, value=0)

                if st.form_submit_button("프로젝트 생성", width='stretch'):
                    client_id = client_options[selected_client]
                    project_id = st.session_state.db["project"].add_project(
                        client_id=client_id,
                        name=project_name,
                        description=project_desc,
                        total_contract_amount=contract_amount
                    )
                    st.success(f"프로젝트가 생성되었습니다. (ID: {project_id})")
                    st.rerun()
            else:
                st.warning("먼저 고객을 등록해주세요.")

    # 프로젝트 목록
    projects = st.session_state.db["project"].get_all_projects()

    if projects:
        # 탭으로 뷰 전환
        tab1, tab2 = st.tabs(["📋 리스트 보기", "📊 칸반 보드"])

        with tab1:
            for project in projects:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.markdown(f"### {project['name']}")
                        st.markdown(f"고객: {project.get('client_name', '-')}")

                        # 진행률 바
                        progress = project.get('progress', 0)
                        st.markdown(f"""
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {progress}%"></div>
                            </div>
                            <small>진행률: {progress}%</small>
                        """, unsafe_allow_html=True)

                    with col2:
                        st.markdown(f"{get_status_badge(project['status'])}")
                        st.markdown(f"{format_currency(project.get('total_contract_amount', 0))}")

                    with col3:
                        if st.button("상세", key=f"detail_{project['id']}", width='stretch'):
                            st.session_state.selected_project = project['id']
                            st.rerun()

                st.markdown("---")

        with tab2:
            # 칸반 보드
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown("#### 📋 기획")
                planning_projects = [p for p in projects if p['status'] == 'planning']
                for p in planning_projects:
                    st.markdown(f"""
                        <div class="kanban-card" style="padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                            <strong>{p['name']}</strong><br>
                            <small>{p.get('client_name', '-')}</small>
                        </div>
                    """, unsafe_allow_html=True)

            with col2:
                st.markdown("#### 🚧 진행중")
                active_projects = [p for p in projects if p['status'] == 'active']
                for p in active_projects:
                    st.markdown(f"""
                        <div class="kanban-card" style="padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                            <strong>{p['name']}</strong><br>
                            <small>{p.get('client_name', '-')}</small><br>
                            <small>진행률: {p.get('progress', 0)}%</small>
                        </div>
                    """, unsafe_allow_html=True)

            with col3:
                st.markdown("#### ✅ 완료")
                completed_projects = [p for p in projects if p['status'] == 'completed']
                for p in completed_projects:
                    st.markdown(f"""
                        <div class="kanban-card" style="padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                            <strong>{p['name']}</strong><br>
                            <small>{p.get('client_name', '-')}</small>
                        </div>
                    """, unsafe_allow_html=True)

            with col4:
                st.markdown("#### ⏸️ 보류")
                hold_projects = [p for p in projects if p['status'] == 'on_hold']
                for p in hold_projects:
                    st.markdown(f"""
                        <div class="kanban-card" style="padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                            <strong>{p['name']}</strong><br>
                            <small>{p.get('client_name', '-')}</small>
                        </div>
                    """, unsafe_allow_html=True)

        # 프로젝트 상세 보기
        if "selected_project" in st.session_state:
            project_id = st.session_state.selected_project
            project = st.session_state.db["project"].get_project(project_id)

            if project:
                st.markdown("### 프로젝트 상세")

                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"#### {project['name']}")
                    st.markdown(f"- **고객:** {project.get('client_name', '-')}")
                    st.markdown(f"- **설명:** {project.get('description', '-')}")

                    # 진행률 업데이트
                    new_progress = st.slider("진행률", 0, 100, project.get('progress', 0))
                    if st.button("진행률 업데이트"):
                        st.session_state.db["project"].update_project_progress(project_id, new_progress)
                        st.success("진행률이 업데이트되었습니다.")
                        st.rerun()

                with col2:
                    st.markdown("#### 태스크 관리")

                    # 태스크 추가
                    with st.form("add_task"):
                        task_title = st.text_input("태스크명")
                        task_priority = st.selectbox("우선순위", ["low", "medium", "high"],
                                                   format_func=lambda x: {"low": "낮음", "medium": "보통", "high": "높음"}[x])

                        if st.form_submit_button("태스크 추가"):
                            if task_title:
                                st.session_state.db["task"].add_task(
                                    project_id=project_id,
                                    title=task_title,
                                    priority=task_priority
                                )
                                st.success("태스크가 추가되었습니다.")
                                st.rerun()

                    # 태스크 목록
                    tasks = st.session_state.db["task"].get_project_tasks(project_id)
                    if tasks:
                        st.markdown("**태스크 목록:**")
                        for task in tasks:
                            status_emoji = {"todo": "⬜", "in_progress": "🟡", "done": "✅"}
                            st.markdown(f"{status_emoji.get(task['status'], '⬜')} {task['title']}")
                    else:
                        st.info("등록된 태스크가 없습니다.")

                if st.button("닫기"):
                    del st.session_state.selected_project
                    st.rerun()
    else:
        st.info("등록된 프로젝트가 없습니다.")


# ===== 설정 페이지 =====

def render_settings():
    """설정 페이지"""
    st.markdown("## ⚙️ 설정")

    st.markdown("### 💰 단가 지침 (Pricing Guideline)")
    st.info("AI가 견적서를 생성할 때 참조하는 단가표입니다.")

    current_pricing = st.session_state.db["settings"].get_setting("pricing_guideline")

    pricing_guideline = st.text_area(
        "단가 지침",
        value=current_pricing,
        height=200,
        help="각 서비스의 기준 가격을 한 줄에 하나씩 입력하세요."
    )

    if st.button("단가 지침 저장", width='stretch'):
        st.session_state.db["settings"].set_setting("pricing_guideline", pricing_guideline)
        st.success("단가 지침이 저장되었습니다.")

    st.markdown("---")

    st.markdown("### 📧 이메일 설정 (SMTP)")
    st.warning("Gmail을 사용하는 경우 앱 비밀번호를 생성해야 합니다.")

    col1, col2 = st.columns(2)

    with col1:
        smtp_host = st.text_input("SMTP 호스트",
                                  value=st.session_state.db["settings"].get_setting("smtp_host"))
        smtp_port = st.text_input("SMTP 포트",
                                  value=st.session_state.db["settings"].get_setting("smtp_port", "587"))

    with col2:
        smtp_email = st.text_input("발신 이메일",
                                   value=st.session_state.db["settings"].get_setting("smtp_email"))
        smtp_password = st.text_input("비밀번호 / 앱 비밀번호",
                                     value=st.session_state.db["settings"].get_setting("smtp_password"),
                                     type="password")

    if st.button("이메일 설정 저장", width='stretch'):
        st.session_state.db["settings"].set_setting("smtp_host", smtp_host)
        st.session_state.db["settings"].set_setting("smtp_port", smtp_port)
        st.session_state.db["settings"].set_setting("smtp_email", smtp_email)
        st.session_state.db["settings"].set_setting("smtp_password", smtp_password)
        st.success("이메일 설정이 저장되었습니다.")

    st.markdown("---")

    st.markdown("### 🏢 회사 정보")
    col1, col2 = st.columns(2)

    with col1:
        company_name = st.text_input("회사명",
                                    value=st.session_state.db["settings"].get_setting("company_name"))
        company_address = st.text_input("주소",
                                       value=st.session_state.db["settings"].get_setting("company_address"))

    with col2:
        company_phone = st.text_input("연락처",
                                     value=st.session_state.db["settings"].get_setting("company_phone"))

    if st.button("회사 정보 저장", width='stretch'):
        st.session_state.db["settings"].set_setting("company_name", company_name)
        st.session_state.db["settings"].set_setting("company_address", company_address)
        st.session_state.db["settings"].set_setting("company_phone", company_phone)
        st.success("회사 정보가 저장되었습니다.")

    st.markdown("---")

    st.markdown("### 🤖 AI 설정")
    st.info("Gemini API를 사용하여 견적서를 자동 생성합니다.")

    api_key = st.text_input("Gemini API Key",
                           value=st.session_state.db["settings"].get_setting("gemini_api_key"),
                           type="password")

    if st.button("API 키 저장", width='stretch'):
        st.session_state.db["settings"].set_setting("gemini_api_key", api_key)
        st.success("API 키가 저장되었습니다.")


# ===== 계약 관리 페이지 =====

def render_contracts():
    """계약 관리 페이지"""
    st.markdown("## 📄 계약 관리")

    # 탭
    tab1, tab2, tab3 = st.tabs(["➕ 계약서 생성", "📋 계약서 목록", "🔗 서명 링크"])

    # ===== 계약서 생성 =====
    with tab1:
        st.markdown("### ➕ 계약서 생성")
        st.info("견적서가 승인(approved) 상태인 경우 계약서를 생성할 수 있습니다.")

        # 승인된 견적서 목록
        quotations = st.session_state.db["quotation"].get_all_quotations()
        approved_quotations = [q for q in quotations if q["status"] == "approved"]

        if approved_quotations:
            quotation_options = {
                f"{q['quotation_number']} - {q.get('client_name', '-')} ({format_currency(int(q['total_amount']))})": q
                for q in approved_quotations
            }

            selected_quotation_option = st.selectbox("견적서 선택", list(quotation_options.keys()))

            if selected_quotation_option:
                quotation = quotation_options[selected_quotation_option]

                # 견적서 내용 미리보기
                with st.expander("📄 견적서 내용 보기", expanded=False):
                    items = quotation.get('items', [])
                    for item in items:
                        st.markdown(f"- **{item.get('name', '-')}**: {format_currency(item.get('unit_price', item.get('price', 0)))}")

                    total = int(quotation['total_amount'])
                    st.markdown(f"**합계:** {format_currency(total)} (+VAT: {format_currency(int(total * 0.1))})")

                if st.button("📄 계약서 생성", width='stretch', type="primary"):
                    # 계약서 생성
                    contract_gen = ContractGenerator()

                    # 고객 정보
                    client = st.session_state.db["client"].get_client(quotation['client_id'])

                    # 회사 정보
                    settings = st.session_state.db["settings"].get_all_settings()
                    company_info = {
                        'name': settings.get('company_name'),
                        'phone': settings.get('company_phone'),
                        'address': settings.get('company_address'),
                    }

                    # 계약서 내용 생성
                    contract_data = contract_gen.generate_contract_from_quotation(
                        quotation=quotation,
                        client=client,
                        company_info=company_info
                    )

                    # 데이터베이스에 계약서 저장 (ContractDB의 메서드 사용)
                    import sqlite3
                    conn = st.session_state.db["settings"].get_connection()
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT INTO contracts (quotation_id, client_id, contract_number, content, status)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        quotation['id'],
                        quotation['client_id'],
                        contract_data['contract_number'],
                        contract_data['content'],
                        'pending'
                    ))
                    contract_id = cursor.lastrowid
                    conn.commit()
                    conn.close()

                    st.success(f"✅ 계약서가 생성되었습니다! (계약번호: {contract_data['contract_number']})")
                    st.rerun()
        else:
            st.info("승인된 견적서가 없습니다. 먼저 견적서를 승인해주세요.")

    # ===== 계약서 목록 =====
    with tab2:
        st.markdown("### 📋 계약서 목록")

        # 계약서 조회
        import sqlite3
        conn = st.session_state.db["settings"].get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*, cl.name as client_name, cl.email as client_email,
                   q.quotation_number, q.total_amount
            FROM contracts c
            LEFT JOIN clients cl ON c.client_id = cl.id
            LEFT JOIN quotations q ON c.quotation_id = q.id
            ORDER BY c.created_at DESC
        """)
        contracts = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if contracts:
            # 계약서 표시
            for contract in contracts:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])

                    with col1:
                        st.markdown(f"### {contract.get('contract_number', '-')}")
                        st.markdown(f"**고객:** {contract.get('client_name', '-')}")

                    with col2:
                        st.markdown(f"{get_status_badge(contract.get('status', 'pending'))}")
                        st.markdown(f"{format_currency(contract.get('total_amount', 0) * 1.1)}")

                    with col3:
                        if st.button("상세", key=f"contract_{contract['id']}", width='stretch'):
                            st.session_state.selected_contract = contract['id']
                            st.rerun()

                st.markdown("---")

            # 선택된 계약서 상세
            if "selected_contract" in st.session_state:
                contract_id = st.session_state.selected_contract
                contract = next((c for c in contracts if c['id'] == contract_id), None)

                if contract:
                    st.markdown("### 계약서 상세")

                    col1, col2 = st.columns([2, 1])

                    with col1:
                        # 계약서 내용 표시 (HTML)
                        st.markdown("#### 계약서 내용")
                        st.markdown(
                            f'<div style="border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; max-height: 400px; overflow-y: auto;">{contract.get("content", "")}</div>',
                            unsafe_allow_html=True
                        )

                    with col2:
                        st.markdown("#### 서명 현황")

                        # 고객 서명
                        if contract.get('client_signature'):
                            st.success("✅ 고객 서명 완료")
                            st.caption(f"서명일: {format_date(contract.get('client_signed_at'))}")
                        else:
                            st.warning("⏳ 고객 서명 대기중")

                        st.markdown("---")

                        # 관리자 서명
                        if contract.get('admin_signature'):
                            st.success("✅ 관리자 서명 완료")
                            st.caption(f"서명일: {format_date(contract.get('admin_signed_at'))}")
                        else:
                            if st.button("✍️ 관리자 서명하기", width='stretch'):
                                # 관리자 서명 모달
                                st.session_state.show_admin_sign = True
                                st.rerun()

                        st.markdown("---")

                        # 서명 링크 생성
                        if not contract.get('client_signature'):
                            # 서명 토큰 생성
                            sign_token = secrets.token_urlsafe(16)

                            # 서명 링크
                            sign_url = f"http://localhost:8501/contract/sign/{sign_token}"
                            st.markdown("#### 🔗 고객 서명 링크")
                            st.code(sign_url, language="text")

                            st.info("이 링크를 고객에게 공유하여 서명을 요청하세요.")

                    if st.button("닫기"):
                        del st.session_state.selected_contract
                        if "show_admin_sign" in st.session_state:
                            del st.session_state.show_admin_sign
                        st.rerun()
        else:
            st.info("등록된 계약서가 없습니다.")

    # ===== 서명 링크 관리 =====
    with tab3:
        st.markdown("### 🔗 서명 링크 발송")
        st.info("계약서 서명 링크를 생성하여 고객에게 이메일로 발송할 수 있습니다.")

        if contracts:
            pending_contracts = [c for c in contracts if not c.get('client_signature')]

            if pending_contracts:
                contract_options = {
                    f"{c.get('contract_number', '-')} - {c.get('client_name', '-')}": c
                    for c in pending_contracts
                }

                selected_contract_option = st.selectbox("계약서 선택", list(contract_options.keys()))

                if selected_contract_option:
                    contract = contract_options[selected_contract_option]

                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"**고객 이메일:** {contract.get('client_email', '-')}")

                        sign_token = secrets.token_urlsafe(16)
                        sign_url = f"http://localhost:8501/contract/sign/{sign_token}"
                        st.markdown(f"**서명 링크:**")
                        st.code(sign_url, language="text")

                    with col2:
                        if st.button("📧 이메일 발송", width='stretch'):
                            # SMTP 설정 확인
                            smtp_settings = st.session_state.db["settings"].get_all_settings()
                            sender = EmailSender.create_from_settings(smtp_settings)

                            if not sender:
                                st.error("SMTP 설정이 되어 있지 않습니다.")
                            else:
                                try:
                                    result = sender.send_email(
                                        to_email=contract.get('client_email', ''),
                                        subject=f"[계약서 서명 요청] {contract.get('contract_number', '-')}",
                                        body=f"""안녕하세요,

계약서에 서명해주세요.

아래 링크에서 계약서를 확인하고 서명할 수 있습니다.
{sign_url}

감사합니다.""",
                                        html_body=f"""<!DOCTYPE html>
<html>
<body>
    <h2>계약서 서명 요청</h2>
    <p>안녕하세요,</p>
    <p>계약서에 서명해주세요.</p>
    <p><a href="{sign_url}" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px;">계약서 서명하기</a></p>
</body>
</html>""",
                                        from_name=smtp_settings.get('company_name')
                                    )

                                    if result['success']:
                                        st.success("✅ " + result['message'])
                                    else:
                                        st.error("❌ " + result['message'])
                                except Exception as e:
                                    st.error(f"이메일 발송 오류: {str(e)}")
            else:
                st.info("서명 대기 중인 계약서가 없습니다.")
        else:
            st.info("등록된 계약서가 없습니다.")


# ===== 정산 관리 페이지 =====

def render_payments():
    """정산 관리 페이지"""
    st.markdown("## 💳 정산 관리")

    # 탭
    tab1, tab2 = st.tabs(["➕ 청구서 생성", "📋 결제 현황"])

    # ===== 청구서 생성 =====
    with tab1:
        st.markdown("### ➕ 청구서 생성")

        projects = st.session_state.db["project"].get_all_projects()
        active_projects = [p for p in projects if p["status"] in ["planning", "active"]]

        if active_projects:
            project_options = {
                f"{p['name']} ({p.get('client_name', '-')}): {format_currency(p.get('total_contract_amount', 0))}": p
                for p in active_projects
            }

            selected_project_option = st.selectbox("프로젝트 선택", list(project_options.keys()))

            if selected_project_option:
                project = project_options[selected_project_option]

                col1, col2, col3 = st.columns(3)

                with col1:
                    payment_type = st.selectbox("결제 유형",
                                               ["계약금", "중도금", "잔금", "추가 비용"],
                                               index=0)

                with col2:
                    amount = st.number_input("금액 (원)", min_value=0, value=0)

                with col3:
                    due_date = st.date_input("입금 예정일")

                notes = st.text_area("비고")

                if st.button("💳 청구서 생성", width='stretch'):
                    import sqlite3
                    conn = st.session_state.db["settings"].get_connection()
                    cursor = conn.cursor()

                    # 송장번호 생성
                    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{project['id']:04d}"

                    cursor.execute("""
                        INSERT INTO payments (project_id, client_id, payment_type, amount, due_date, invoice_number, notes, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        project['id'],
                        project['client_id'],
                        payment_type,
                        amount,
                        due_date.isoformat() if due_date else None,
                        invoice_number,
                        notes,
                        'pending'
                    ))
                    payment_id = cursor.lastrowid
                    conn.commit()
                    conn.close()

                    st.success(f"✅ 청구서가 생성되었습니다! (송장번호: {invoice_number})")
                    st.rerun()
        else:
            st.info("진행 중인 프로젝트가 없습니다.")

    # ===== 결제 현황 =====
    with tab2:
        st.markdown("### 📋 결제 현황")

        # 결제 내역 조회
        import sqlite3
        conn = st.session_state.db["settings"].get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, pr.name as project_name, cl.name as client_name, cl.email as client_email
            FROM payments p
            LEFT JOIN projects pr ON p.project_id = pr.id
            LEFT JOIN clients cl ON p.client_id = cl.id
            ORDER BY p.due_date ASC
        """)
        payments = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if payments:
            # 요약
            total_pending = sum(p['amount'] for p in payments if p['status'] == 'pending')
            total_paid = sum(p['amount'] for p in payments if p['status'] == 'paid')

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("총 청구액", format_currency(int(sum(p['amount'] for p in payments))))
            with col2:
                st.metric("입금 대기", format_currency(int(total_pending)))
            with col3:
                st.metric("입금 완료", format_currency(int(total_paid)))

            st.markdown("---")

            # 결제 내역 테이블
            payment_data = []
            for p in payments:
                payment_data.append({
                    "송장번호": p.get('invoice_number', '-'),
                    "프로젝트": p.get('project_name', '-'),
                    "고객": p.get('client_name', '-'),
                    "유형": p.get('payment_type', '-'),
                    "금액": format_currency(int(p['amount'])),
                    "입금 예정일": format_date(p.get('due_date')),
                    "상태": get_status_badge(p.get('status', 'pending'))
                })

            st.dataframe(pd.DataFrame(payment_data), width='stretch', hide_index=True)

            # 상세 보기
            st.markdown("### 결제 상세")
            payment_ids = [str(p['id']) for p in payments]
            selected_id = st.selectbox("결제 선택", [""] + payment_ids,
                                     format_func=lambda x: "선택하세요" if x == "" else f"{x}번 결제")

            if selected_id:
                payment = next((p for p in payments if p['id'] == int(selected_id)), None)
                if payment:
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"#### {payment.get('invoice_number', '-')}")
                        st.markdown(f"**프로젝트:** {payment.get('project_name', '-')}")
                        st.markdown(f"**고객:** {payment.get('client_name', '-')}")
                        st.markdown(f"**결제 유형:** {payment.get('payment_type', '-')}")
                        st.markdown(f"**금액:** {format_currency(int(payment['amount']))}")
                        st.markdown(f"**입금 예정일:** {format_date(payment.get('due_date'))}")
                        st.markdown(f"**비고:** {payment.get('notes', '-')}")

                    with col2:
                        st.markdown("#### 작업")

                        # 상태 변경
                        statuses = ["pending", "paid", "overdue"]
                        status_labels = {"pending": "대기", "paid": "완료", "overdue": "연체"}
                        current_status = payment.get('status', 'pending')

                        new_status = st.selectbox("결제 상태", statuses,
                                                index=statuses.index(current_status) if current_status in statuses else 0,
                                                format_func=lambda x: status_labels[x])

                        if st.button("🔄 상태 변경", width='stretch'):
                            import sqlite3
                            conn = st.session_state.db["settings"].get_connection()
                            cursor = conn.cursor()

                            paid_date = "CURRENT_TIMESTAMP" if new_status == "paid" else "NULL"
                            cursor.execute(f"""
                                UPDATE payments SET status = ?, paid_date = {paid_date}
                                WHERE id = ?
                            """, (new_status, payment['id']))
                            conn.commit()
                            conn.close()

                            st.success("상태가 변경되었습니다.")
                            st.rerun()

                        if st.button("📧 입금 요청 알림", width='stretch'):
                            # SMTP 설정 확인
                            smtp_settings = st.session_state.db["settings"].get_all_settings()
                            sender = EmailSender.create_from_settings(smtp_settings)

                            if not sender:
                                st.error("SMTP 설정이 되어 있지 않습니다.")
                            else:
                                try:
                                    result = sender.send_email(
                                        to_email=payment.get('client_email', ''),
                                        subject=f"[입금 요청] {payment.get('invoice_number', '-')}",
                                        body=f"""안녕하세요,

{payment.get('project_name', '-')} 프로젝트의 {payment.get('payment_type', '-')} 입금을 안내드립니다.

송장번호: {payment.get('invoice_number', '-')}
금액: {format_currency(int(payment['amount']))}
입금 기한: {format_date(payment.get('due_date'))}

지정된 기한 내에 입금 부탁드립니다.

감사합니다.""",
                                        from_name=smtp_settings.get('company_name')
                                    )

                                    if result['success']:
                                        st.success("✅ " + result['message'])
                                    else:
                                        st.error("❌ " + result['message'])
                                except Exception as e:
                                    st.error(f"이메일 발송 오류: {str(e)}")
        else:
            st.info("등록된 결제 내역이 없습니다.")


# ===== 캘린더 페이지 =====

def render_calendar():
    """캘린더 페이지"""
    st.markdown("## 📅 캘린더")

    # 뷰 모드 선택
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        view_mode = st.radio("뷰 모드", ["월간 보기", "주간 보기", "리스트 보기"], horizontal=True)
    with col2:
        if st.button("🔄 동기화", width='stretch'):
            cal_manager = CalendarManager(st.session_state.db["calendar"])
            task_count = cal_manager.sync_from_tasks()
            payment_count = cal_manager.sync_from_payments()
            st.success(f"태스크 {task_count}개, 결제 {payment_count}개 동기화 완료!")
            st.rerun()
    with col3:
        if st.button("📥 내보내기", width='stretch'):
            events = st.session_state.db["calendar"].get_all_events()
            if events:
                ical_data = generate_ical_from_events(events)
                st.download_button(
                    label="⬇️ iCal 파일 다운로드",
                    data=ical_data,
                    file_name=f"calendar_{datetime.now().strftime('%Y%m%d')}.ics",
                    mime="text/calendar",
                    width='stretch'
                )

    st.markdown("---")

    cal_manager = CalendarManager(st.session_state.db["calendar"])

    # 날짜 네비게이션
    if "current_month" not in st.session_state:
        st.session_state.current_month = datetime.now().month
    if "current_year" not in st.session_state:
        st.session_state.current_year = datetime.now().year

    col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
    with col1:
        if st.button("◀ 이전"):
            if st.session_state.current_month == 1:
                st.session_state.current_month = 12
                st.session_state.current_year -= 1
            else:
                st.session_state.current_month -= 1
            st.rerun()
    with col4:
        if st.button("다음 ▶"):
            if st.session_state.current_month == 12:
                st.session_state.current_month = 1
                st.session_state.current_year += 1
            else:
                st.session_state.current_month += 1
            st.rerun()

    with col2:
        pass  # Spacer
    with col3:
        st.markdown(f"#### {st.session_state.current_year}년 {st.session_state.current_month}월")

    st.markdown("")

    # 월간 보기
    if view_mode == "월간 보기":
        render_monthly_view(cal_manager)

    # 주간 보기
    elif view_mode == "주간 보기":
        render_weekly_view(cal_manager)

    # 리스트 보기
    else:
        render_list_view(cal_manager)

    # 이벤트 추가 모달
    with st.expander("➕ 새 이벤트 추가", expanded=False):
        with st.form("add_event_form"):
            col1, col2 = st.columns(2)
            with col1:
                event_title = st.text_input("이벤트 제목 *")
                event_type = st.selectbox("이벤트 유형",
                                         ["general", "meeting", "deadline", "task", "payment"],
                                         format_func=lambda x: {
                                             "general": "일반",
                                             "meeting": "회의",
                                             "deadline": "마감",
                                             "task": "태스크",
                                             "payment": "결제"
                                         }[x])
            with col2:
                event_date = st.date_input("날짜", value=datetime.now().date())
                all_day = st.checkbox("종일 이벤트", value=True)

            if not all_day:
                col1, col2 = st.columns(2)
                with col1:
                    event_time = st.time_input("시작 시간")
                with col2:
                    end_time = st.time_input("종료 시간")

            col1, col2 = st.columns(2)
            with col1:
                event_location = st.text_input("장소")
            with col2:
                event_color = st.color_picker("색상", "#3b82f6")

            event_description = st.text_area("설명")

            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("이벤트 추가", width='stretch')

            if submit and event_title:
                start_datetime = f"{event_date} 00:00:00" if all_day else f"{event_date} {event_time}"
                end_datetime = None if all_day else f"{event_date} {end_time}"

                event_id = st.session_state.db["calendar"].add_event(
                    title=event_title,
                    start_date=start_datetime,
                    end_date=end_datetime,
                    event_type=event_type,
                    description=event_description,
                    location=event_location,
                    all_day=all_day,
                    color=event_color
                )
                st.success(f"이벤트가 추가되었습니다! (ID: {event_id})")
                st.rerun()


def render_monthly_view(cal_manager: CalendarManager):
    """월간 캘린더 렌더링"""
    import calendar

    year = st.session_state.current_year
    month = st.session_state.current_month

    # 월의 첫날과 마지막 날
    first_day = datetime(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]

    # 해당 월의 이벤트 가져오기
    events = cal_manager.get_month_events(year, month)

    # 캘린더 그리드 생성
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    days = cal.monthdayscalendar(year, month)

    # 요일 헤더
    weekdays = ["일", "월", "화", "수", "목", "금", "토"]

    # 캘린더 HTML 생성
    st.markdown(f"""
        <div class="calendar-grid">
    """, unsafe_allow_html=True)

    # 요일 헤더
    for day in weekdays:
        st.markdown(f'<div class="calendar-day-header">{day}</div>', unsafe_allow_html=True)

    # 날짜 셀
    today = datetime.now().date()
    for week in days:
        for day in week:
            if day == 0:
                # 이전/다음 달 날짜
                st.markdown('<div class="calendar-day other-month"></div>', unsafe_allow_html=True)
            else:
                current_date = f"{year}-{month:02d}-{day:02d}"
                is_today = (today.year == year and today.month == month and today.day == day)

                # 해당 날짜의 이벤트 찾기
                day_events = [e for e in events if e['start_date'].startswith(current_date)]

                event_html = ""
                for event in day_events[:3]:  # 최대 3개 표시
                    title = event['title']
                    event_html += f'<div class="calendar-event {event.get("event_type", "general")}" title="{title}">{title}</div>'

                if len(day_events) > 3:
                    event_html += f'<div class="calendar-event general">+{len(day_events) - 3} 더보기</div>'

                today_class = "today" if is_today else ""

                st.markdown(f"""
                    <div class="calendar-day {today_class}" onclick="selectDate('{current_date}')">
                        <div class="calendar-day-number">{day}</div>
                        {event_html}
                    </div>
                """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_weekly_view(cal_manager: CalendarManager):
    """주간 캘린더 렌더링"""
    from datetime import timedelta

    current_date = datetime(st.session_state.current_year, st.session_state.current_month, 1)
    start_of_week = current_date - timedelta(days=current_date.weekday())

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("◀ 이전 주"):
            st.session_state.current_week_start = (start_of_week - timedelta(weeks=1)).strftime("%Y-%m-%d")
            st.rerun()
    with col3:
        if st.button("다음 주 ▶"):
            st.session_state.current_week_start = (start_of_week + timedelta(weeks=1)).strftime("%Y-%m-%d")
            st.rerun()

    week_start = start_of_week
    weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]

    for i in range(7):
        day = week_start + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")
        events = cal_manager.get_events_by_date(date_str)

        with st.container():
            st.markdown(f"""
                <div class="weekly-day">
                    <div class="weekly-day-header">
                        <span class="weekly-day-name">{weekdays[i]} {day.month}/{day.day}</span>
                        <span class="weekly-day-date">{date_str}</span>
                    </div>
                """, unsafe_allow_html=True)

            if events:
                for event in events:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"""
                            <div class="calendar-event {event.get('event_type', 'general')}">
                                <strong>{event['title']}</strong>
                            </div>
                        """, unsafe_allow_html=True)
                        if event.get('description'):
                            st.caption(event['description'])
                    with col2:
                        if st.button("🗑️", key=f"del_{event['id']}"):
                            st.session_state.db["calendar"].delete_event(event['id'])
                            st.rerun()
            else:
                st.caption("이벤트 없음")

            st.markdown('</div>', unsafe_allow_html=True)


def render_list_view(cal_manager: CalendarManager):
    """리스트 뷰 렌더링"""
    events = st.session_state.db["calendar"].get_all_events()

    if events:
        # 필터
        col1, col2, col3 = st.columns(3)
        with col1:
            type_filter = st.selectbox("유형 필터", ["all", "general", "meeting", "deadline", "task", "payment"],
                                      format_func=lambda x: {
                                          "all": "전체",
                                          "general": "일반",
                                          "meeting": "회의",
                                          "deadline": "마감",
                                          "task": "태스크",
                                          "payment": "결제"
                                      }[x], key="type_filter")

        filtered_events = events
        if type_filter != "all":
            filtered_events = [e for e in events if e.get('event_type') == type_filter]

        # 날짜순 정렬
        filtered_events = sorted(filtered_events, key=lambda x: x['start_date'])

        for event in filtered_events:
            with st.container():
                col1, col2, col3 = st.columns([4, 2, 1])

                with col1:
                    st.markdown(f"**{event['title']}**")
                    st.caption(f"📅 {format_date(event['start_date'])}")
                    if event.get('description'):
                        st.caption(event['description'])

                with col2:
                    type_labels = {
                        "general": "일반",
                        "meeting": "회의",
                        "deadline": "마감",
                        "task": "태스크",
                        "payment": "결제"
                    }
                    st.markdown(f'<span class="badge badge-info">{type_labels.get(event.get("event_type", "general"), "일반")}</span>',
                               unsafe_allow_html=True)

                with col3:
                    if st.button("🗑️", key=f"list_del_{event['id']}"):
                        st.session_state.db["calendar"].delete_event(event['id'])
                        st.rerun()

                st.markdown("---")
    else:
        st.info("등록된 이벤트가 없습니다.")


# ===== 시간 추적 페이지 =====

def render_time_tracker():
    """시간 추적 페이지"""
    st.markdown("## ⏱️ 시간 추적")

    tab1, tab2, tab3 = st.tabs(["⏱️ 타이머", "📝 수동 입력", "📊 리포트"])

    # ===== 타이머 =====
    with tab1:
        st.markdown("### 실시간 타이머")

        projects = st.session_state.db["project"].get_all_projects()
        if projects:
            col1, col2 = st.columns(2)
            with col1:
                project_options = {f"{p['name']} ({p.get('client_name', '-')})": p['id'] for p in projects}
                selected_project = st.selectbox("프로젝트 선택", list(project_options.keys()))

            with col2:
                if selected_project:
                    project_id = project_options[selected_project]
                    tasks = st.session_state.db["task"].get_project_tasks(project_id)
                    task_options = {"태스크 없음": None}
                    for t in tasks:
                        task_options[f"{t['title']}"] = t['id']
                    selected_task = st.selectbox("태스크 선택 (선택사항)", list(task_options.keys()))

            timer_title = st.text_input("작업 제목")

            # 진행 중인 세션 확인
            active_session = st.session_state.db["time_session"].get_active_session(
                project_id if selected_project else None
            )

            col1, col2, col3 = st.columns([1, 1, 1])

            with col1:
                if active_session:
                    if st.button("⏹️ 정지", width='stretch', type="primary"):
                        st.session_state.db["time_session"].stop_session(active_session['id'])
                        st.success("타이머가 정지되었습니다.")
                        st.rerun()
                else:
                    if st.button("▶️ 시작", width='stretch', type="primary"):
                        if selected_project:
                            task_id = task_options[selected_task] if selected_task != "태스크 없음" else None
                            st.session_state.db["time_session"].start_session(
                                project_id=project_id,
                                task_id=task_id,
                                title=timer_title or "작업"
                            )
                            st.success("타이머가 시작되었습니다.")
                            st.rerun()

            with col2:
                if st.button("⏸️ 일시정지", width='stretch'):
                    st.info("일시정지 기능은 준비 중입니다.")

            with col3:
                if active_session:
                    # 경과 시간 계산
                    start = datetime.fromisoformat(active_session['start_time'])
                    elapsed = datetime.now() - start
                    hours, remainder = divmod(elapsed.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)

                    st.markdown(f"""
                        <div class="timer-display">
                            {elapsed.days * 24 + hours:02d}:{minutes:02d}
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                        <div class="timer-display">
                            00:00
                        </div>
                    """, unsafe_allow_html=True)

        else:
            st.warning("먼저 프로젝트를 생성해주세요.")

    # ===== 수동 입력 =====
    with tab2:
        st.markdown("### 수동 시간 입력")

        with st.form("add_time_entry"):
            col1, col2 = st.columns(2)
            with col1:
                project_options = {f"{p['name']}": p['id'] for p in projects}
                entry_project = st.selectbox("프로젝트 *", list(project_options.keys()) if projects else [])
                entry_date = st.date_input("날짜", value=datetime.now().date())

            with col2:
                if entry_project:
                    entry_project_id = project_options[entry_project]
                    entry_tasks = st.session_state.db["task"].get_project_tasks(entry_project_id)
                    entry_task_options = {"태스크 없음": None}
                    for t in entry_tasks:
                        entry_task_options[f"{t['title']}"] = t['id']
                    entry_task = st.selectbox("태스크", list(entry_task_options.keys()))

            entry_title = st.text_input("작업 제목 *")
            entry_duration = st.number_input("소요 시간 (분)", min_value=1, value=60)
            entry_billable = st.checkbox("청구 가능", value=True)
            entry_hourly_rate = st.number_input("시간당 단가 (원)", min_value=0, value=0)
            entry_description = st.text_area("설명")

            if st.form_submit_button("시간 기록 추가", width='stretch'):
                if entry_project and entry_title:
                    task_id = entry_task_options[entry_task] if entry_task != "태스크 없음" else None

                    st.session_state.db["time_entry"].add_entry(
                        project_id=project_options[entry_project],
                        title=entry_title,
                        duration_minutes=entry_duration,
                        entry_date=entry_date.isoformat(),
                        task_id=task_id,
                        description=entry_description,
                        billable=entry_billable,
                        hourly_rate=entry_hourly_rate
                    )
                    st.success("시간 기록이 추가되었습니다.")
                    st.rerun()

        # 최근 시간 기록
        st.markdown("### 최근 기록")
        if projects:
            recent_entries = st.session_state.db["time_entry"].get_entries_by_date_range(
                (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                datetime.now().strftime("%Y-%m-%d")
            )

            if recent_entries:
                for entry in recent_entries:
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"**{entry['title']}**")
                        st.caption(f"📅 {format_date(entry['entry_date'])}")
                    with col2:
                        hours = entry['duration_minutes'] / 60
                        st.markdown(f"⏱️ {hours:.1f}시간")
                        if entry['billable']:
                            st.markdown('<span class="billable-badge yes">청구가능</span>', unsafe_allow_html=True)
                    with col3:
                        if st.button("🗑️", key=f"time_{entry['id']}"):
                            st.session_state.db["time_entry"].delete_entry(entry['id'])
                            st.rerun()
                    st.markdown("---")
            else:
                st.info("최근 기록이 없습니다.")

    # ===== 리포트 =====
    with tab3:
        st.markdown("### 시간 리포트")

        col1, col2 = st.columns(2)
        with col1:
            report_start = st.date_input("시작일", value=(datetime.now() - timedelta(days=30)).date())
        with col2:
            report_end = st.date_input("종료일", value=datetime.now().date())

        # 기간별 총 시간
        total_hours = st.session_state.db["time_entry"].get_total_hours(
            start_date=report_start.isoformat(),
            end_date=report_end.isoformat()
        )
        billable_hours = st.session_state.db["time_entry"].get_total_hours(
            start_date=report_start.isoformat(),
            end_date=report_end.isoformat(),
            billable_only=True
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 작업 시간", f"{total_hours:.1f}시간")
        with col2:
            st.metric("청구 가능 시간", f"{billable_hours:.1f}시간")
        with col3:
            st.metric("청구 불가 시간", f"{total_hours - billable_hours:.1f}시간")

        st.markdown("---")

        # 프로젝트별 시간
        st.markdown("### 프로젝트별 작업 시간")

        project_times = {}
        for project in projects:
            hours = st.session_state.db["time_entry"].get_total_hours(
                project_id=project['id'],
                start_date=report_start.isoformat(),
                end_date=report_end.isoformat()
            )
            if hours > 0:
                project_times[project['name']] = hours

        if project_times:
            df_times = pd.DataFrame([
                {"프로젝트": k, "시간": f"{v:.1f}시간"}
                for k, v in sorted(project_times.items(), key=lambda x: x[1], reverse=True)
            ])
            st.dataframe(df_times, width='stretch', hide_index=True)
        else:
            st.info("기록된 시간이 없습니다.")


# ===== 파일 관리 페이지 =====

def render_file_manager():
    """파일 관리 페이지"""
    st.markdown("## 📁 파일 관리")

    projects = st.session_state.db["project"].get_all_projects()

    if not projects:
        st.warning("먼저 프로젝트를 생성해주세요.")
        return

    tab1, tab2 = st.tabs(["📁 파일 목록", "⬆️ 업로드"])

    # ===== 파일 목록 =====
    with tab1:
        col1, col2 = st.columns([2, 1])
        with col1:
            project_options = {f"{p['name']}": p['id'] for p in projects}
            file_project = st.selectbox("프로젝트 선택", list(project_options.keys()))
        with col2:
            category_filter = st.selectbox("카테고리", ["전체", "general", "design", "document", "code", "other"],
                                          format_func=lambda x: {
                                              "전체": "전체",
                                              "general": "일반",
                                              "design": "디자인",
                                              "document": "문서",
                                              "code": "코드",
                                              "other": "기타"
                                          }[x], key="file_cat_filter")

        if file_project:
            project_id = project_options[file_project]

            # 업로드 디렉토리 확인
            upload_dir = Path(__file__).parent / "data" / "uploads" / str(project_id)
            upload_dir.mkdir(parents=True, exist_ok=True)

            # 파일 목록 조회
            if category_filter == "전체":
                files = st.session_state.db["file"].get_files_by_project(project_id)
            else:
                files = st.session_state.db["file"].get_files_by_category(project_id, category_filter)

            if files:
                # 파일 그리드 표시
                for file in files:
                    col1, col2, col3 = st.columns([3, 2, 1])

                    with col1:
                        # 파일 아이콘
                        mime_type = file.get('mime_type', '')
                        if mime_type.startswith('image/'):
                            icon = "🖼️"
                        elif mime_type == 'application/pdf':
                            icon = "📄"
                        elif mime_type.startswith('video/'):
                            icon = "🎬"
                        elif mime_type.startswith('audio/'):
                            icon = "🎵"
                        else:
                            icon = "📎"

                        st.markdown(f"**{icon} {file['filename']}**")
                        st.caption(f"버전 {file['version']} • {file.get('uploaded_by', 'admin')}")

                    with col2:
                        # 카테고리
                        cat_labels = {
                            "general": "일반",
                            "design": "디자인",
                            "document": "문서",
                            "code": "코드",
                            "other": "기타"
                        }
                        st.markdown(f'<span class="badge badge-neutral">{cat_labels.get(file.get("category", "general"), "일반")}</span>',
                                   unsafe_allow_html=True)
                        if file.get('description'):
                            st.caption(file['description'])

                    with col3:
                        if st.button("🗑️", key=f"file_{file['id']}"):
                            st.session_state.db["file"].delete_file(file['id'])
                            st.success("파일이 삭제되었습니다.")
                            st.rerun()

                    st.markdown("---")
            else:
                st.info("등록된 파일이 없습니다.")

    # ===== 업로드 =====
    with tab2:
        with st.form("upload_file"):
            upload_project = st.selectbox("프로젝트 선택 *", list(project_options.keys()))

            col1, col2 = st.columns(2)
            with col1:
                uploaded_file = st.file_uploader("파일 선택", type=[
                    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                    'jpg', 'jpeg', 'png', 'gif', 'svg',
                    'zip', 'txt', 'md'
                ])
            with col2:
                file_category = st.selectbox("카테고리", ["general", "design", "document", "code", "other"],
                                            format_func=lambda x: {
                                                "general": "일반",
                                                "design": "디자인",
                                                "document": "문서",
                                                "code": "코드",
                                                "other": "기타"
                                            }[x])

            file_description = st.text_area("설명")

            if st.form_submit_button("파일 업로드", width='stretch'):
                if upload_project and uploaded_file:
                    project_id = project_options[upload_project]

                    # 파일 저장
                    upload_dir = Path(__file__).parent / "data" / "uploads" / str(project_id)
                    upload_dir.mkdir(parents=True, exist_ok=True)

                    file_path = upload_dir / uploaded_file.name
                    with open(file_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())

                    # MIME 타입 감지 (간단 구현)
                    mime_type = uploaded_file.type
                    if not mime_type:
                        ext = uploaded_file.name.split('.')[-1].lower()
                        mime_map = {
                            'pdf': 'application/pdf',
                            'jpg': 'image/jpeg',
                            'jpeg': 'image/jpeg',
                            'png': 'image/png',
                            'gif': 'image/gif',
                            'svg': 'image/svg+xml',
                            'doc': 'application/msword',
                            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                            'xls': 'application/vnd.ms-excel',
                            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            'zip': 'application/zip',
                            'txt': 'text/plain',
                            'md': 'text/markdown',
                        }
                        mime_type = mime_map.get(ext, 'application/octet-stream')

                    # 데이터베이스에 저장
                    file_id = st.session_state.db["file"].add_file(
                        project_id=project_id,
                        filename=uploaded_file.name,
                        file_path=str(file_path),
                        file_size=uploaded_file.size,
                        mime_type=mime_type,
                        category=file_category,
                        description=file_description
                    )

                    st.success(f"파일이 업로드되었습니다! (ID: {file_id})")
                    st.rerun()


# ===== 로그인 페이지 =====

def render_login():
    """로그인 페이지"""
    st.markdown("""
        <div style="text-align: center; padding: 60px 20px;">
            <h1 style="font-size: 48px; margin: 0;">🚀</h1>
            <h2 style="margin: 20px 0;">에이전시 관리 시스템</h2>
            <p style="color: #64748b;">로그인하여 접속하세요</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.form("login_form"):
            st.markdown("### 로그인")

            email = st.text_input("이메일", placeholder="admin@agency.com")
            password = st.text_input("비밀번호", type="password", placeholder="********")

            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("로그인", type="primary", width='stretch')
            with col2:
                if st.form_submit_button("초기화"):
                    st.rerun()

            if submit and email and password:
                user = auth_manager.authenticate(email, password)

                if user:
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    st.session_state.current_page = "dashboard"

                    # 활동 로그
                    activity_logger.log_login(user['id'], True)

                    st.success(f"환영합니다, {user['name']}님!")
                    st.rerun()
                else:
                    st.error("이메일 또는 비밀번호가 올바르지 않습니다.")

        # 기본 계정 정보 표시 (처음 사용자용)
        with st.expander("기본 계정 정보"):
            st.info("""
            **기본 관리자 계정**
            - 이메일: admin@agency.com
            - 비밀번호: admin1234

            ⚠️ 로그인 후 비밀번호를 변경하세요.
            """)


# ===== 사용자 관리 페이지 =====

def render_users():
    """사용자 관리 페이지"""
    st.markdown("## 👥 팀원 관리")

    tab1, tab2, tab3 = st.tabs(["👥 팀원 목록", "➕ 팀원 추가", "👥 팀 관리"])

    # ===== 팀원 목록 =====
    with tab1:
        users = st.session_state.db["user"].get_all_users()

        if users:
            for user in users:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])

                    with col1:
                        st.markdown(f"**{user['name']}**")
                        st.caption(f"📧 {user['email']}")
                        if user.get('department'):
                            st.caption(f"🏢 {user['department']}")

                    with col2:
                        role_labels = {
                            'admin': '관리자',
                            'manager': '매니저',
                            'member': '팀원',
                            'viewer': '게스트'
                        }
                        role_badges = {
                            'admin': 'badge-danger',
                            'manager': 'badge-warning',
                            'member': 'badge-info',
                            'viewer': 'badge-neutral'
                        }
                        role = user.get('role', 'member')
                        st.markdown(
                            f'<span class="badge {role_badges.get(role, "badge-neutral")}">{role_labels.get(role, role)}</span>',
                            unsafe_allow_html=True
                        )
                        if user.get('is_active'):
                            st.markdown('<span class="badge badge-success">활성</span>', unsafe_allow_html=True)
                        else:
                            st.markdown('<span class="badge badge-danger">비활성</span>', unsafe_allow_html=True)

                    with col3:
                        if st.button("✏️", key=f"edit_user_{user['id']}"):
                            st.session_state.editing_user = user['id']
                            st.rerun()

                    st.markdown("---")
        else:
            st.info("등록된 팀원이 없습니다.")

    # ===== 팀원 추가 =====
    with tab2:
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_name = st.text_input("이름 *")
                new_email = st.text_input("이메일 *")
            with col2:
                new_password = st.text_input("비밀번호 *", type="password")
                new_role = st.selectbox("역할", ["admin", "manager", "member", "viewer"],
                                       format_func=lambda x: {
                                           "admin": "관리자",
                                           "manager": "매니저",
                                           "member": "팀원",
                                           "viewer": "게스트"
                                       }[x])

            new_department = st.text_input("부서")
            new_phone = st.text_input("연락처")

            if st.form_submit_button("팀원 추가", type="primary", width='stretch'):
                if new_name and new_email and new_password:
                    try:
                        user_id = auth_manager.create_user(
                            email=new_email,
                            name=new_name,
                            password=new_password,
                            role=new_role,
                            department=new_department,
                            phone=new_phone
                        )
                        st.success(f"팀원이 추가되었습니다! (ID: {user_id})")

                        # 활동 로그
                        if st.session_state.user:
                            activity_logger.log_creation(
                                user_id=st.session_state.user['id'],
                                entity_type="user",
                                entity_id=user_id,
                                entity_name=new_name
                            )

                        st.rerun()
                    except Exception as e:
                        st.error(f"오류가 발생했습니다: {str(e)}")
                else:
                    st.warning("이름, 이메일, 비밀번호는 필수 항목입니다.")

    # ===== 팀 관리 =====
    with tab3:
        teams = st.session_state.db["team"].get_all_teams()

        st.markdown("### 팀 목록")

        if teams:
            for team in teams:
                with st.expander(f"👥 {team['name']}", expanded=False):
                    st.caption(team.get('description', ''))

                    members = st.session_state.db["team"].get_team_members(team['id'])

                    if members:
                        for member in members:
                            st.markdown(f"- {member.get('name', '알 수 없음')} ({member.get('role', 'member')})")
                    else:
                        st.caption("팀원이 없습니다.")
        else:
            st.info("등록된 팀이 없습니다.")

        with st.expander("➕ 새 팀 생성", expanded=False):
            with st.form("create_team"):
                team_name = st.text_input("팀 이름 *")
                team_description = st.text_area("설명")

                if st.form_submit_button("팀 생성"):
                    if team_name:
                        team_id = st.session_state.db["team"].create_team(
                            name=team_name,
                            description=team_description
                        )
                        st.success(f"팀이 생성되었습니다! (ID: {team_id})")
                        st.rerun()


# ===== 활동 로그 페이지 =====

def render_activity_log():
    """활동 로그 페이지"""
    st.markdown("## 📜 활동 로그")

    col1, col2, col3 = st.columns(3)

    with col1:
        user_filter = st.selectbox("사용자 필터", ["전체"] + [
            f"{u['name']} ({u['email']})" for u in st.session_state.db["user"].get_all_users()
        ])

    with col2:
        action_filter = st.selectbox("액션 필터", ["전체", "생성", "수정", "삭제", "상태변경"])

    with col3:
        limit = st.number_input("표시 개수", min_value=10, max_value=500, value=50)

    st.markdown("---")

    # 활동 로그 조회
    activities = st.session_state.db["activity"].get_activities(limit=limit)

    if activities:
        for activity in activities:
            with st.container():
                col1, col2 = st.columns([4, 1])

                with col1:
                    user_name = activity.get('user_name', '시스템')
                    action_type = activity.get('action_type', '')
                    details = activity.get('details', '')
                    created_at = activity.get('created_at', '')

                    # 액션 타입에 따른 아이콘
                    action_icons = {
                        'created': '➕',
                        'updated': '✏️',
                        'deleted': '🗑️',
                        'status_changed': '🔄',
                        'login': '🔐',
                        'logout': '🚪',
                    }
                    icon = '📌'
                    for key, value in action_icons.items():
                        if key in action_type:
                            icon = value
                            break

                    st.markdown(f"**{icon} {user_name}**")
                    st.caption(f"📅 {format_date(created_at)}")
                    if details:
                        st.caption(details)

                with col2:
                    st.caption(activity.get('entity_type', ''))

                st.markdown("---")
    else:
        st.info("활동 로그가 없습니다.")


# ===== 메인 앱 =====

def main():
    """메인 앱"""
    # 로그인되지 않은 경우
    if not st.session_state.authenticated:
        render_login()
        return

    # 로그인된 경우
    render_sidebar()

    # 페이지 라우팅
    page_renderers = {
        "login": render_login,
        "dashboard": render_dashboard,
        "clients": render_clients,
        "inquiries": render_inquiries,
        "quotations": render_quotations,
        "contracts": render_contracts,
        "projects": render_projects,
        "payments": render_payments,
        "calendar": render_calendar,
        "time_tracker": render_time_tracker,
        "files": render_file_manager,
        "users": render_users,
        "activity": render_activity_log,
        "settings": render_settings,
    }

    renderer = page_renderers.get(st.session_state.current_page, render_login)
    renderer()


if __name__ == "__main__":
    main()
