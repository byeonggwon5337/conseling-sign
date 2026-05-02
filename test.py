import streamlit as st
from streamlit_drawable_canvas import st_canvas
from reportlab.pdfgen import canvas
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

    # 1. 파일 업로드
    st.subheader("1. 서명할 문서 업로드")
    bg_file = st.file_uploader("상담 양식 이미지를 업로드하세요 (JPG, PNG)", type=['png', 'jpg', 'jpeg'])

    if bg_file:
        # 이미지를 열고 RGB 모드로 변환 (에러 방지)
        bg_image = Image.open(bg_file).convert("RGB")

        # 가로 600px 기준으로 비율 맞춤
        w, h = bg_image.size
        aspect_ratio = h / w
        canvas_width = 600
        canvas_height = int(canvas_width * aspect_ratio)

        # 캔버스 크기에 맞게 이미지 리사이즈
        bg_image_resized = bg_image.resize((canvas_width, canvas_height))

        st.subheader("2. 문서 위에 직접 작성 및 서명")

        # 2. 캔버스 설정
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=2,
            stroke_color="#0000ff",
            background_image=bg_image_resized,  # 리사이즈된 이미지 객체 전달
            update_streamlit=True,
            height=canvas_height,
            width=canvas_width,
            drawing_mode="freedraw",
            key="canvas",
        )

        # 3. PDF 생성
        if st.button("서명 완료 및 PDF 저장"):
            if canvas_result.image_data is not None:
                # 서명 레이어 (RGBA)
                sign_layer = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')

                # 배경 이미지와 서명 합성
                final_combined = bg_image_resized.convert("RGBA")
                final_combined = Image.alpha_composite(final_combined, sign_layer)

                buffer = io.BytesIO()
                # 합성된 이미지를 PDF 페이지 크기로 생성
                p = canvas.Canvas(buffer, pagesize=(canvas_width, canvas_height))
                p.drawInlineImage(final_combined.convert("RGB"), 0, 0, width=canvas_width, height=canvas_height)
                p.showPage()
                p.save()

                st.success("서명이 완료되었습니다!")
                st.download_button(
                    label="📥 완성된 PDF 다운로드",
                    data=buffer.getvalue(),
                    file_name="signed_document.pdf",
                    mime="application/pdf"
                )
    else:
        st.warning("먼저 서명할 문서를 업로드해 주세요.")