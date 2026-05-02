import streamlit as st
from streamlit_drawable_canvas import st_canvas
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PIL import Image
import io
import numpy as np

st.set_page_config(page_title="전문 상담 관리 시스템", layout="centered")

# --- 로그인 세션 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

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
    st.title("📑 상담 문서 관리")

    # 1. 상담 정보 입력 방식 선택
    st.subheader("1. 상담 정보 입력")
    input_method = st.radio("입력 방식을 선택하세요", ["타이핑하기", "손글씨(터치)로 적기"])

    c_date = st.date_input("상담 날짜")

    if input_method == "타이핑하기":
        c_loc = st.text_input("상담 장소", placeholder="예: 서초동 OO카페")
        c_note = st.text_area("상담 메모")
    else:
        st.write("아래에 장소와 메모를 적어주세요.")
        info_canvas = st_canvas(
            stroke_width=2, stroke_color="#000000", background_color="#f0f2f6",
            height=150, width=400, drawing_mode="freedraw", key="info_canvas"
        )

    # 2. 파일 업로드 기능
    st.subheader("2. 양식 파일 업로드")
    uploaded_file = st.file_uploader("상담 양식이나 배경 이미지를 업로드하세요 (JPG, PNG)", type=['png', 'jpg', 'jpeg'])

    # 3. 서명란
    st.subheader("3. 피상담자 서명")
    sign_canvas = st_canvas(
        stroke_width=3, stroke_color="#0000ff", background_color="#ffffff",
        height=150, width=400, drawing_mode="freedraw", key="sign_canvas"
    )

    # 4. PDF 생성 및 저장
    if st.button("문서 완성 및 PDF 생성"):
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        # 배경 이미지(업로드 파일)가 있다면 먼저 그림
        if uploaded_file:
            bg_img = Image.open(uploaded_file)
            p.drawInlineImage(bg_img, 50, 400, width=500, height=350)

        # 정보 기입
        p.setFont("Helvetica", 12)
        p.drawString(50, 800, f"Date: {c_date}")

        if input_method == "타이핑하기":
            p.drawString(50, 780, f"Location: {c_loc}")
            p.drawString(50, 760, f"Note: {c_note}")
        elif info_canvas.image_data is not None:
            info_img = Image.fromarray(info_canvas.image_data.astype('uint8'), 'RGBA')
            p.drawInlineImage(info_img, 50, 700, width=300, height=80)

        # 서명 이미지 합성
        if sign_canvas.image_data is not None:
            sign_img = Image.fromarray(sign_canvas.image_data.astype('uint8'), 'RGBA')
            p.drawInlineImage(sign_img, 350, 100, width=150, height=60)
            p.drawString(350, 90, "Signature Above")

        p.showPage()
        p.save()

        pdf_data = buffer.getvalue()
        st.success("PDF 문서가 성공적으로 생성되었습니다!")
        st.download_button("📥 완성된 PDF 다운로드", data=pdf_data, file_name=f"result_{c_date}.pdf")

        st.warning("⚠️ 구글 드라이브 자동 저장을 위해 'API 설정'이 필요합니다. 설정 전까지는 다운로드 버튼을 이용해 주세요.")