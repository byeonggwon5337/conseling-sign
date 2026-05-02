import streamlit as st
from PIL import Image
import io, base64, json
from datetime import datetime

# --- 구글 라이브러리 체크 ---
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload

    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False

st.set_page_config(page_title="간편 서명 시스템", layout="centered")

# --- 로그인 로직 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False


def upload_to_gdrive(img_data, file_name, creds_json, folder_id):
    try:
        info = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(info)
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': file_name, 'parents': [folder_id] if folder_id else []}
        media = MediaIoBaseUpload(io.BytesIO(img_data), mimetype='image/png')
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return True, "성공"
    except Exception as e:
        return False, str(e)


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
                st.error("정보가 올바르지 않습니다.")
else:
    st.title("🖋️ 통합 서명 시스템")

    # --- [섹션 1] 구글 드라이브 설정 (사이드바가 아닌 창 내부에 배치) ---
    with st.expander("⚙️ 구글 드라이브 설정 (최초 1회 설정)", expanded=False):
        st.info("구글 클라우드에서 발급받은 서비스 계정 JSON 전체 내용과 폴더 ID를 입력하세요.")
        g_json = st.text_area("서비스 계정 JSON", height=200, placeholder='{"type": "service_account", ...}')
        g_folder = st.text_input("폴더 ID", placeholder="예: 1aBcDeFgHiJkLmNoPqRsTuVwXyZ")

    st.divider()

    # --- [섹션 2] 문서 업로드 및 서명 ---
    st.subheader("1️⃣ 서명하기")
    bg_file = st.file_uploader("서명할 문서(이미지)를 업로드하세요", type=['png', 'jpg', 'jpeg'])

    if bg_file:
        img_data = bg_file.read()
        img = Image.open(io.BytesIO(img_data)).convert("RGB")
        CW = 700
        CH = int(CW * img.height / img.width)

        buf = io.BytesIO()
        img.resize((CW, CH)).save(buf, format="PNG")
        bg_b64 = base64.b64encode(buf.getvalue()).decode()

        # HTML/JS 캔버스
        canvas_html = f"""
        <div style="position:relative; width:{CW}px; height:{CH}px; border:2px solid #333; margin: 0 auto;">
            <img id="bg" src="data:image/png;base64,{bg_b64}" style="position:absolute; width:100%; height:100%; user-select:none;">
            <canvas id="c" width="{CW}" height="{CH}" style="position:absolute; cursor:crosshair;"></canvas>
        </div>
        <div style="text-align: center; margin-top: 20px;">
            <button onclick="process()" style="padding:12px 24px; background:#27ae60; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">💾 서명 완료 (내 PC 저장)</button>
            <button onclick="clr()" style="padding:12px 24px; background:#e74c3c; color:white; border:none; border-radius:5px; cursor:pointer; margin-left:10px;">🗑️ 초기화</button>
        </div>
        <script>
            const v=document.getElementById('c'), x=v.getContext('2d');
            const bg=document.getElementById('bg');
            x.strokeStyle='#000000'; x.lineWidth=3;
            let d=0;
            const getPos = e => {{
                const r=v.getBoundingClientRect();
                const t=e.touches ? e.touches[0] : e;
                return [t.clientX-r.left, t.clientY-r.top];
            }};
            v.onmousedown=e=>{{d=1; [lx,ly]=getPos(e);}};
            v.onmousemove=e=>{{if(!d)return; const[nx,ny]=getPos(e); x.beginPath(); x.moveTo(lx,ly); x.lineTo(nx,ny); x.stroke(); [lx,ly]=[nx,ny];}};
            v.onmouseup=()=>d=0;
            v.ontouchstart=e=>{{d=1; [lx,ly]=getPos(e); e.preventDefault();}};
            v.ontouchmove=e=>{{if(!d)return; const[nx,ny]=getPos(e); x.beginPath(); x.moveTo(lx,ly); x.lineTo(nx,ny); x.stroke(); [lx,ly]=[nx,ny]; e.preventDefault();}};
            v.ontouchend=()=>d=0;
            function clr() {{ x.clearRect(0,0,v.width,v.height); }}
            function process() {{
                const out = document.createElement('canvas');
                out.width = v.width; out.height = v.height;
                const ctx = out.getContext('2d');
                ctx.drawImage(bg, 0, 0, out.width, out.height);
                ctx.drawImage(v, 0, 0);
                const a = document.createElement('a');
                a.href = out.toDataURL('image/png');
                a.download = 'signed_document.png';
                a.click();
            }}
        </script>
        """
        import streamlit.components.v1 as components

        components.html(canvas_html, height=CH + 100)

        st.divider()

        # --- [섹션 3] 구글 드라이브 전송 ---
        st.subheader("2️⃣ 구글 드라이브로 전송")
        final_file = st.file_uploader("위에서 다운로드한 'signed_document.png' 파일을 여기에 드래그하세요", type='png',
                                      key="final_uploader")

        if st.button("📤 전송 시작", use_container_width=True):
            if not final_file:
                st.error("전송할 파일을 업로드해주세요.")
            elif not g_json or not g_folder:
                st.error("상단의 '구글 드라이브 설정'을 완료해주세요.")
            else:
                with st.spinner("업로드 중..."):
                    fname = f"signed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    ok, msg = upload_to_gdrive(final_file.read(), fname, g_json, g_folder)
                    if ok:
                        st.success(f"성공적으로 저장되었습니다! (파일명: {fname})")
                        st.balloons()
                    else:
                        st.error(f"실패: {msg}")