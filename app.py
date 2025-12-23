import streamlit as st
import os
import base64
import json
from streamlit.components.v1 import html
import hashlib
from urllib.parse import unquote, quote
from datetime import datetime
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Cloudinary Config
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"), 
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

PORT = int(os.environ.get("PORT", 8501))
st.set_page_config(page_title="𝄞 sing-along", layout="wide")

# --------- CONFIG ----------
APP_URL = "https://karaoke-song.onrender.com/"

# 🔒 SECURITY
ADMIN_HASH = os.getenv("ADMIN_HASH", "")
USER1_HASH = os.getenv("USER1_HASH", "")
USER2_HASH = os.getenv("USER2_HASH", "")

# Directories (metadata only persistent)
base_dir = os.getcwd()
media_dir = os.path.join(base_dir, "media")
logo_dir = os.path.join(media_dir, "logo")
shared_links_dir = os.path.join(media_dir, "shared_links")
metadata_path = os.path.join(media_dir, "song_metadata.json")

os.makedirs(logo_dir, exist_ok=True)
os.makedirs(shared_links_dir, exist_ok=True)

# ================= HELPER FUNCTIONS =================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_metadata():
    if os.path.exists(metadata_path):
        with open(metadata_path, "r") as f:
            return json.load(f)
    return {}

def save_metadata(data):
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    with open(metadata_path, "w") as f:
        json.dump(data, f, indent=2)

def load_shared_links():
    links = {}
    if os.path.exists(shared_links_dir):
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
                    pass
    return links

def save_shared_link(song_name, link_data):
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    os.makedirs(shared_links_dir, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(link_data, f)

def delete_shared_link(song_name):
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)

def delete_song_from_cloudinary(song_name):
    """Delete all Cloudinary assets for a song"""
    try:
        # Delete original, accompaniment, lyrics
        cloudinary.api.delete_resources([
            f"karaoke/{song_name}_original",
            f"karaoke/{song_name}_accompaniment", 
            f"karaoke/{song_name}_lyrics_bg"
        ], resource_type="video" if "_original" in f"karaoke/{song_name}_original" else "image")
    except:
        pass

def get_uploaded_songs(show_unshared=False):
    metadata = load_metadata()
    shared_links = load_shared_links()
    songs = []
    
    for song_name in metadata.keys():
        if show_unshared or song_name in shared_links:
            songs.append(song_name)
    return sorted(songs)

def file_to_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# ================= SESSION STATE =================
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
    logo_upload = st.file_uploader("Upload Logo (PNG)", type=["png"], key="logo_upload")
    if logo_upload:
        with open(default_logo_path, "wb") as f:
            f.write(logo_upload.getbuffer())
        st.rerun()
logo_b64 = file_to_base64(default_logo_path)

# ================= LOGIN PAGE =================
if st.session_state.page == "Login":
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    header {visibility:hidden;}
    body {background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%);}
    .login-content {padding: 1.8rem 2.2rem;}
    .login-header {display: flex; flex-direction: column; align-items: center; gap: 0.8rem; margin-bottom: 1.6rem; text-align: center;}
    .login-header img {width: 60px; height: 60px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.4);}
    .login-title {font-size: 1.6rem; font-weight: 700;}
    .login-sub {font-size: 0.9rem; color: #c3cfdd;}
    .stTextInput input {background: rgba(5,10,25,0.7) !important; border-radius: 10px !important; color: white !important; border: 1px solid rgba(255,255,255,0.2) !important; padding: 12px 14px !important;}
    .stTextInput input:focus {border-color: rgba(255,255,255,0.6) !important; box-shadow: 0 0 0 1px rgba(255,255,255,0.3);}
    .stButton button {width: 100%; height: 44px; background: linear-gradient(to right, #1f2937, #020712); border-radius: 10px; font-weight: 600; color: white; border: none;}
    </style>
    """, unsafe_allow_html=True)

    left, center, right = st.columns([1, 1.5, 1])
    with center:
        st.markdown('<div class="login-content">', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="login-header">
            <img src="data:image/png;base64,{logo_b64}">
            <div class="login-title">𝄞 Karaoke Reels</div>
            <div class="login-sub">Login to continue</div>
        </div>
        """, unsafe_allow_html=True)

        username = st.text_input("Email / Username", placeholder="admin / user1 / user2")
        password = st.text_input("Password", type="password", placeholder="Enter password")

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
                elif username in ["user1", "user2"] and (USER1_HASH if username == "user1" else USER2_HASH) and hashed_pass == (USER1_HASH if username == "user1" else USER2_HASH):
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")

        st.markdown('</div>', unsafe_allow_html=True)

# ================= ADMIN DASHBOARD =================
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    st.title(f"👑 Admin Dashboard - {st.session_state.user}")
    page_sidebar = st.sidebar.radio("Navigate", ["Upload Songs", "Songs List", "Share Links"])

    if page_sidebar == "Upload Songs":
        st.subheader("📤 Upload New Song to Cloud")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            uploaded_original = st.file_uploader("Original Song (MP3)", type=["mp3"], key="original_upload")
        with col2:
            uploaded_accompaniment = st.file_uploader("Accompaniment (MP3)", type=["mp3"], key="acc_upload")
        with col3:
            uploaded_lyrics_image = st.file_uploader("Lyrics Image (JPG/PNG)", type=["jpg", "jpeg", "png"], key="lyrics_upload")

        if uploaded_original and uploaded_accompaniment and uploaded_lyrics_image:
            with st.spinner("🔄 Uploading to Cloudinary..."):
                try:
                    song_name = uploaded_original.name.replace("_original.mp3", "").strip()
                    if not song_name:
                        song_name = os.path.splitext(uploaded_original.name)[0]

                    # Upload to Cloudinary
                    orig_upload = cloudinary.uploader.upload(
                        uploaded_original,
                        resource_type="video",
                        folder="karaoke/originals",
                        public_id=f"{song_name}_original",
                        overwrite=True
                    )

                    acc_upload = cloudinary.uploader.upload(
                        uploaded_accompaniment,
                        resource_type="video", 
                        folder="karaoke/accompaniments",
                        public_id=f"{song_name}_accompaniment",
                        overwrite=True
                    )

                    lyrics_upload = cloudinary.uploader.upload(
                        uploaded_lyrics_image,
                        resource_type="image",
                        folder="karaoke/lyrics",
                        public_id=f"{song_name}_lyrics_bg",
                        overwrite=True
                    )

                    # Save metadata
                    metadata[song_name] = {
                        "uploaded_by": st.session_state.user,
                        "original_url": orig_upload["secure_url"],
                        "accompaniment_url": acc_upload["secure_url"],
                        "lyrics_url": lyrics_upload["secure_url"],
                        "timestamp": datetime.now().isoformat()
                    }
                    save_metadata(metadata)

                    st.success(f"✅ {song_name} uploaded PERMANENTLY to cloud!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Upload failed: {str(e)}")

    elif page_sidebar == "Songs List":
        st.subheader("🎵 All Songs (Admin - With Delete)")
        uploaded_songs = get_uploaded_songs(show_unshared=True)
        
        if not uploaded_songs:
            st.warning("❌ No songs uploaded yet.")
        else:
            for song_name in uploaded_songs:
                col1, col2, col3, col4 = st.columns([3, 1, 1.5, 1])
                song_data = metadata.get(song_name, {})
                
                with col1:
                    st.write(f"🎵 **{song_name}** - by {song_data.get('uploaded_by', 'Unknown')}")
                with col2:
                    if st.button("▶ Play", key=f"play_{song_name}"):
                        st.session_state.selected_song = song_name
                        st.session_state.page = "Song Player"
                        st.rerun()
                with col3:
                    share_url = f"{APP_URL}?song={quote(song_name)}"
                    st.markdown(f"[🔗 Share]({share_url})")
                with col4:
                    if st.button("🗑 Delete", key=f"delete_{song_name}", type="secondary"):
                        delete_song_from_cloudinary(song_name)
                        if song_name in metadata:
                            del metadata[song_name]
                        save_metadata(metadata)
                        if song_name in load_shared_links():
                            delete_shared_link(song_name)
                        st.success(f"✅ {song_name} deleted PERMANENTLY!")
                        st.rerun()

    elif page_sidebar == "Share Links":
        st.header("🔗 Manage Shared Links")
        all_songs = get_uploaded_songs(show_unshared=True)
        shared_links_data = load_shared_links()

        for song in all_songs:
            col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1.5])
            safe_song = quote(song)
            is_shared = song in shared_links_data

            with col1:
                status = "✅ SHARED" if is_shared else "❌ NOT SHARED"
                st.write(f"{song} - {status}")

            with col2:
                if st.button("🔄 Toggle", key=f"toggle_{song}"):
                    if is_shared:
                        delete_shared_link(song)
                        st.success(f"✅ {song} unshared!")
                    else:
                        save_shared_link(song, {"shared_by": st.session_state.user, "active": True})
                        st.success(f"✅ {song} shared!")
                    st.rerun()

            with col3:
                if is_shared and st.button("🚫 Unshare", key=f"unshare_{song}"):
                    delete_shared_link(song)
                    st.success(f"✅ {song} unshared!")
                    st.rerun()

            with col4:
                if is_shared:
                    share_url = f"{APP_URL}?song={safe_song}"
                    st.markdown(f"[📱 Open]({share_url})")

    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ================= USER DASHBOARD =================
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    st.title(f"👤 User Dashboard - {st.session_state.user}")
    
    st.subheader("🎵 Available Songs (Shared Only)")
    uploaded_songs = get_uploaded_songs(show_unshared=False)

    if not uploaded_songs:
        st.warning("❌ No shared songs available.")
        st.info("👑 Ask admin to share songs.")
    else:
        for song in uploaded_songs:
            col1, col2 = st.columns([3,1])
            with col1:
                st.write(f"✅ {song}")
            with col2:
                if st.button("▶ Play", key=f"user_play_{song}"):
                    st.session_state.selected_song = song
                    st.session_state.page = "Song Player"
                    st.rerun()

    if st.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ================= SONG PLAYER =================
elif st.session_state.page == "Song Player" and st.session_state.get("selected_song"):
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none !important;}
    header, footer {visibility: hidden !important;}
    div.block-container {padding: 0 !important; margin: 0 !important; width: 100vw !important;}
    html, body {overflow: hidden !important;}
    </style>
    """, unsafe_allow_html=True)

    selected_song = st.session_state.selected_song
    if not selected_song:
        st.error("No song selected!")
        st.stop()

    # Check access
    shared_links = load_shared_links()
    is_shared = selected_song in shared_links
    is_admin = st.session_state.role == "admin"

    if not (is_shared or is_admin):
        st.error("❌ Access denied! Song not shared.")
        st.session_state.page = "User Dashboard" if st.session_state.role == "user" else "Admin Dashboard"
        st.rerun()

    # Get song data from metadata
    song_data = metadata.get(selected_song, {})
    original_url = song_data.get("original_url", "")
    accompaniment_url = song_data.get("accompaniment_url", "")
    lyrics_url = song_data.get("lyrics_url", "")

    if not all([original_url, accompaniment_url, lyrics_url]):
        st.error("❌ Song files missing!")
        st.session_state.page = "Admin Dashboard" if is_admin else "User Dashboard"
        st.rerun()
        st.stop()

    # Karaoke HTML Template (URLs instead of base64)
    karaoke_template = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>🎤 Karaoke</title>
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
<img class="reel-bg" id="mainBg" src="%%LYRICS_URL%%">
<img id="logoImg" src="data:image/png;base64,%%LOGO_B64%%">
<div id="status">Ready 🎤</div>
<audio id="originalAudio" src="%%ORIGINAL_URL%%"></audio>
<audio id="accompaniment" src="%%ACCOMP_URL%%"></audio>
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
<button id="newRecordingBtn">🔄 New</button>
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

async function safePlay(audio){
    try{await ensureAudioContext(); await audio.play();}catch(e){console.log(e);}
}

playBtn.onclick = async () => {
    if (originalAudio.paused) {
        originalAudio.currentTime = 0; accompanimentAudio.currentTime = 0;
        await safePlay(originalAudio); await safePlay(accompanimentAudio);
        playBtn.innerText="⏸ Pause"; status.innerText="🎵 Playing...";
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
        downloadRecordingBtn.href=url; downloadRecordingBtn.download=`karaoke_${Date.now()}.webm`;
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

    # Replace URLs in template
    karaoke_html = karaoke_template.replace("%%LYRICS_URL%%", lyrics_url)
    karaoke_html = karaoke_html.replace("%%ORIGINAL_URL%%", original_url)
    karaoke_html = karaoke_html.replace("%%ACCOMP_URL%%", accompaniment_url)
    karaoke_html = karaoke_html.replace("%%LOGO_B64%%", logo_b64)

    html(karaoke_html, height=800, width=1920)

# ================= FALLBACK =================
else:
    st.session_state.page = "Login"
    st.rerun()
