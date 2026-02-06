"""
고객 포털 앱
고객이 자신의 프로젝트 진행상황을 확인할 수 있는 별도 Streamlit 앱
"""

import streamlit as st
from datetime import datetime
from utils.portal_auth import PortalAuth, PortalSession
from database import ProjectDB, TaskDB, ClientDB, FileDB, ClientCommunicationDB

# 페이지 설정
st.set_page_config(
    page_title="고객 포털",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS 로드
def load_portal_css():
    css = """
    <style>
        .portal-container {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }

        .portal-header {
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            color: white;
            margin-bottom: 30px;
        }

        .status-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }

        .progress-bar-container {
            height: 24px;
            background: #e2e8f0;
            border-radius: 12px;
            overflow: hidden;
            margin: 10px 0;
        }

        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 12px;
        }

        .message-bubble {
            padding: 12px 16px;
            border-radius: 12px;
            margin-bottom: 12px;
            max-width: 80%;
        }

        .message-admin {
            background: #f3e8ff;
            margin-right: auto;
        }

        .message-client {
            background: #dbeafe;
            margin-left: auto;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

load_portal_css()


# ===== 인증 처리 =====

def check_authentication():
    """토큰 인증 확인"""
    # URL 파라미터에서 토큰 가져오기
    query_params = st.query_params
    token = query_params.get('token', [''])[0]

    if not token:
        return None

    auth = PortalAuth()
    return auth.validate_token(token)


# ===== 메인 페이지 =====

def main():
    # 인증 확인
    user_data = check_authentication()

    if not user_data:
        st.markdown("""
            <div class="portal-header">
                <h1>🔐 고객 포털</h1>
                <p>프로젝트 진행상황을 확인하세요</p>
            </div>
        """, unsafe_allow_html=True)

        st.error("유효하지 않은 접속입니다. 올바른 링크를 통해 접속해주세요.")
        st.info("링크가 만료되었거나 잘못되었을 수 있습니다. 담당자에게 문의해주세요.")
        return

    client_id = user_data['client_id']
    client_name = user_data.get('client_name', '고객')

    # DB 초기화
    project_db = ProjectDB()
    task_db = TaskDB()
    client_db = ClientDB()
    file_db = FileDB()
    comm_db = ClientCommunicationDB()

    # 헤더
    st.markdown(f"""
        <div class="portal-header">
            <h1>👋 {client_name}님, 환영합니다!</h1>
            <p>프로젝트 진행상황을 확인하세요</p>
        </div>
    """, unsafe_allow_html=True)

    # 탭
    tab1, tab2, tab3, tab4 = st.tabs(["📊 프로젝트 현황", "📝 태스크", "💬 메시지", "📁 파일"])

    # ===== 프로젝트 현황 =====
    with tab1:
        # 고객의 모든 프로젝트 조회
        all_projects = project_db.get_all_projects()
        client_projects = [p for p in all_projects if p['client_id'] == client_id]

        if client_projects:
            for project in client_projects:
                st.markdown(f"""
                    <div class="status-card">
                        <h3>🚀 {project['name']}</h3>
                        <p>{project.get('description', '-')}</p>
                        <div class="progress-bar-container">
                            <div class="progress-bar-fill" style="width: {project.get('progress', 0)}%">
                                {project.get('progress', 0)}%
                            </div>
                        </div>
                        <p><small>상태: {project.get('status', 'planning')}</small></p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("진행 중인 프로젝트가 없습니다.")

    # ===== 태스크 =====
    with tab2:
        if client_projects:
            selected_project = st.selectbox(
                "프로젝트 선택",
                client_projects,
                format_func=lambda p: p['name']
            )

            if selected_project:
                tasks = task_db.get_project_tasks(selected_project['id'])

                if tasks:
                    for task in tasks:
                        status_icon = {
                            'todo': '⬜',
                            'in_progress': '🟡',
                            'done': '✅'
                        }.get(task['status'], '⬜')

                        st.markdown(f"""
                            <div class="status-card">
                                <h4>{status_icon} {task['title']}</h4>
                                <p>{task.get('description', '-')}</p>
                                <p><small>마감일: {task.get('due_date', '-')}</small></p>
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("등록된 태스크가 없습니다.")

    # ===== 메시지 =====
    with tab3:
        st.markdown("### 💬 관리자와 대화")

        if client_projects:
            # 메시지 전송
            with st.form("send_message"):
                new_message = st.text_area("메시지 입력")
                if st.form_submit_button("전송"):
                    if new_message:
                        comm_db.send_message(
                            client_id=client_id,
                            sender='client',
                            message=new_message
                        )
                        st.success("메시지가 전송되었습니다.")
                        st.rerun()

            # 메시지 목록
            messages = comm_db.get_messages(client_id)

            if messages:
                for msg in messages:
                    is_from_client = msg['sender'] == 'client'
                    bubble_class = "message-client" if is_from_client else "message-admin"

                    st.markdown(f"""
                        <div class="message-bubble {bubble_class}">
                            <p>{msg['message']}</p>
                            <small>{msg['created_at'][:16]}</small>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("등록된 메시지가 없습니다.")

    # ===== 파일 =====
    with tab4:
        if client_projects:
            file_projects = []

            for project in client_projects:
                files = file_db.get_files_by_project(project['id'])
                if files:
                    file_projects.append((project, files))

            if file_projects:
                for project, files in file_projects:
                    st.markdown(f"#### 📁 {project['name']}")

                    for file in files:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"**📎 {file['filename']}**")
                            if file.get('description'):
                                st.caption(file['description'])
                        with col2:
                            if file['version'] > 1:
                                st.caption(f"v{file['version']}")

                        st.markdown("---")
            else:
                st.info("공유된 파일이 없습니다.")


if __name__ == "__main__":
    main()
