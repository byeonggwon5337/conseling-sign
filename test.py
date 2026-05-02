import streamlit as st
from streamlit_drawable_canvas import st_canvas
from reportlab.pdfgen import canvas as rl_canvas
from PIL import Image
import io
import base64

st.set_page_config(page_title="서명 시스템", layout="centered")

# ── 세션 초기화 ──────────────────────────────────────────────
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'img_bytes' not in st.session_state:
    st.session_state['img_bytes'] = None
if 'canvas_key' not in st.session_state:
    st.session_state['canvas_key'] = "canvas_0"

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

    # 1. 파일 업로드
    bg_file = st.file_uploader(
        "상담 양식 이미지를 업로드하세요 (PNG / JPG)",
        type=['png', 'jpg', 'jpeg'],
        key="file_uploader"
    )

    # 파일이 새로 업로드되면 세션에 bytes 저장 + canvas key 갱신
    if bg_file is not None:
        new_bytes = bg_file.read()
        if new_bytes != st.session_state['img_bytes']:
            st.session_state['img_bytes'] = new_bytes
            # key를 바꿔야 캔버스가 완전히 새로 마운트됨
            idx = int(st.session_state['canvas_key'].split("_")[1])
            st.session_state['canvas_key'] = f"canvas_{idx + 1}"
            st.rerun()

    # 세션에 이미지가 있을 때만 캔버스 표시
    if st.session_state['img_bytes'] is not None:
        # ── 이미지 준비 ──────────────────────────────────────
        img = Image.open(io.BytesIO(st.session_state['img_bytes'])).convert("RGB")
        w, h = img.size
        canvas_width = 600
        canvas_height = int(canvas_width * h / w)
        bg_resized = img.resize((canvas_width, canvas_height))

        st.write("---")
        st.subheader("아래 문서 위에 서명해 주세요")
        st.caption("마우스 또는 터치로 서명하세요.")

        # ── 캔버스 ───────────────────────────────────────────
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.0)",
            stroke_width=3,
            stroke_color="#0000ff",
            background_image=bg_resized,          # PIL Image
            update_streamlit=True,
            height=canvas_height,
            width=canvas_width,
            drawing_mode="freedraw",
            key=st.session_state['canvas_key'],   # 파일 바뀔 때마다 새 key
        )

        # ── PDF 생성 ─────────────────────────────────────────
        if st.button("✅ 서명 완료 및 PDF 생성"):
            if canvas_result.image_data is not None:
                sign_layer = Image.fromarray(
                    canvas_result.image_data.astype('uint8'), 'RGBA'
                )
                final = Image.alpha_composite(
                    bg_resized.convert("RGBA"), sign_layer
                ).convert("RGB")

                pdf_buf = io.BytesIO()
                c = rl_canvas.Canvas(pdf_buf, pagesize=(canvas_width, canvas_height))

                # reportlab에 이미지를 넘기려면 임시 BytesIO 필요
                img_buf = io.BytesIO()
                final.save(img_buf, format="PNG")
                img_buf.seek(0)

                from reportlab.lib.utils import ImageReader
                c.drawImage(
                    ImageReader(img_buf),
                    0, 0,
                    width=canvas_width,
                    height=canvas_height,
                )
                c.showPage()
                c.save()

                st.success("서명이 완료되었습니다!")
                st.download_button(
                    label="📥 PDF 다운로드",
                    data=pdf_buf.getvalue(),
                    file_name="signed_doc.pdf",
                    mime="application/pdf",
                )
            else:
                st.warning("서명 데이터가 없습니다. 먼저 서명해 주세요.")

        # ── 초기화 버튼 ──────────────────────────────────────
        if st.button("🗑️ 서명 초기화"):
            idx = int(st.session_state['canvas_key'].split("_")[1])
            st.session_state['canvas_key'] = f"canvas_{idx + 1}"
            st.rerun()

    else:
        st.info("⬆️ 파일을 업로드하면 서명창이 나타납니다.")