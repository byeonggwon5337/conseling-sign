import streamlit as st
from streamlit_drawable_canvas import st_canvas
from reportlab.pdfgen import canvas
from PIL import Image
import io

st.set_page_config(page_title="서명 시스템", layout="centered")

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
    bg_file = st.file_uploader("상담 양식 이미지를 업로드하세요", type=['png', 'jpg', 'jpeg'], key="file_uploader")

    if bg_file:
        # 이미지 로드 (캐싱 없이 즉시 처리)
        img = Image.open(bg_file).convert("RGB")

        # 가로 600px 기준 비율 조정
        w, h = img.size
        canvas_width = 600
        canvas_height = int(canvas_width * (h / w))
        bg_image_resized = img.resize((canvas_width, canvas_height))

        st.write("---")
        st.subheader("아래 문서 위에 서명해 주세요")

        # 2. 캔버스 (가장 안정적인 설정)
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=3,
            stroke_color="#0000ff",
            background_image=bg_image_resized,
            update_streamlit=True,
            height=canvas_height,
            width=canvas_width,
            drawing_mode="freedraw",
            key="canvas_main",
        )

        # 3. PDF 저장
        if st.button("서명 완료 및 PDF 생성"):
            if canvas_result.image_data is not None:
                sign_layer = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                final_combined = bg_image_resized.convert("RGBA")
                final_combined = Image.alpha_composite(final_combined, sign_layer)

                buffer = io.BytesIO()
                p = canvas.Canvas(buffer, pagesize=(canvas_width, canvas_height))
                p.drawInlineImage(final_combined.convert("RGB"), 0, 0, width=canvas_width, height=canvas_height)
                p.showPage()
                p.save()

                st.success("완성되었습니다!")
                st.download_button(
                    label="📥 PDF 다운로드",
                    data=buffer.getvalue(),
                    file_name="signed_doc.pdf",
                    mime="application/pdf"
                )
    else:
        st.info("파일을 업로드하면 아래에 서명창이 나타납니다.")