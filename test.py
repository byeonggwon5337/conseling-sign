import streamlit as st
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
import io, base64, json
from datetime import datetime

# --- 구글 드라이브 라이브러리 체크 ---
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload

    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False

st.set_page_config(page_title="전문 서명 시스템", layout="wide")

# --- 세션 상태 초기화 ---
if 'signers' not in st.session_state:
    st.session_state['signers'] = []
if 'img_bytes' not in st.session_state:
    st.session_state['img_bytes'] = None
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False


# --- 유틸리티 함수 ---
def pil_to_b64(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def build_pdf(images):
    buf = io.BytesIO()
    W, H = images[0].size
    c = rl_canvas.Canvas(buf, pagesize=(W, H))
    for im in images:
        ib = io.BytesIO()
        im.convert("RGB").save(ib, format="PNG")
        ib.seek(0)
        c.drawImage(ImageReader(ib), 0, 0, width=W, height=H)
        c.showPage()
    c.save()
    return buf.getvalue()


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
                st.error("로그인 정보가 틀립니다.")

else:
    st.title("🖋️ 다중 서명 시스템")

    # 사이드바: 설정 및 현황
    with st.sidebar:
        st.header("⚙️ 구글 드라이브 설정")
        gdrive_json = st.text_area("서비스 계정 JSON", height=100)
        gdrive_folder = st.text_input("폴더 ID")
        st.divider()
        st.header("📋 서명 목록")
        for i, s in enumerate(st.session_state['signers']):
            st.write(f"{i + 1}. {s['name']} ✅")
        if st.button("전체 초기화"):
            st.session_state['signers'] = []
            st.rerun()

    tab1, tab2 = st.tabs(["✍️ 서명 하기", "📁 PDF 생성/업로드"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            bg_file = st.file_uploader("📄 문서 이미지 업로드", type=['png', 'jpg', 'jpeg'])
            if bg_file:
                st.session_state['img_bytes'] = bg_file.read()
        with c2:
            signer_name = st.text_input("✏️ 서명자 이름")

        if st.session_state['img_bytes']:
            # 이미지 처리
            img = Image.open(io.BytesIO(st.session_state['img_bytes'])).convert("RGB")
            CW = 700
            CH = int(CW * img.height / img.width)
            base_img = img.resize((CW, CH), Image.LANCZOS)

            # 기존 서명 누적 합성
            combined = base_img.convert("RGBA")
            for s in st.session_state['signers']:
                prev_sig = Image.open(io.BytesIO(base64.b64decode(s['sig_b64']))).convert("RGBA")
                combined = Image.alpha_composite(combined, prev_sig.resize((CW, CH)))

            st.info("1. 아래 캔버스에 서명 후 [저장] 하세요. 2. 다운로드된 파일을 아래 업로드함에 넣으세요.")

            # --- HTML 캔버스 ---
            bg_b64 = pil_to_b64(combined.convert("RGB"))
            canvas_html = f"""
            <div style="position:relative; width:{CW}px; height:{CH}px; border:2px solid #000;">
                <img src="data:image/png;base64,{bg_b64}" style="position:absolute; width:100%; height:100%;">
                <canvas id="c" width="{CW}" height="{CH}" style="position:absolute; cursor:crosshair;"></canvas>
            </div>
            <br>
            <button onclick="save()" style="padding:10px; background:#27ae60; color:white; border:none; border-radius:5px;">💾 서명 이미지 저장 (signature.png)</button>
            <button onclick="clr()" style="padding:10px; background:#e74c3c; color:white; border:none; border-radius:5px;">🗑️ 초기화</button>
            <script>
                const v=document.getElementById('c'), x=v.getContext('2d');
                x.strokeStyle='#ff0000'; x.lineWidth=3;
                let d=0;
                const getP = e => {{
                    const r=v.getBoundingClientRect();
                    const t=e.touches?e.touches[0]:e;
                    return [t.clientX-r.left, t.clientY-r.top];
                }};
                v.onmousedown=e=>{{d=1; [lx,ly]=getP(e);}};
                v.onmousemove=e=>{{if(!d)return; const[nx,ny]=getP(e); x.beginPath(); x.moveTo(lx,ly); x.lineTo(nx,ny); x.stroke(); [lx,ly]=[nx,ny];}};
                v.onmouseup=()=>d=0;
                v.ontouchstart=e=>{{d=1; [lx,ly]=getP(e); e.preventDefault();}};
                v.ontouchmove=e=>{{if(!d)return; const[nx,ny]=getP(e); x.beginPath(); x.moveTo(lx,ly); x.lineTo(nx,ny); x.stroke(); [lx,ly]=[nx,ny]; e.preventDefault();}};
                v.ontouchend=()=>d=0;
                function clr() {{ x.clearRect(0,0,v.width,v.height); }}
                function save() {{
                    const a=document.createElement('a');
                    a.href=v.toDataURL('image/png');
                    a.download='signature.png'; a.click();
                }}
            </script>
            """
            import streamlit.components.v1 as components

            components.html(canvas_html, height=CH + 100)

            st.divider()
            # 서명 파일 다시 받기
            sig_upload = st.file_uploader("📎 방금 저장한 signature.png를 여기에 업로드", type='png')
            if sig_upload and st.button("➕ 서명 목록에 추가"):
                if signer_name:
                    sig_b64 = base64.b64encode(sig_upload.read()).decode()
                    st.session_state['signers'].append({'name': signer_name, 'sig_b64': sig_b64})
                    st.success(f"{signer_name}님 추가 완료!")
                    st.rerun()
                else:
                    st.warning("이름을 입력하세요.")

    with tab2:
        if st.session_state['signers']:
            if st.button("📄 최종 PDF 생성"):
                img = Image.open(io.BytesIO(st.session_state['img_bytes'])).convert("RGBA")
                acc = img.copy()
                for s in st.session_state['signers']:
                    sig = Image.open(io.BytesIO(base64.b64decode(s['sig_b64']))).convert("RGBA")
                    acc = Image.alpha_composite(acc, sig.resize(img.size))

                pdf_data = build_pdf([acc])
                st.session_state['final_pdf'] = pdf_data
                st.download_button("📥 PDF 다운로드", pdf_data, file_name="final_signed.pdf")
        else:
            st.info("서명된 내역이 없습니다.")