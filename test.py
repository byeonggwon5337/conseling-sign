import streamlit as st
from streamlit_drawable_canvas import st_canvas
from reportlab.pdfgen import canvas
from PIL import Image
import io, json
from datetime import datetime

# 구글 드라이브 라이브러리 체크
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload

    GDRIVE_AVAILABLE = True
except:
    GDRIVE_AVAILABLE = False

st.set_page_config(page_title="전문 서명 시스템", layout="wide")

# 세션 초기화
if 'signers' not in st.session_state:
    st.session_state['signers'] = []
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- 로그인 ---
if not st.session_state['logged_in']:
    st.title("📱 상담사 로그인")
    with st.form("login"):
        uid = st.text_input("아이디")
        upw = st.text_input("비밀번호", type="password")
        if st.form_submit_button("로그인"):
            if uid == "admin" and upw == "1234":
                st.session_state['logged_in'] = True
                st.rerun()
            else:
                st.error("불일치")
else:
    st.title("🖋️ 다중 서명 시스템")

    with st.sidebar:
        st.header("⚙️ 구글 드라이브 설정")
        gdrive_json = st.text_area("서비스 계정 JSON", height=150)
        gdrive_folder = st.text_input("드라이브 폴더 ID")

        st.divider()
        st.header("📋 서명 목록")
        for i, s in enumerate(st.session_state['signers']):
            st.write(f"{i + 1}. {s['name']} ✅")
        if st.button("목록 전체 초기화"):
            st.session_state['signers'] = []
            st.rerun()

    tab1, tab2 = st.tabs(["✍️ 서명하기", "📁 PDF 생성 및 업로드"])

    with tab1:
        c1, c2 = st.columns([2, 1])
        with c1:
            bg_file = st.file_uploader("📄 문서 업로드", type=['png', 'jpg', 'jpeg'])
        with c2:
            signer_name = st.text_input("✏️ 서명자 이름")

        if bg_file:
            # 이미지 처리
            img = Image.open(bg_file).convert("RGB")
            w_size = 700
            h_size = int(w_size * img.height / img.width)
            bg_resized = img.resize((w_size, h_size))

            st.info("아래 문서 위에 서명을 그린 후, [서명 추가] 버튼을 누르세요.")

            # 서명 캔버스 (HTML 방식보다 훨씬 안정적)
            canvas_result = st_canvas(
                fill_color="rgba(255, 255, 255, 0)",
                stroke_width=3,
                stroke_color="#cc0000",
                background_image=bg_resized,
                update_streamlit=True,
                height=h_size,
                width=w_size,
                drawing_mode="freedraw",
                key="canvas",
            )

            if st.button("➕ 서명 목록에 추가", type="primary"):
                if not signer_name:
                    st.warning("이름을 입력하세요.")
                elif canvas_result.image_data is not None:
                    # 서명 데이터 저장
                    st.session_state['signers'].append({
                        'name': signer_name,
                        'data': canvas_result.image_data
                    })
                    st.success(f"{signer_name}님 서명이 추가되었습니다!")
                    st.rerun()

    with tab2:
        if not st.session_state['signers']:
            st.info("서명을 먼저 추가해주세요.")
        else:
            if st.button("📄 최종 PDF 생성"):
                # PDF 생성 로직 (Pillow 합성)
                img = Image.open(bg_file).convert("RGBA")
                w, h = img.size
                base = img.copy()

                for s in st.session_state['signers']:
                    sig_img = Image.fromarray(s['data'].astype('uint8'), 'RGBA').resize((w, h))
                    base = Image.alpha_composite(base, sig_img)

                buffer = io.BytesIO()
                base.convert("RGB").save(buffer, format="PDF")
                st.session_state['final_pdf'] = buffer.getvalue()
                st.success("PDF 생성 완료!")
                st.download_button("📥 PDF 다운로드", st.session_state['final_pdf'], file_name="signed.pdf")

            # 드라이브 업로드 로직
            if GDRIVE_AVAILABLE and 'final_pdf' in st.session_state and gdrive_json:
                if st.button("☁️ 구글 드라이브 업로드"):
                    try:
                        creds = service_account.Credentials.from_service_account_info(json.loads(gdrive_json), scopes=[
                            "https://www.googleapis.com/auth/drive"])
                        service = build("drive", "v3", credentials=creds)
                        media = MediaIoBaseUpload(io.BytesIO(st.session_state['final_pdf']), mimetype="application/pdf")
                        file = service.files().create(
                            body={"name": f"{datetime.now()}.pdf", "parents": [gdrive_folder] if gdrive_folder else []},
                            media_body=media).execute()
                        st.success(f"업로드 성공! 파일 ID: {file['id']}")
                    except Exception as e:
                        st.error(f"오류: {e}")