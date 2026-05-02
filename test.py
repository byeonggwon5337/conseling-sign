import streamlit as st

# 모바일 화면 최적화 설정
st.set_page_config(page_title="상담 관리 시스템", layout="centered")

# --- 로그인 세션 상태 초기화 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False


# --- 로그인 화면 ---
def login_page():
    st.title("📱 상담사 로그인")
    st.write("서비스 이용을 위해 로그인해주세요.")

    with st.form("login_form"):
        user_id = st.text_input("아이디", placeholder="ID 입력")
        password = st.text_input("비밀번호", type="password", placeholder="Password 입력")
        login_button = st.form_submit_button("로그인")

        if login_button:
            # 임시 아이디와 비밀번호 (나중에 지인분께 알려줄 정보)
            if user_id == "admin" and password == "1234":
                st.session_state['logged_in'] = True
                st.rerun()  # 화면 새로고침
            else:
                st.error("아이디 또는 비밀번호가 잘못되었습니다.")


# --- 메인 관리 화면 (로그인 성공 시) ---
def main_dashboard():
    st.title("📑 상담 관리 대시보드")
    st.write(f"반갑습니다, 상담사님!")

    if st.button("로그아웃"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.divider()

    # 향후 구현할 기능 메뉴
    menu = st.radio("수행할 작업을 선택하세요", ["상담 문서 만들기", "서명 현황 확인", "구글 드라이브 확인"])

    if menu == "상담 문서 만들기":
        st.subheader("📍 상담 정보 입력")
        date = st.date_input("상담 날짜")
        location = st.text_input("상담 장소", placeholder="예: 강남역 인근 카페")

        # 터치로 작성하는 기능은 다음 단계에서 라이브러리 추가 예정
        st.info("여기에 파일 업로드 및 정보 기입 기능을 추가할 예정입니다.")


# --- 앱 실행 로직 ---
if st.session_state['logged_in']:
    main_dashboard()
else:
    login_page()