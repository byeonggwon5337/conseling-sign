import streamlit as st
from streamlit_drawable_canvas import st_canvas
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PIL import Image
import io
import numpy as np

st.set_page_config(page_title="문서 위 직접 서명 시스템", layout="centered")

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
    st.title("🖋️ 문서 위 직접 서명")

    # 1. 파일 업로드 (서명할 문서)
    st.subheader("1. 서명할 문서 업로드")
    bg_file = st.file_uploader("상담 양식 이미지를 업로드하세요 (JPG, PNG)", type=['png', 'jpg', 'jpeg'])

    if bg_file:
        bg_image = Image.open(bg_file)
        # 캔버스 크기에 맞게 이미지 리사이즈 (가로 600px 기준)
        aspect_ratio = bg_image.height / bg_image.width
        canvas_width = 600
        canvas_height = int(canvas_width * aspect_ratio)

        st.subheader("2. 문서 위에 직접 작성 및 서명")
        st.info("손가락이나 펜으로 문서 위 원하는 곳에 서명하세요.")

        # 2. 문서가 배경으로 깔린 캔버스
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",  # 채우기 색상
            stroke_width=2,
            stroke_color="#0000ff",  # 서명 색상 (파란색 펜 느낌)
            background_image=bg_image,  # 업로드한 파일이 배경이 됨
            update_streamlit=True,
            height=canvas_height,
            width=canvas_width,
            drawing_mode="freedraw",
            key="canvas",
        )

        # 3. PDF 생성 및 저장
        if st.button("서명 완료 및 PDF 저장"):
            if canvas_result.image_data is not None:
                # 캔버스 결과를 이미지로 변환
                res_img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')

                # 배경 이미지와 서명 이미지 합성
                final_combined = bg_image.convert("RGBA").resize((canvas_width, canvas_height))
                final_combined = Image.alpha_composite(final_combined, res_img)

                # PDF 생성
                buffer = io.BytesIO()
                # 이미지 크기에 맞춘 PDF 페이지 설정
                p = canvas.Canvas(buffer, pagesize=(canvas_width, canvas_height))
                p.drawInlineImage(final_combined, 0, 0, width=canvas_width, height=canvas_height)
                p.showPage()
                p.save()

                st.success("서명이 포함된 문서가 완성되었습니다!")
                st.download_button(
                    label="📥 완성된 PDF 다운로드",
                    data=buffer.getvalue(),
                    file_name="signed_document.pdf",
                    mime="application/pdf"
                )
    else:
        st.warning("먼저 서명할 문서(이미지 파일)를 업로드해 주세요.")