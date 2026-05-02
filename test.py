import streamlit as st
from streamlit_drawable_canvas import st_canvas
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io
from PIL import Image

st.set_page_config(page_title="상담 서명 시스템", layout="centered")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- 로그인 화면 ---
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
    # --- 상담사 대시보드 ---
    st.title("📑 상담 문서 만들기")
    if st.button("로그아웃"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.subheader("1. 상담 정보 입력")
    c_date = st.date_input("상담 날짜")
    c_loc = st.text_input("상담 장소", placeholder="예: 강남역 카페")

    st.subheader("2. 터치로 내용 작성 (장소/특이사항)")
    st.write("아래 하얀 판에 손가락으로 장소나 메모를 적어주세요.")

    # 터치 캔버스 설정
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=3,
        stroke_color="#000000",
        background_color="#ffffff",
        height=200,
        width=300,
        drawing_mode="freedraw",
        key="canvas",
    )

    if st.button("PDF 생성 및 링크 준비"):
        if canvas_result.image_data is not None:
            # PDF 생성 로직
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            p.setFont("Helvetica", 12)

            # 텍스트 데이터 입력
            p.drawString(100, 800, f"Date: {c_date}")
            p.drawString(100, 780, f"Location: {c_loc}")

            # 터치 입력 이미지 합성
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            # PDF에 이미지 배치
            p.drawInlineImage(img, 100, 550, width=200, height=130)
            p.drawString(100, 530, "--------------------------------------------------")
            p.drawString(100, 510, "Client Signature: (Waiting for link...)")

            p.showPage()
            p.save()

            st.success("PDF가 생성되었습니다!")
            st.download_button(
                label="생성된 PDF 다운로드",
                data=buffer.getvalue(),
                file_name=f"counseling_{c_date}.pdf",
                mime="application/pdf"
            )
            st.info("이제 이 파일을 구글 드라이브에 올리거나 링크로 보낼 준비가 되었습니다.")