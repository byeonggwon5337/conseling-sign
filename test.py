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

# --- 세션 상태 초기화 (이미지 고정용) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'active_img' not in st.session_state:
    st.session_state['active_img'] = None


# --- 구글 드라이브 업로드 함수 ---
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


# --- 로그인 로직 ---
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
    st.title("🖋️ 단일 서명 시스템")

    with st.sidebar:
        st.header("⚙️ 드라이브 설정")
        g_json = st.text_area("서비스 계정 JSON", height=150)
        g_folder = st.text_input("폴더 ID (URL 뒷부분)")
        if st.button("처음부터 다시 시작 (이미지 삭제)"):
            st.session_state['active_img'] = None
            st.rerun()

    # 1. 파일 업로드 (업로드 즉시 세션에 저장)
    bg_file = st.file_uploader("📄 문서 이미지 업로드", type=['png', 'jpg', 'jpeg'])
    if bg_file:
        st.session_state['active_img'] = bg_file.read()

    signer_name = st.text_input("✏️ 서명자 이름")

    # 세션에 이미지가 있을 때만 캔버스 표시
    if st.session_state['active_img'] and signer_name:
        img = Image.open(io.BytesIO(st.session_state['active_img'])).convert("RGB")
        CW = 700
        CH = int(CW * img.height / img.width)

        # 배경 이미지 base64 변환
        buf = io.BytesIO()
        img.resize((CW, CH)).save(buf, format="PNG")
        bg_b64 = base64.b64encode(buf.getvalue()).decode()

        st.info("검정색으로 서명한 후 [서명 완료] 버튼을 눌러주세요.")

        # --- HTML/JS 캔버스 ---
        canvas_html = f"""
        <div style="position:relative; width:{CW}px; height:{CH}px; border:2px solid #000;">
            <img id="bg" src="data:image/png;base64,{bg_b64}" style="position:absolute; width:100%; height:100%; user-select:none;">
            <canvas id="c" width="{CW}" height="{CH}" style="position:absolute; cursor:crosshair;"></canvas>
        </div>
        <br>
        <button onclick="process()" style="padding:12px 24px; background:#27ae60; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">✅ 서명 완료 (파일 다운로드)</button>
        <button onclick="clr()" style="padding:12px 24px; background:#e74c3c; color:white; border:none; border-radius:5px; cursor:pointer; margin-left:10px;">🗑️ 초기화</button>

        <script>
            const v=document.getElementById('c'), x=v.getContext('2d');
            const bg=document.getElementById('bg');
            x.strokeStyle='#000000'; // 검정색 서명
            x.lineWidth=3;
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
                a.download = '{signer_name}_signed.png';
                a.click();
            }}
        </script>
        """
        import streamlit.components.v1 as components

        components.html(canvas_html, height=CH + 150)

        st.divider()
        final_file = st.file_uploader("📥 다운로드된 파일을 여기에 드롭하세요", type='png')

        if final_file and g_json and g_folder:
            if st.button("🚀 구글 드라이브에 최종 저장"):
                with st.spinner("저장 중..."):
                    fname = f"{signer_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    ok, msg = upload_to_gdrive(final_file.read(), fname, g_json, g_folder)
                    if ok:
                        st.success(f"저장 성공! (파일명: {fname})")
                    else:
                        st.error(f"저장 실패: {msg}")