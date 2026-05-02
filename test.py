import streamlit as st
import streamlit.components.v1 as components
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
import io, base64, json
from datetime import datetime

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False

st.set_page_config(page_title="서명 시스템", layout="wide")

for k, v in {
    'logged_in': False,
    'img_bytes': None,
    'prev_file': None,
    'signers': [],
    'final_pdf': None,
    'sig_b64': None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def pil_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def b64_to_pil(b64str: str) -> Image.Image:
    raw = base64.b64decode(b64str.split(",", 1)[1])
    return Image.open(io.BytesIO(raw)).convert("RGBA")

def build_pdf(images: list) -> bytes:
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

def upload_to_gdrive(pdf_bytes, filename, folder_id, creds_dict):
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/drive"])
    service = build("drive", "v3", credentials=creds)
    meta = {"name": filename}
    if folder_id:
        meta["parents"] = [folder_id]
    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf")
    f = service.files().create(body=meta, media_body=media, fields="id").execute()
    service.permissions().create(fileId=f["id"], body={"type":"anyone","role":"reader"}).execute()
    return f"https://drive.google.com/file/d/{f['id']}/view"

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

else:
    st.title("🖋️ 다중 서명 시스템")

    # ── URL query param으로 서명 데이터 수신 ────────────────
    params = st.query_params
    if "sig" in params:
        st.session_state['sig_b64'] = params["sig"]
        st.query_params.clear()
        st.rerun()

    # ── 사이드바 ─────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ 구글 드라이브 설정")
        st.markdown("""
1. [Google Cloud Console](https://console.cloud.google.com) → 서비스 계정 생성  
2. JSON 키 다운로드  
3. 드라이브 폴더를 서비스 계정 이메일에 공유  
4. 아래에 JSON 붙여넣기
""")
        gdrive_json   = st.text_area("서비스 계정 JSON", height=120, placeholder='{"type":"service_account",...}')
        gdrive_folder = st.text_input("드라이브 폴더 ID", placeholder="folders/ 뒤 ID")

        st.divider()
        st.header("📋 서명 현황")
        if st.session_state['signers']:
            for i, s in enumerate(st.session_state['signers']):
                c1, c2 = st.columns([3,1])
                c1.markdown(f"✅ **{i+1}. {s['name']}**")
                if c2.button("삭제", key=f"del_{i}"):
                    st.session_state['signers'].pop(i)
                    st.rerun()
            if st.button("🗑️ 전체 초기화", use_container_width=True):
                st.session_state['signers'] = []
                st.session_state['final_pdf'] = None
                st.rerun()
        else:
            st.info("아직 서명 없음")

    tab1, tab2 = st.tabs(["✍️ 서명 받기", "📁 최종 PDF & 드라이브 업로드"])

    # ════════════════════════════════════════════════
    # TAB 1: 서명 받기
    # ════════════════════════════════════════════════
    with tab1:
        col_l, col_r = st.columns([1,1])
        with col_l:
            bg_file = st.file_uploader("📄 문서 이미지 업로드 (PNG/JPG)", type=['png','jpg','jpeg'])
            if bg_file and bg_file.name != st.session_state['prev_file']:
                st.session_state['img_bytes'] = bg_file.read()
                st.session_state['prev_file'] = bg_file.name
                st.session_state['sig_b64'] = None
        with col_r:
            signer_name = st.text_input("✏️ 서명자 이름", placeholder="예: 홍길동")
            if st.session_state['signers']:
                st.markdown("**서명 완료:**")
                for s in st.session_state['signers']:
                    st.markdown(f"- ✅ {s['name']}")

        if st.session_state['img_bytes']:
            img = Image.open(io.BytesIO(st.session_state['img_bytes'])).convert("RGB")
            CW, CH = 750, int(750 * img.height / img.width)
            base_img = img.resize((CW, CH), Image.LANCZOS)

            # 기존 서명 레이어 합성해서 캔버스 배경으로
            bg = base_img.convert("RGBA")
            for s in st.session_state['signers']:
                layer = b64_to_pil(s['sig_b64']).resize((CW, CH), Image.LANCZOS)
                bg = Image.alpha_composite(bg, layer)
            bg_b64 = pil_to_b64(bg.convert("RGB"))

            # ── 서명 저장 완료 표시 ──────────────────────────
            if st.session_state['sig_b64']:
                st.success("✅ 서명이 저장되었습니다! 아래에서 서명자 이름 확인 후 [서명 목록에 추가]를 누르세요.")

            # ── HTML 캔버스: 저장 버튼이 query_param으로 전달 ─
            origin = "http://localhost:8501"   # 실서버면 본인 URL로 변경
            html = f"""
<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#f0f2f6;display:flex;flex-direction:column;align-items:center;padding:8px;font-family:sans-serif}}
#wrap{{position:relative;width:{CW}px;height:{CH}px;border:2px solid #4a90e2;border-radius:8px;overflow:hidden;cursor:crosshair;touch-action:none;box-shadow:0 2px 12px rgba(0,0,0,.2)}}
#bgImg{{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none}}
#sigCanvas{{position:absolute;top:0;left:0;width:{CW}px;height:{CH}px}}
.btns{{margin-top:10px;display:flex;gap:10px;flex-wrap:wrap;justify-content:center}}
button{{padding:11px 24px;border:none;border-radius:6px;font-size:15px;font-weight:700;cursor:pointer;transition:opacity .15s}}
button:hover{{opacity:.85}}
#btnClear{{background:#e74c3c;color:#fff}}
#btnSave{{background:#27ae60;color:#fff;font-size:16px}}
#msg{{margin-top:10px;font-size:14px;font-weight:600;min-height:22px;text-align:center}}
</style></head><body>
<div id="wrap">
  <img id="bgImg" src="data:image/png;base64,{bg_b64}" draggable="false"/>
  <canvas id="sigCanvas" width="{CW}" height="{CH}"></canvas>
</div>
<div class="btns">
  <button id="btnClear" onclick="clearSig()">🗑️ 초기화</button>
  <button id="btnSave"  onclick="saveSig()">✅ 서명 저장</button>
</div>
<div id="msg"></div>
<script>
const cv=document.getElementById('sigCanvas');
const ctx=cv.getContext('2d');
ctx.strokeStyle='#cc0000';ctx.lineWidth=3;ctx.lineCap='round';ctx.lineJoin='round';
let drawing=false,lx=0,ly=0;
function pos(e){{
  const r=cv.getBoundingClientRect(),sx=cv.width/r.width,sy=cv.height/r.height;
  if(e.touches)return[(e.touches[0].clientX-r.left)*sx,(e.touches[0].clientY-r.top)*sy];
  return[(e.clientX-r.left)*sx,(e.clientY-r.top)*sy];
}}
cv.addEventListener('mousedown',e=>{{drawing=true;[lx,ly]=pos(e)}});
cv.addEventListener('mousemove',e=>{{if(!drawing)return;const[x,y]=pos(e);ctx.beginPath();ctx.moveTo(lx,ly);ctx.lineTo(x,y);ctx.stroke();[lx,ly]=[x,y]}});
cv.addEventListener('mouseup',()=>drawing=false);
cv.addEventListener('mouseleave',()=>drawing=false);
cv.addEventListener('touchstart',e=>{{e.preventDefault();drawing=true;[lx,ly]=pos(e)}},{{passive:false}});
cv.addEventListener('touchmove',e=>{{if(!drawing)return;e.preventDefault();const[x,y]=pos(e);ctx.beginPath();ctx.moveTo(lx,ly);ctx.lineTo(x,y);ctx.stroke();[lx,ly]=[x,y]}},{{passive:false}});
cv.addEventListener('touchend',()=>drawing=false);
function clearSig(){{ctx.clearRect(0,0,cv.width,cv.height);msg('서명이 초기화되었습니다.','#888')}}
function msg(t,c){{const m=document.getElementById('msg');m.textContent=t;m.style.color=c}}
function saveSig(){{
  msg('저장 중...','#f39c12');
  const sigOnly=cv.toDataURL('image/png');
  // query param으로 Streamlit에 전달 (가장 안정적인 방법)
  const encoded=encodeURIComponent(sigOnly);
  window.parent.location.href=window.parent.location.pathname+'?sig='+encoded;
}}
</script>
</body></html>
"""
            components.html(html, height=CH+110, scrolling=False)

            st.markdown("---")

            # ── 서명 목록에 추가 버튼 ───────────────────────
            if st.button("➕ 서명 목록에 추가", type="primary", use_container_width=True):
                if not signer_name.strip():
                    st.warning("서명자 이름을 입력해주세요.")
                elif not st.session_state['sig_b64']:
                    st.warning("먼저 캔버스에 서명 후 '✅ 서명 저장'을 눌러주세요.")
                else:
                    st.session_state['signers'].append({
                        'name': signer_name.strip(),
                        'sig_b64': st.session_state['sig_b64'],
                    })
                    st.session_state['sig_b64'] = None
                    st.success(f"✅ {signer_name} 서명 추가 완료! (총 {len(st.session_state['signers'])}명)")
                    st.rerun()
        else:
            st.info("⬆️ 문서 이미지를 업로드하면 서명창이 나타납니다.")

    # ════════════════════════════════════════════════
    # TAB 2: 최종 PDF & 드라이브 업로드
    # ════════════════════════════════════════════════
    with tab2:
        st.subheader("📁 최종 PDF 생성")

        if not st.session_state['signers']:
            st.info("Tab 1에서 먼저 서명을 받아주세요.")
        elif not st.session_state['img_bytes']:
            st.warning("문서 이미지가 없습니다. Tab 1에서 업로드해주세요.")
        else:
            st.markdown(f"**서명 완료 인원: {len(st.session_state['signers'])}명**")
            for i, s in enumerate(st.session_state['signers']):
                st.markdown(f"  {i+1}. ✅ {s['name']}")

            mode = st.radio(
                "PDF 구성 방식",
                ["한 페이지에 모든 서명 합치기", "서명자별 개별 페이지 (멀티페이지 PDF)"],
                horizontal=True,
            )

            if st.button("📄 최종 PDF 생성", type="primary", use_container_width=True):
                img_orig = Image.open(io.BytesIO(st.session_state['img_bytes'])).convert("RGB")
                CW, CH = 750, int(750 * img_orig.height / img_orig.width)
                base = img_orig.resize((CW, CH), Image.LANCZOS).convert("RGBA")

                if mode == "한 페이지에 모든 서명 합치기":
                    combined = base.copy()
                    for s in st.session_state['signers']:
                        layer = b64_to_pil(s['sig_b64']).resize((CW, CH), Image.LANCZOS)
                        combined = Image.alpha_composite(combined, layer)
                    pages = [combined]
                else:
                    pages, acc = [], base.copy()
                    for s in st.session_state['signers']:
                        layer = b64_to_pil(s['sig_b64']).resize((CW, CH), Image.LANCZOS)
                        acc = Image.alpha_composite(acc, layer)
                        pages.append(acc.copy())

                pdf_bytes = build_pdf(pages)
                st.session_state['final_pdf'] = pdf_bytes
                fname = f"signed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                st.success("✅ PDF 생성 완료!")
                st.download_button("📥 PDF 다운로드", data=pdf_bytes,
                                   file_name=fname, mime="application/pdf",
                                   use_container_width=True)

            st.divider()
            st.subheader("☁️ 구글 드라이브 업로드")

            if not GDRIVE_AVAILABLE:
                st.error("패키지 설치 필요:\n```\npip install google-api-python-client google-auth\n```")
            elif not st.session_state.get('final_pdf'):
                st.info("위에서 먼저 PDF를 생성해주세요.")
            elif not gdrive_json.strip():
                st.warning("사이드바에 서비스 계정 JSON을 입력해주세요.")
            else:
                if st.button("☁️ 구글 드라이브에 업로드", use_container_width=True):
                    try:
                        creds_dict = json.loads(gdrive_json)
                        fname = f"signed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        link = upload_to_gdrive(
                            st.session_state['final_pdf'], fname,
                            gdrive_folder.strip() or None, creds_dict)
                        st.success("✅ 업로드 완료!")
                        st.markdown(f"**🔗 링크:** [{fname}]({link})")
                        st.code(link)
                    except json.JSONDecodeError:
                        st.error("JSON 형식이 올바르지 않습니다.")
                    except Exception as e:
                        st.error(f"업로드 실패: {e}")