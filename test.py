import streamlit as st
import streamlit.components.v1 as components
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
import io, base64, urllib.parse

st.set_page_config(page_title="서명 시스템", layout="centered")

# ── 세션 초기화 ─────────────────────────────────────────────
for k, v in {'logged_in': False, 'img_bytes': None, 'prev_file': None, 'merged_b64': None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def pil_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
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

    bg_file = st.file_uploader("상담 양식 이미지 업로드 (PNG / JPG)", type=['png','jpg','jpeg'])

    if bg_file and bg_file.name != st.session_state['prev_file']:
        st.session_state['img_bytes'] = bg_file.read()
        st.session_state['prev_file'] = bg_file.name
        st.session_state['merged_b64'] = None

    if st.session_state['img_bytes']:
        img = Image.open(io.BytesIO(st.session_state['img_bytes'])).convert("RGB")
        W, H = img.size
        CW = 700
        CH = int(CW * H / W)
        bg_resized = img.resize((CW, CH), Image.LANCZOS)
        bg_b64 = pil_to_b64(bg_resized)

        # ── 합성 결과 수신용 hidden input ───────────────────
        merged_input = st.text_input("__merged__", value="", key="merged_recv", label_visibility="collapsed")
        if merged_input.startswith("data:image"):
            st.session_state['merged_b64'] = merged_input

        # ── 순수 HTML 캔버스 (문서 위에 서명) ───────────────
        html = f"""
<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#f0f2f6;display:flex;flex-direction:column;align-items:center;padding:8px;font-family:sans-serif}}
#wrap{{position:relative;width:{CW}px;height:{CH}px;border:2px solid #4a90e2;border-radius:8px;overflow:hidden;cursor:crosshair;touch-action:none;box-shadow:0 2px 12px rgba(0,0,0,.15)}}
#bgImg{{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;user-select:none}}
#sigCanvas{{position:absolute;top:0;left:0;width:{CW}px;height:{CH}px}}
.btns{{margin-top:10px;display:flex;gap:10px}}
button{{padding:10px 22px;border:none;border-radius:6px;font-size:15px;font-weight:700;cursor:pointer}}
#btnClear{{background:#e74c3c;color:#fff}}
#btnSave{{background:#27ae60;color:#fff}}
#msg{{margin-top:8px;font-size:13px;color:#27ae60;font-weight:600;min-height:20px}}
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
const cv = document.getElementById('sigCanvas');
const ctx = cv.getContext('2d');
ctx.strokeStyle='#0000cc'; ctx.lineWidth=3; ctx.lineCap='round'; ctx.lineJoin='round';
let drawing=false, lx=0, ly=0;

function pos(e){{
  const r=cv.getBoundingClientRect();
  const sx=cv.width/r.width, sy=cv.height/r.height;
  if(e.touches) return [(e.touches[0].clientX-r.left)*sx,(e.touches[0].clientY-r.top)*sy];
  return [(e.clientX-r.left)*sx,(e.clientY-r.top)*sy];
}}
cv.addEventListener('mousedown', e=>{{drawing=true;[lx,ly]=pos(e)}});
cv.addEventListener('mousemove', e=>{{if(!drawing)return;const[x,y]=pos(e);ctx.beginPath();ctx.moveTo(lx,ly);ctx.lineTo(x,y);ctx.stroke();[lx,ly]=[x,y]}});
cv.addEventListener('mouseup',   ()=>drawing=false);
cv.addEventListener('mouseleave',()=>drawing=false);
cv.addEventListener('touchstart',e=>{{e.preventDefault();drawing=true;[lx,ly]=pos(e)}},{{passive:false}});
cv.addEventListener('touchmove', e=>{{if(!drawing)return;e.preventDefault();const[x,y]=pos(e);ctx.beginPath();ctx.moveTo(lx,ly);ctx.lineTo(x,y);ctx.stroke();[lx,ly]=[x,y]}},{{passive:false}});
cv.addEventListener('touchend',  ()=>drawing=false);

function clearSig(){{ctx.clearRect(0,0,cv.width,cv.height);document.getElementById('msg').textContent='';}}

function saveSig(){{
  const merged=document.createElement('canvas');
  merged.width={CW}; merged.height={CH};
  const mc=merged.getContext('2d');
  mc.drawImage(document.getElementById('bgImg'),0,0,{CW},{CH});
  mc.drawImage(cv,0,0);
  const dataURL=merged.toDataURL('image/png');

  // Streamlit hidden input에 값 전달
  const inputs=window.parent.document.querySelectorAll('input[type=text]');
  inputs.forEach(inp=>{{
    if(inp.value===''||inp.value.startsWith('data:image')){{
      const nativeInputValueSetter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
      nativeInputValueSetter.call(inp,dataURL);
      inp.dispatchEvent(new Event('input',{{bubbles:true}}));
    }}
  }});
  document.getElementById('msg').textContent='✅ 서명이 저장되었습니다! 아래 버튼을 눌러 PDF를 생성하세요.';
}}
</script>
</body></html>
"""
        components.html(html, height=CH + 100, scrolling=False)

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 페이지 새로고침 (초기화)"):
                st.session_state['merged_b64'] = None
                st.rerun()

        with col2:
            if st.button("📄 PDF 생성"):
                mb64 = st.session_state.get('merged_b64')
                if mb64 and mb64.startswith("data:image"):
                    raw = base64.b64decode(mb64.split(",",1)[1])
                    merged_img = Image.open(io.BytesIO(raw)).convert("RGB")
                    pdf_buf = io.BytesIO()
                    c = rl_canvas.Canvas(pdf_buf, pagesize=(CW, CH))
                    ib = io.BytesIO(); merged_img.save(ib, format="PNG"); ib.seek(0)
                    c.drawImage(ImageReader(ib), 0, 0, width=CW, height=CH)
                    c.showPage(); c.save()
                    st.success("PDF 생성 완료!")
                    st.download_button("📥 PDF 다운로드", data=pdf_buf.getvalue(),
                                       file_name="signed_doc.pdf", mime="application/pdf")
                else:
                    st.warning("캔버스에서 서명 후 '✅ 서명 저장' 버튼을 먼저 눌러주세요.")
    else:
        st.info("⬆️ 파일을 업로드하면 문서 위에 서명창이 나타납니다.")