import streamlit as st
import os
import base64
import json
from streamlit.components.v1 import html
import hashlib
from urllib.parse import unquote, quote

PORT = int(os.environ.get("PORT", 8501))

st.set_page_config(page_title="𝄞 sing-along", layout="wide")

# --------- CONFIG: set your deployed app URL here ----------
APP_URL = "https://karaoke-song.onrender.com/"

# 🔒 SECURITY: Environment Variables for Password Hashes
ADMIN_HASH = os.getenv("ADMIN_HASH", "")
USER1_HASH = os.getenv("USER1_HASH", "")
USER2_HASH = os.getenv("USER2_HASH", "")

# Base directories
base_dir = os.getcwd()
media_dir = os.path.join(base_dir, "media")
songs_dir = os.path.join(media_dir, "songs")
lyrics_dir = os.path.join(media_dir, "lyrics_images")
logo_dir = os.path.join(media_dir, "logo")
shared_links_dir = os.path.join(media_dir, "shared_links")
metadata_path = os.path.join(media_dir, "song_metadata.json")

os.makedirs(songs_dir, exist_ok=True)
os.makedirs(lyrics_dir, exist_ok=True)
os.makedirs(logo_dir, exist_ok=True)
os.makedirs(shared_links_dir, exist_ok=True)

# Helper functions
def file_to_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_metadata():
    if os.path.exists(metadata_path):
        with open(metadata_path, "r") as f:
            return json.load(f)
    return {}

def save_metadata(data):
    with open(metadata_path, "w") as f:
        json.dump(data, f, indent=2)

def load_shared_links():
    links = {}
    if not os.path.exists(shared_links_dir):
        return links
    for filename in os.listdir(shared_links_dir):
        if filename.endswith('.json'):
            song_name = filename[:-5]
            filepath = os.path.join(shared_links_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    if data.get("active", True):
                        links[song_name] = data
            except:
                links[song_name] = {}
    return links

def save_shared_link(song_name, link_data):
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    with open(filepath, 'w') as f:
        json.dump(link_data, f)

def delete_shared_link(song_name):
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)

# Get songs function - filters based on shared status for users
def get_uploaded_songs(show_unshared=False):
    songs = []
    if not os.path.exists(songs_dir):
        return songs

    shared_links = load_shared_links()

    for f in os.listdir(songs_dir):
        if f.endswith("_original.mp3"):
            song_name = f.replace("_original.mp3", "")
            if show_unshared or song_name in shared_links:
                songs.append(song_name)
    return sorted(songs)

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "page" not in st.session_state:
    st.session_state.page = "Login"

metadata = load_metadata()

# Logo
default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
if not os.path.exists(default_logo_path):
    logo_upload = st.file_uploader("Upload Logo (PNG) (optional)", type=["png"], key="logo_upload")
    if logo_upload:
        with open(default_logo_path, "wb") as f:
            f.write(logo_upload.getbuffer())
        st.rerun()
logo_b64 = file_to_base64(default_logo_path)

# =============== RESPONSIVE LOGIN PAGE ===============
if st.session_state.page == "Login":

    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    header {visibility:hidden;}

    body {
        background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%);
    }

    /* INNER CONTENT PADDING - Reduced since box has padding now */
    .login-content {
        padding: 1.8rem 2.2rem 2.2rem 2.2rem; /* Top padding reduced */
    }

    /* CENTERED HEADER SECTION */
    .login-header {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.8rem; /* Slightly more gap */
        margin-bottom: 1.6rem; /* More bottom margin */
        text-align: center;
    }

    .login-header img {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        border: 2px solid rgba(255,255,255,0.4);
    }

    .login-title {
        font-size: 1.6rem;
        font-weight: 700;
        width: 100%;
    }

    .login-sub {
        font-size: 0.9rem;
        color: #c3cfdd;
        margin-bottom: 0.5rem;
        width: 100%;
    }

    /* CREDENTIALS INFO */
    .credentials-info {
        background: rgba(5,10,25,0.8);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 10px;
        padding: 12px;
        margin-top: 16px;
        font-size: 0.85rem;
        color: #b5c2d2;
    }

    /* INPUTS BLEND WITH BOX */
    .stTextInput input {
        background: rgba(5,10,25,0.7) !important;
        border-radius: 10px !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        padding: 12px 14px !important; /* Better input padding */
    }

    .stTextInput input:focus {
        border-color: rgba(255,255,255,0.6) !important;
        box-shadow: 0 0 0 1px rgba(255,255,255,0.3);
    }

    .stButton button {
        width: 100%;
        height: 44px; /* Slightly taller */
        background: linear-gradient(to right, #1f2937, #020712);
        border-radius: 10px; /* Match input radius */
        font-weight: 600;
        margin-top: 0.6rem;
        color: white;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

    # -------- CENTER ALIGN COLUMN --------
    left, center, right = st.columns([1, 1.5, 1])

    with center:
        st.markdown('<div class="login-content">', unsafe_allow_html=True)

        # Header with better spacing
        st.markdown(f"""
        <div class="login-header">
            <img src="data:image/png;base64,{logo_b64}">
            <div class="login-title">𝄞 Karaoke Reels</div>
            <div class="login-sub">Login to continue</div>
        </div>
        """, unsafe_allow_html=True)

        username = st.text_input("Email / Username", placeholder="admin / user1 / user2", value="")
        password = st.text_input("Password", type="password", placeholder="Enter password", value="")

        if st.button("Login"):
            if not username or not password:
                st.error("❌ Enter both username and password")
            else:
                hashed_pass = hash_password(password)
                if username == "admin" and ADMIN_HASH and hashed_pass == ADMIN_HASH:
                    st.session_state.user = username
                    st.session_state.role = "admin"
                    st.session_state.page = "Admin Dashboard"
                    st.rerun()
                elif username == "user1" and USER1_HASH and hashed_pass == USER1_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    st.rerun()
                elif username == "user2" and USER2_HASH and hashed_pass == USER2_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")

        st.markdown("""
        <div style="margin-top:16px;font-size:0.8rem;color:#b5c2d2;text-align:center;padding-bottom:8px;">
            Don't have access? Contact admin.
        </div>
        """, unsafe_allow_html=True)

        st.markdown('</div></div>', unsafe_allow_html=True)

# =============== ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    st.title(f"👑 Admin Dashboard - {st.session_state.user}")

    page_sidebar = st.sidebar.radio("Navigate", ["Upload Songs", "Songs List", "Share Links"])

    if page_sidebar == "Upload Songs":
        st.subheader("📤 Upload New Song")
        col1, col2, col3 = st.columns(3)
        with col1:
            uploaded_original = st.file_uploader("Original Song (_original.mp3)", type=["mp3"], key="original_upload")
        with col2:
            uploaded_accompaniment = st.file_uploader("Accompaniment (_accompaniment.mp3)", type=["mp3"], key="acc_upload")
        with col3:
            uploaded_lyrics_image = st.file_uploader("Lyrics Image (_lyrics_bg.jpg/png)", type=["jpg", "jpeg", "png"], key="lyrics_upload")

        if uploaded_original and uploaded_accompaniment and uploaded_lyrics_image:
            song_name = uploaded_original.name.replace("_original.mp3", "").strip()
            if not song_name:
                song_name = os.path.splitext(uploaded_original.name)[0]

            original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
            acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
            lyrics_ext = os.path.splitext(uploaded_lyrics_image.name)[1]
            lyrics_path = os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{lyrics_ext}")

            with open(original_path, "wb") as f:
                f.write(uploaded_original.getbuffer())
            with open(acc_path, "wb") as f:
                f.write(uploaded_accompaniment.getbuffer())
            with open(lyrics_path, "wb") as f:
                f.write(uploaded_lyrics_image.getbuffer())

            metadata[song_name] = {"uploaded_by": st.session_state.user, "timestamp": str(st.session_state.get("timestamp", ""))}
            save_metadata(metadata)
            st.success(f"✅ Uploaded: {song_name}")
            st.rerun()

    elif page_sidebar == "Songs List":
        st.subheader("🎵 All Songs List (Admin View)")
        uploaded_songs = get_uploaded_songs(show_unshared=True)
        if not uploaded_songs:
            st.warning("❌ No songs uploaded yet.")
        else:
            for s in uploaded_songs:
                col1, col2, col3 = st.columns([3, 1, 2])
                safe_s = quote(s)

                with col1:
                    st.write(f"{s}** - by {metadata.get(s, {}).get('uploaded_by', 'Unknown')}")
                with col2:
                    if st.button("▶ Play", key=f"play_{s}"):
                        st.session_state.selected_song = s
                        st.session_state.page = "Song Player"
                        st.rerun()
                with col3:
                    share_url = f"{APP_URL}?song={safe_s}"
                    st.markdown(f"[🔗 Share Link]({share_url})")

    elif page_sidebar == "Share Links":
        st.header("🔗 Manage Shared Links")
        all_songs = get_uploaded_songs(show_unshared=True)
        shared_links_data = load_shared_links()

        for song in all_songs:
            col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1.5])
            safe_song = quote(song)
            is_shared = song in shared_links_data

            with col1:
                status = "✅ SHARED" if is_shared else "❌ **NOT SHARED"
                st.write(f"{song} - {status}")

            with col2:
                if st.button("🔄 Toggle Share", key=f"toggle_share_{song}"):
                    if is_shared:
                        delete_shared_link(song)
                        st.success(f"✅ {song} unshared! Users can no longer see this song.")
                    else:
                        save_shared_link(song, {"shared_by": st.session_state.user, "active": True})
                        share_url = f"{APP_URL}?song={safe_song}"
                        st.success(f"✅ {song} shared! Link: {share_url}")
                    st.rerun()

            with col3:
                if is_shared:
                    if st.button("🚫 Unshare", key=f"unshare_{song}"):
                        delete_shared_link(song)
                        st.success(f"✅ {song} unshared! Users cannot see this song anymore.")
                        st.rerun()

            with col4:
                if is_shared:
                    share_url = f"{APP_URL}?song={safe_song}"
                    st.markdown(f"[📱 Open Link]({share_url})")

    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    st.title(f"👤 User Dashboard - {st.session_state.user}")

    st.subheader("🎵 Available Songs (Only Shared Songs)")
    uploaded_songs = get_uploaded_songs(show_unshared=False)

    if not uploaded_songs:
        st.warning("❌ No shared songs available. Contact admin to share songs.")
        st.info("👑 Only admin-shared songs appear here for users.")
    else:
        for song in uploaded_songs:
            col1, col2 = st.columns([3,1])
            with col1:
                st.write(f"✅ {song} (Shared)")
            with col2:
                if st.button("▶ Play", key=f"user_play_{song}"):
                    st.session_state.selected_song = song
                    st.session_state.page = "Song Player"
                    st.rerun()

    if st.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# =============== SONG PLAYER ===============
elif st.session_state.page == "Song Player" and st.session_state.get("selected_song"):

    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none !important;}
    header {visibility: hidden !important;}
    .st-emotion-cache-1pahdxg {display:none !important;}
    .st-emotion-cache-18ni7ap {padding: 0 !important;}
    footer {visibility: hidden !important;}
    div.block-container {
        padding: 0 !important;
        margin: 0 !important;
        width: 100vw !important;
    }
    html, body {
        overflow: hidden !important;
    }
    </style>
    """, unsafe_allow_html=True)

    selected_song = st.session_state.get("selected_song", None)
    if not selected_song:
        st.error("No song selected!")
        st.stop()

    # Double-check access permission
    shared_links = load_shared_links()
    is_shared = selected_song in shared_links
    is_admin = st.session_state.role == "admin"

    if not (is_shared or is_admin):
        st.error("❌ Access denied! This song is not shared with users.")
        st.session_state.page = "User Dashboard" if st.session_state.role == "user" else "Admin Dashboard"
        st.rerun()

    original_path = os.path.join(songs_dir, f"{selected_song}_original.mp3")
    accompaniment_path = os.path.join(songs_dir, f"{selected_song}_accompaniment.mp3")

    lyrics_path = ""
    for ext in [".jpg", ".jpeg", ".png"]:
        p = os.path.join(lyrics_dir, f"{selected_song}_lyrics_bg{ext}")
        if os.path.exists(p):
            lyrics_path = p
            break

    original_b64 = file_to_base64(original_path)
    accompaniment_b64 = file_to_base64(accompaniment_path)
    lyrics_b64 = file_to_base64(lyrics_path)

    # ✅ PERFECT IMAGE SIZE + LOGO POSITIONING LIKE DJANGO VERSION
    karaoke_template = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>🎤 Karaoke Reels</title>
<style>
* {margin:0; padding:0; box-sizing:border-box;}
body {background:#000; font-family:sans-serif; height:100vh; width:100vw; overflow:hidden;}
.reel-container {width:100%; height:100%; position:absolute; background:#111; overflow:hidden;}
#status {position:absolute; top:20px; width:100%; text-align:center; font-size:14px; color:#ccc; z-index:20;}
.reel-bg {position:absolute; top:0; left:0; width:100%; height:85vh; object-fit:contain;}
.controls {position:absolute; bottom:20%; width:100%; text-align:center; z-index:30;}
button {background:linear-gradient(135deg, #ff0066, #ff66cc); border:none; color:white; padding:8px 20px; border-radius:25px; font-size:13px; margin:4px; cursor:pointer;}
.final-output {position:fixed; width:100vw; height:100vh; top:0; left:0; background:rgba(0,0,0,0.9); display:none; justify-content:center; align-items:center; z-index:999;}
#logoImg {position:absolute; top:20px; left:20px; width:60px; opacity:0.6;}
canvas {display:none;}
</style>
</head>
<body>
<div class="reel-container" id="reelContainer">
<img class="reel-bg" id="mainBg" src="data:image/jpeg;base64,%%LYRICS_B64%%">
<img id="logoImg" src="data:image/png;base64,%%LOGO_B64%%">
<div id="status">Ready 🎤</div>
<audio id="originalAudio" src="data:audio/mp3;base64,%%ORIGINAL_B64%%"></audio>
<audio id="accompaniment" src="data:audio/mp3;base64,%%ACCOMP_B64%%"></audio>
<div class="controls">
<button id="playBtn">▶ Play</button>
<button id="recordBtn">🎙 Record</button>
<button id="stopBtn" style="display:none;">⏹ Stop</button>
</div>
</div>

<div class="final-output" id="finalOutputDiv">
<div class="final-reel-container">
<img class="reel-bg" id="finalBg">
<div class="controls">
<button id="playRecordingBtn">▶ Play Recording</button>
<a id="downloadRecordingBtn" href="#" download><button>⬇ Download</button></a>
<button id="newRecordingBtn">🔄 New Recording</button>
</div>
</div>
</div>

<canvas id="recordingCanvas" width="1920" height="1080"></canvas>

<script>
let mediaRecorder, recordedChunks = [], isRecording = false, playRecordingAudio = null, isPlayingRecording = false, lastRecordingURL = null;
let audioContext, micSource, accSource, canvasRafId = null;

const playBtn = document.getElementById("playBtn");
const recordBtn = document.getElementById("recordBtn");
const stopBtn = document.getElementById("stopBtn");
const status = document.getElementById("status");
const originalAudio = document.getElementById("originalAudio");
const accompanimentAudio = document.getElementById("accompaniment");
const finalDiv = document.getElementById("finalOutputDiv");
const mainBg = document.getElementById("mainBg");
const finalBg = document.getElementById("finalBg");
const playRecordingBtn = document.getElementById("playRecordingBtn");
const downloadRecordingBtn = document.getElementById("downloadRecordingBtn");
const newRecordingBtn = document.getElementById("newRecordingBtn");
const canvas = document.getElementById("recordingCanvas");
const ctx = canvas.getContext("2d");
const logoImg = new Image(); logoImg.src = document.getElementById("logoImg").src;

async function ensureAudioContext() {
    if (!audioContext) audioContext = new (window.AudioContext||window.webkitAudioContext)();
    if (audioContext.state==="suspended") await audioContext.resume();
}

async function safePlay(audio){try{await ensureAudioContext(); await audio.play();}catch(e){console.log(e);}}

playBtn.onclick = async () => {
    if (originalAudio.paused) {
        originalAudio.currentTime = 0; accompanimentAudio.currentTime = 0;
        await safePlay(originalAudio); await safePlay(accompanimentAudio);
        playBtn.innerText="⏸ Pause"; status.innerText="🎵 Playing song...";
    } else {
        originalAudio.pause(); accompanimentAudio.pause();
        playBtn.innerText="▶ Play"; status.innerText="⏸ Paused";
    }
};

function drawCanvas() {
    ctx.fillStyle="#000"; ctx.fillRect(0,0,canvas.width,canvas.height);
    const canvasW=canvas.width, canvasH=canvas.height*0.85;
    const imgRatio = mainBg.naturalWidth / mainBg.naturalHeight;
    const canvasRatio = canvasW / canvasH;
    let drawW, drawH;
    if(imgRatio>canvasRatio){drawW=canvasW; drawH=canvasW/imgRatio;}
    else{drawH=canvasH; drawW=canvasH*imgRatio;}
    const x=(canvasW-drawW)/2, y=0;
    ctx.drawImage(mainBg,x,y,drawW,drawH);
    ctx.globalAlpha=0.6; ctx.drawImage(logoImg,20,20,60,60); ctx.globalAlpha=1;
    canvasRafId=requestAnimationFrame(drawCanvas);
}

recordBtn.onclick = async () => {
    if(isRecording) return; isRecording=true; recordedChunks=[];
    await ensureAudioContext();
    const micStream=await navigator.mediaDevices.getUserMedia({audio:true});
    micSource=audioContext.createMediaStreamSource(micStream);
    const accRes=await fetch(accompanimentAudio.src);
    const accBuf=await accRes.arrayBuffer();
    const accDecoded=await audioContext.decodeAudioData(accBuf);
    accSource=audioContext.createBufferSource(); accSource.buffer=accDecoded;
    const destination=audioContext.createMediaStreamDestination();
    micSource.connect(destination); accSource.connect(destination);
    accSource.start(); canvas.width=1920; canvas.height=1080; drawCanvas();
    const stream=new MediaStream([...canvas.captureStream(30).getTracks(), ...destination.stream.getTracks()]);
    mediaRecorder=new MediaRecorder(stream);
    mediaRecorder.ondataavailable=e=>e.data.size&&recordedChunks.push(e.data);
    mediaRecorder.onstop=()=>{
        cancelAnimationFrame(canvasRafId);
        const blob=new Blob(recordedChunks,{type:"video/webm"});
        const url=URL.createObjectURL(blob);
        if(lastRecordingURL) URL.revokeObjectURL(lastRecordingURL);
        lastRecordingURL=url; finalBg.src=mainBg.src; finalDiv.style.display="flex";
        downloadRecordingBtn.href=url; downloadRecordingBtn.download=karaoke_${Date.now()}.webm;
        playRecordingBtn.onclick=()=>{
            if(!isPlayingRecording){playRecordingAudio=new Audio(url); playRecordingAudio.play(); playRecordingBtn.innerText="⏹ Stop"; isPlayingRecording=true; playRecordingAudio.onended=resetPlayBtn;}
            else resetPlayBtn();
        };
    };
    mediaRecorder.start();
    originalAudio.currentTime=0; accompanimentAudio.currentTime=0;
    await safePlay(originalAudio); await safePlay(accompanimentAudio);
    playBtn.style.display="none"; recordBtn.style.display="none"; stopBtn.style.display="inline-block"; status.innerText="🎙 Recording...";
};

stopBtn.onclick = () => {
    if(!isRecording) return; isRecording=false;
    try{mediaRecorder.stop();}catch{}
    try{accSource.stop();}catch{}
    originalAudio.pause(); accompanimentAudio.pause(); stopBtn.style.display="none"; status.innerText="⏹ Processing...";
};

function resetPlayBtn(){
    if(playRecordingAudio){playRecordingAudio.pause(); playRecordingAudio.currentTime=0;}
    playRecordingBtn.innerText="▶ Play Recording"; isPlayingRecording=false;
}

newRecordingBtn.onclick = ()=>{
    finalDiv.style.display="none"; recordedChunks=[]; isRecording=false; isPlayingRecording=false;
    originalAudio.pause(); accompanimentAudio.pause(); originalAudio.currentTime=0; accompanimentAudio.currentTime=0;
    if(playRecordingAudio){playRecordingAudio.pause(); playRecordingAudio=null;}
    playBtn.style.display="inline-block"; recordBtn.style.display="inline-block"; stopBtn.style.display="none"; playBtn.innerText="▶ Play"; status.innerText="Ready 🎤";
};
</script>
</body>
</html>
"""



    karaoke_html = karaoke_template.replace("%%LYRICS_B64%%", lyrics_b64 or "")
    karaoke_html = karaoke_html.replace("%%LOGO_B64%%", logo_b64 or "")
    karaoke_html = karaoke_html.replace("%%ORIGINAL_B64%%", original_b64 or "")
    karaoke_html = karaoke_html.replace("%%ACCOMP_B64%%", accompaniment_b64 or "")

    html(karaoke_html, height=800, width=1920)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    st.rerun()
