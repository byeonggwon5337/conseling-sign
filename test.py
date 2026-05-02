import streamlit as st
from streamlit_drawable_canvas import st_canvas
from reportlab.pdfgen import canvas
from PIL import Image
import io

st.set_page_config(page_title="문서 위 직접 서명 시스템", layout="centered")

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
    st.title("🖋️ 문서 위 직접 서명")

    # 1. 파일 업로드
    st.subheader("1. 서명할 문서 업로드")
    bg_file = st.file_uploader("상담 양식 이미지를 업로드하세요", type=['png', 'jpg', 'jpeg'])

    if bg_file:
        # 이미지를 처리하여 세션에 저장 (매번 새로 로드하지 않도록 함)
        if 'bg_image' not in st.session_state or st.session_state.get('last_uploaded') != bg_file.name:
            img = Image.open(bg_file).convert("RGB")
            # 가로 600px 고정 비율 리사이즈
            w, h = img.size
            canvas_width = 600
            canvas_height = int(canvas_width * (h / w))
            st.session_state['bg_image'] = img.resize((canvas_width, canvas_height))
            st.session_state['canvas_h'] = canvas_height
            st.session_state['last_uploaded'] = bg_file.name

        st.subheader("2. 문서 위에 직접 작성 및 서명")

        # 2. 캔버스 그리기
        # background_image에 세션에 저장된 이미지를 직접 전달
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=2,
            stroke_color="#0000ff",
            background_image=st.session_state['bg_image'],
            update_streamlit=True,
            height=st.session_state['canvas_h'],
            width=600,
            drawing_mode="freedraw",
            key="canvas_signature",
        )

        # 3. PDF 저장 버튼
        if st.button("서명 완료 및 PDF 생성"):
            if canvas_result.image_data is not None:
                # 서명 레이어 (RGBA)
                sign_layer = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')

                # 배경 이미지 위에 서명 합성
                final_combined = st.session_state['bg_image'].convert("RGBA")
                final_combined = Image.alpha_composite(final_combined, sign_layer)

                buffer = io.BytesIO()
                # 합성된 이미지를 PDF로 변환 (RGB로 다시 변환 필요)
                p = canvas.Canvas(buffer, pagesize=(600, st.session_state['canvas_h']))
                p.drawInlineImage(final_combined.convert("RGB"), 0, 0, width=600, height=st.session_state['canvas_h'])
                p.showPage()
                p.save()

                st.success("문서가 완성되었습니다!")
                st.download_button(
                    label="📥 완성된 PDF 다운로드",
                    data=buffer.getvalue(),
                    file_name="signed_document.pdf",
                    mime="application/pdf"
                )
    else:
        st.info("먼저 상담 양식 사진을 업로드해 주세요.")