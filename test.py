import streamlit as st
from streamlit_drawable_canvas import st_canvas
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
import io
import base64

st.set_page_config(page_title="서명 시스템", layout="centered")

# ── 세션 초기화 ──────────────────────────────────────────────
for k, v in {
    'logged_in': False,
    'img_bytes': None,
    'canvas_key': "canvas_0",
    'prev_file_name': None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


def pil_to_base64(pil_img: Image.Image) -> str:
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ── 로그인 화면 ──────────────────────────────────────────────
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
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

# ── 메인 화면 ────────────────────────────────────────────────
else:
    st.title("🖋️ 문서 위 직접 서명")

    bg_file = st.file_uploader(
        "상담 양식 이미지를 업로드하세요 (PNG / JPG)",
        type=['png', 'jpg', 'jpeg'],
    )

    # 새 파일이 올라왔을 때만 세션 갱신
    if bg_file is not None:
        if bg_file.name != st.session_state['prev_file_name']:
            st.session_state['img_bytes'] = bg_file.read()
            st.session_state['prev_file_name'] = bg_file.name
            idx = int(st.session_state['canvas_key'].split("_")[1])
            st.session_state['canvas_key'] = f"canvas_{idx + 1}"

    # ── 이미지가 세션에 있으면 캔버스 표시 ───────────────────
    if st.session_state['img_bytes'] is not None:
        img = Image.open(io.BytesIO(st.session_state['img_bytes'])).convert("RGB")
        w, h = img.size
        canvas_width = 680
        canvas_height = int(canvas_width * h / w)
        bg_resized = img.resize((canvas_width, canvas_height), Image.LANCZOS)

        # ── 업로드된 이미지를 HTML로 미리보기 출력 ──────────
        b64 = pil_to_base64(bg_resized)
        st.markdown(
            f"""
            <div style="margin-bottom:6px; font-weight:600; color:#333;">
                📄 업로드된 문서 미리보기
            </div>
            <img src="data:image/png;base64,{b64}"
                 style="width:{canvas_width}px; border:1px solid #ccc;
                        border-radius:6px; display:block;" />
            """,
            unsafe_allow_html=True,
        )

        st.write("---")
        st.subheader("아래 캔버스에 서명해 주세요")
        st.caption("파란 선으로 서명이 그려집니다. 마우스 또는 터치로 서명하세요.")

        # ── 캔버스: background_image에 PIL Image 전달 ────────
        canvas_result = st_canvas(
            fill_color="rgba(0,0,0,0)",
            stroke_width=3,
            stroke_color="#0000ff",
            background_image=bg_resized,
            update_streamlit=True,
            height=canvas_height,
            width=canvas_width,
            drawing_mode="freedraw",
            key=st.session_state['canvas_key'],
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🗑️ 서명 초기화"):
                idx = int(st.session_state['canvas_key'].split("_")[1])
                st.session_state['canvas_key'] = f"canvas_{idx + 1}"
                st.rerun()

        with col2:
            if st.button("✅ 서명 완료 및 PDF 생성"):
                if canvas_result.image_data is not None:
                    sign_layer = Image.fromarray(
                        canvas_result.image_data.astype('uint8'), 'RGBA'
                    )
                    final = Image.alpha_composite(
                        bg_resized.convert("RGBA"), sign_layer
                    ).convert("RGB")

                    pdf_buf = io.BytesIO()
                    c = rl_canvas.Canvas(
                        pdf_buf, pagesize=(canvas_width, canvas_height)
                    )
                    img_buf = io.BytesIO()
                    final.save(img_buf, format="PNG")
                    img_buf.seek(0)
                    c.drawImage(
                        ImageReader(img_buf), 0, 0,
                        width=canvas_width, height=canvas_height,
                    )
                    c.showPage()
                    c.save()

                    st.success("서명이 완료되었습니다! 아래에서 PDF를 다운로드하세요.")
                    st.download_button(
                        label="📥 PDF 다운로드",
                        data=pdf_buf.getvalue(),
                        file_name="signed_doc.pdf",
                        mime="application/pdf",
                    )
                else:
                    st.warning("서명 데이터가 없습니다. 먼저 서명해 주세요.")

    else:
        st.info("⬆️ 파일을 업로드하면 아래에 문서와 서명창이 나타납니다.")