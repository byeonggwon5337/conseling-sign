import streamlit as st
from streamlit_drawable_canvas import st_canvas
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
import io, base64

st.set_page_config(page_title="서명 시스템", layout="centered")

# ── 세션 초기화 ─────────────────────────────────────────────
for k, v in {
    'logged_in': False,
    'img_bytes': None,
    'prev_file_name': None,
    'canvas_key_idx': 0,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


def pil_to_b64(pil_img: Image.Image) -> str:
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ── 로그인 ──────────────────────────────────────────────────
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

# ── 메인 ────────────────────────────────────────────────────
else:
    st.title("🖋️ 문서 위 직접 서명")

    bg_file = st.file_uploader(
        "상담 양식 이미지를 업로드하세요 (PNG / JPG)",
        type=['png', 'jpg', 'jpeg'],
    )

    # 새 파일 감지 → 세션 저장 + 캔버스 key 갱신
    if bg_file is not None and bg_file.name != st.session_state['prev_file_name']:
        st.session_state['img_bytes'] = bg_file.read()
        st.session_state['prev_file_name'] = bg_file.name
        st.session_state['canvas_key_idx'] += 1

    if st.session_state['img_bytes'] is not None:
        # ── 이미지 준비 ─────────────────────────────────────
        img = Image.open(io.BytesIO(st.session_state['img_bytes'])).convert("RGB")
        w, h = img.size
        CANVAS_W = 700
        CANVAS_H = int(CANVAS_W * h / w)
        bg_resized = img.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
        bg_b64 = pil_to_b64(bg_resized)

        st.markdown("**✏️ 문서 위에 직접 서명하세요** (마우스 또는 터치)")

        canvas_key = f"canvas_{st.session_state['canvas_key_idx']}"

        # ── st_canvas 호출 ──────────────────────────────────
        canvas_result = st_canvas(
            fill_color="rgba(0,0,0,0)",
            stroke_width=3,
            stroke_color="#0000cc",
            background_image=bg_resized,   # PIL Image → 배경
            update_streamlit=True,
            height=CANVAS_H,
            width=CANVAS_W,
            drawing_mode="freedraw",
            key=canvas_key,
        )

        # ── 배경이 안 뜨는 버그 패치: JS로 직접 주입 ────────
        # st_canvas가 내부적으로 만드는 <canvas> 배경을 JS로 강제 설정
        patch_js = f"""
<script>
(function injectBg() {{
  const b64 = "data:image/png;base64,{bg_b64}";
  const img = new Image();
  img.onload = function() {{
    // st_canvas는 fabric.js 캔버스를 씀 → lowerCanvasEl이 배경 레이어
    function trySet() {{
      const canvases = document.querySelectorAll('canvas');
      let found = false;
      canvases.forEach(cv => {{
        // 크기가 일치하는 캔버스가 배경 레이어
        if (cv.width === {CANVAS_W} && cv.height === {CANVAS_H}) {{
          const ctx = cv.getContext('2d');
          if (ctx) {{
            ctx.save();
            ctx.globalCompositeOperation = 'destination-over';
            ctx.drawImage(img, 0, 0, {CANVAS_W}, {CANVAS_H});
            ctx.restore();
            found = true;
          }}
        }}
      }});
      if (!found) setTimeout(trySet, 300);
    }}
    trySet();
  }};
  img.src = b64;

  // 매 1초마다 재주입 (rerun 후에도 유지)
  setInterval(() => {{
    const canvases = document.querySelectorAll('canvas');
    canvases.forEach(cv => {{
      if (cv.width === {CANVAS_W} && cv.height === {CANVAS_H}) {{
        const ctx = cv.getContext('2d');
        if (ctx) {{
          ctx.save();
          ctx.globalCompositeOperation = 'destination-over';
          ctx.drawImage(img, 0, 0, {CANVAS_W}, {CANVAS_H});
          ctx.restore();
        }}
      }}
    }});
  }}, 1000);
}})();
</script>
"""
        st.markdown(patch_js, unsafe_allow_html=True)

        # ── 버튼 ────────────────────────────────────────────
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🗑️ 서명 초기화"):
                st.session_state['canvas_key_idx'] += 1
                st.rerun()

        with col2:
            if st.button("✅ 서명 완료 및 PDF 생성"):
                if canvas_result.image_data is not None:
                    # 서명 레이어(RGBA) + 원본 이미지 합성
                    sign_layer = Image.fromarray(
                        canvas_result.image_data.astype('uint8'), 'RGBA'
                    )
                    final = Image.alpha_composite(
                        bg_resized.convert("RGBA"), sign_layer
                    ).convert("RGB")

                    pdf_buf = io.BytesIO()
                    c = rl_canvas.Canvas(pdf_buf, pagesize=(CANVAS_W, CANVAS_H))
                    img_buf = io.BytesIO()
                    final.save(img_buf, format="PNG")
                    img_buf.seek(0)
                    c.drawImage(ImageReader(img_buf), 0, 0,
                                width=CANVAS_W, height=CANVAS_H)
                    c.showPage()
                    c.save()

                    st.success("서명이 완료되었습니다!")
                    st.download_button(
                        "📥 PDF 다운로드",
                        data=pdf_buf.getvalue(),
                        file_name="signed_doc.pdf",
                        mime="application/pdf",
                    )
                else:
                    st.warning("먼저 캔버스에 서명해 주세요.")

    else:
        st.info("⬆️ 파일을 업로드하면 문서 위에 서명창이 나타납니다.")