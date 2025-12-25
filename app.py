import streamlit as st
import os
import base64
import json
from streamlit.components.v1 import html
import hashlib
from urllib.parse import unquote, quote
import time
import sqlite3
from datetime import datetime
import uuid

st.set_page_config(page_title="𝄞 sing-along", layout="wide")

# --------- CONFIG: Update this for Railway ----------
APP_URL = os.getenv("APP_URL", "https://karaoke-project-production.up.railway.app/")

# 🔒 SECURITY: Environment Variables for Password Hashes
ADMIN_HASH = os.getenv("ADMIN_HASH", "")
USER1_HASH = os.getenv("USER1_HASH", "")
USER2_HASH = os.getenv("USER2_HASH", "")

# Base directories - FIXED for Railway
base_dir = os.getcwd()
media_dir = os.path.join(base_dir, "media")
songs_dir = os.path.join(media_dir, "songs")
lyrics_dir = os.path.join(media_dir, "lyrics_images")
logo_dir = os.path.join(media_dir, "logo")
shared_links_dir = os.path.join(media_dir, "shared_links")
metadata_path = os.path.join(media_dir, "song_metadata.json")
session_db_path = os.path.join(base_dir, "sessions.db")  # Fixed DB name

# Create directories
os.makedirs(songs_dir, exist_ok=True)
os.makedirs(lyrics_dir, exist_ok=True)
os.makedirs(logo_dir, exist_ok=True)
os.makedirs(shared_links_dir, exist_ok=True)

# =============== FAST PERSISTENT SESSION DATABASE ===============
@st.cache_resource
def get_session_db():
    """Cached database connection for Railway performance"""
    return sqlite3.connect(session_db_path, check_same_thread=False)

def init_session_db():
    """Initialize SQLite database for persistent sessions"""
    try:
        conn = get_session_db()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS sessions
                     (session_id TEXT PRIMARY KEY,
                      user TEXT,
                      role TEXT,
                      page TEXT,
                      selected_song TEXT,
                      last_active TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS shared_links
                     (song_name TEXT PRIMARY KEY,
                      shared_by TEXT,
                      active BOOLEAN,
                      created_at TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS metadata
                     (song_name TEXT PRIMARY KEY,
                      uploaded_by TEXT,
                      timestamp REAL)''')
        conn.commit()
    except Exception as e:
        st.error(f"DB init error: {e}")

def save_session_to_db():
    """Save current session to database - FAST"""
    try:
        if 'session_id' not in st.session_state:
            return
        conn = get_session_db()
        c = conn.cursor()
        session_id = st.session_state.session_id
        
        c.execute('''INSERT OR REPLACE INTO sessions 
                     (session_id, user, role, page, selected_song, last_active)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (session_id,
                   st.session_state.get('user', ''),
                   st.session_state.get('role', ''),
                   st.session_state.get('page', ''),
                   st.session_state.get('selected_song', ''),
                   datetime.now()))
        conn.commit()
    except:
        pass

def load_session_from_db():
    """Load session from database - FAST"""
    try:
        if 'session_id' not in st.session_state:
            return
        session_id = st.session_state.session_id
        conn = get_session_db()
        c = conn.cursor()
        c.execute('SELECT user, role, page, selected_song FROM sessions WHERE session_id = ?', 
                  (session_id,))
        result = c.fetchone()
        if result:
            user, role, page, selected_song = result
            if user: st.session_state.user = user
            if role: st.session_state.role = role
            if page: st.session_state.page = page
            if selected_song: st.session_state.selected_song = selected_song
    except:
        pass

def get_uploaded_songs(show_unshared=False):
    """Get list of uploaded songs - CACHED for speed"""
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def cached_songs(_show_unshared):
        songs = []
        if not os.path.exists(songs_dir):
            return songs
        
        for f in os.listdir(songs_dir):
            if f.endswith("_original.mp3"):
                song_name = f.replace("_original.mp3", "")
                songs.append(song_name)
        return sorted(songs)
    
    all_songs = cached_songs(show_unshared)
    if show_unshared:
        return all_songs
    
    # Filter shared songs
    try:
        conn = get_session_db()
        c = conn.cursor()
        c.execute('SELECT song_name FROM shared_links WHERE active = 1')
        shared = {row[0] for row in c.fetchall()}
        conn.close()
        return [s for s in all_songs if s in shared]
    except:
        return all_songs

# Initialize database ONCE
if not os.path.exists(session_db_path):
    init_session_db()

# =============== FAST HELPER FUNCTIONS ===============
def file_to_base64(path):
    """Fast base64 conversion with size check"""
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "rb") as f:
            data = f.read()
            # Limit size for Railway - compress if needed
            if len(data) > 50 * 1024 * 1024:  # 50MB limit
                return ""
            return base64.b64encode(data).decode()
    except:
        return ""

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_and_create_session_id():
    """Create unique session ID"""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

# =============== INITIALIZE FAST SESSION ===============
check_and_create_session_id()

# Initialize session state with default values
for key, default in [("user", None), ("role", None), ("page", "Login"), ("selected_song", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# Load persistent session data FAST
load_session_from_db()

# Logo - cached
@st.cache_data
def get_logo():
    default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
    return file_to_base64(default_logo_path) if os.path.exists(default_logo_path) else ""

logo_b64 = get_logo()

# =============== FAST DIRECT SONG ACCESS ===============
query_params = st.query_params
if "song" in query_params and st.session_state.page == "Login":
    song_from_url = unquote(query_params["song"][0])
    songs = get_uploaded_songs(show_unshared=False)
    if song_from_url in songs:
        st.session_state.selected_song = song_from_url
        st.session_state.page = "Song Player"
        st.session_state.user = "guest"
        st.session_state.role = "guest"
        save_session_to_db()
        st.rerun()

# =============== LOGIN PAGE (UNCHANGED UI) ===============
if st.session_state.page == "Login":
    save_session_to_db()
    
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    header {visibility:hidden;}
    body {background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%);}
    .login-content {padding: 1.8rem 2.2rem 2.2rem 2.2rem;}
    .login-header {display: flex;flex-direction: column;align-items: center;justify-content: center;gap: 0.8rem;margin-bottom: 1.6rem;text-align: center;}
    .login-header img {width: 60px;height: 60px;border-radius: 50%;border: 2px solid rgba(255,255,255,0.4);}
    .login-title {font-size: 1.6rem;font-weight: 700;width: 100%;}
    .login-sub {font-size: 0.9rem;color: #c3cfdd;margin-bottom: 0.5rem;width: 100%;}
    .credentials-info {background: rgba(5,10,25,0.8);border: 1px solid rgba(255,255,255,0.2);border-radius: 10px;padding: 12px;margin-top: 16px;font-size: 0.85rem;color: #b5c2d2;}
    .stTextInput input {background: rgba(5,10,25,0.7) !important;border-radius: 10px !important;color: white !important;border: 1px solid rgba(255,255,255,0.2) !important;padding: 12px 14px !important;}
    .stTextInput input:focus {border-color: rgba(255,255,255,0.6) !important;box-shadow: 0 0 0 1px rgba(255,255,255,0.3);}
    .stButton button {width: 100%;height: 44px;background: linear-gradient(to right, #1f2937, #020712);border-radius: 10px;font-weight: 600;margin-top: 0.6rem;color: white;border: none;}
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

        username = st.text_input("Email / Username", placeholder="admin / user1 / user2", key="login_username")
        password = st.text_input("Password", type="password", placeholder="Enter password", key="login_password")

        if st.button("Login", key="login_button"):
            if not username or not password:
                st.error("❌ Enter both username and password")
            else:
                hashed_pass = hash_password(password)
                if username == "admin" and ADMIN_HASH and hashed_pass == ADMIN_HASH:
                    st.session_state.user = username
                    st.session_state.role = "admin"
                    st.session_state.page = "Admin Dashboard"
                    save_session_to_db()
                    st.rerun()
                elif username == "user1" and USER1_HASH and hashed_pass == USER1_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    save_session_to_db()
                    st.rerun()
                elif username == "user2" and USER2_HASH and hashed_pass == USER2_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    save_session_to_db()
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")

        st.markdown("""
        <div style="margin-top:16px;font-size:0.8rem;color:#b5c2d2;text-align:center;padding-bottom:8px;">
            Don't have access? Contact admin.
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

# =============== ADMIN DASHBOARD (UNCHANGED UI) ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    save_session_to_db()
    st.title(f"👑 Admin Dashboard - {st.session_state.user}")
    
    page_sidebar = st.sidebar.radio("Navigate", ["Upload Songs", "Songs List", "Share Links"], key="admin_nav")

    if page_sidebar == "Upload Songs":
        st.subheader("📤 Upload New Song")
        col1, col2, col3 = st.columns(3)
        with col1: uploaded_original = st.file_uploader("Original Song (_original.mp3)", type=["mp3"], key="original_upload")
        with col2: uploaded_accompaniment = st.file_uploader("Accompaniment (_accompaniment.mp3)", type=["mp3"], key="acc_upload")
        with col3: uploaded_lyrics_image = st.file_uploader("Lyrics Image (_lyrics_bg.jpg/png)", type=["jpg", "jpeg", "png"], key="lyrics_upload")

        if uploaded_original and uploaded_accompaniment and uploaded_lyrics_image:
            song_name = uploaded_original.name.replace("_original.mp3", "").strip() or os.path.splitext(uploaded_original.name)[0]
            
            original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
            acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
            lyrics_ext = os.path.splitext(uploaded_lyrics_image.name)[1]
            lyrics_path = os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{lyrics_ext}")

            with open(original_path, "wb") as f: f.write(uploaded_original.getbuffer())
            with open(acc_path, "wb") as f: f.write(uploaded_accompaniment.getbuffer())
            with open(lyrics_path, "wb") as f: f.write(uploaded_lyrics_image.getbuffer())

            # Fast metadata save
            conn = get_session_db()
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO metadata (song_name, uploaded_by, timestamp) VALUES (?, ?, ?)''',
                     (song_name, st.session_state.user, time.time()))
            conn.commit()
            conn.close()
            
            st.success(f"✅ Uploaded: {song_name}")
            st.balloons()
            time.sleep(1)
            st.rerun()

    elif page_sidebar == "Songs List":
        st.subheader("🎵 All Songs List (Admin View)")
        uploaded_songs = get_uploaded_songs(show_unshared=True)
        if not uploaded_songs:
            st.warning("❌ No songs uploaded yet.")
        else:
            for idx, s in enumerate(uploaded_songs):
                col1, col2, col3 = st.columns([3, 1, 2])
                safe_s = quote(s)
                with col1: st.write(f"**{s}**")
                with col2:
                    if st.button("▶ Play", key=f"play_{s}_{idx}"):
                        st.session_state.selected_song = s
                        st.session_state.page = "Song Player"
                        save_session_to_db()
                        st.rerun()
                with col3: st.markdown(f"[🔗 Share Link]({APP_URL}?song={safe_s})")

    elif page_sidebar == "Share Links":
        st.header("🔗 Manage Shared Links")
        all_songs = get_uploaded_songs(show_unshared=True)
        
        for song in all_songs:
            col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1.5])
            safe_song = quote(song)
            
            conn = get_session_db()
            c = conn.cursor()
            c.execute('SELECT active FROM shared_links WHERE song_name = ?', (song,))
            result = c.fetchone()
            is_shared = bool(result and result[0]) if result else False
            conn.close()
            
            with col1: st.write(f"{song} - {'✅ SHARED' if is_shared else '❌ NOT SHARED'}")
            with col2:
                if st.button("🔄 Toggle Share", key=f"toggle_share_{song}"):
                    conn = get_session_db()
                    c = conn.cursor()
                    if is_shared:
                        c.execute('DELETE FROM shared_links WHERE song_name = ?', (song,))
                        st.success(f"✅ {song} unshared!")
                    else:
                        c.execute('INSERT OR REPLACE INTO shared_links (song_name, shared_by, active, created_at) VALUES (?, ?, 1, ?)',
                                (song, st.session_state.user, datetime.now()))
                        st.success(f"✅ {song} shared! Link: {APP_URL}?song={safe_song}")
                    conn.commit()
                    conn.close()
                    time.sleep(0.5)
                    st.rerun()
            with col3:
                if is_shared and st.button("🚫 Unshare", key=f"unshare_{song}"):
                    conn = get_session_db()
                    c = conn.cursor()
                    c.execute('DELETE FROM shared_links WHERE song_name = ?', (song,))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ {song} unshared!")
                    time.sleep(0.5)
                    st.rerun()
            with col4:
                if is_shared: st.markdown(f"[📱 Open Link]({APP_URL}?song={safe_song})")

    if st.sidebar.button("🚪 Logout", key="admin_logout"):
        st.session_state.clear()
        st.session_state.page = "Login"
        st.rerun()

# =============== USER DASHBOARD (UNCHANGED UI) ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    save_session_to_db()
    st.title(f"👤 User Dashboard - {st.session_state.user}")
    
    st.subheader("🎵 Available Songs (Only Shared Songs)")
    uploaded_songs = get_uploaded_songs(show_unshared=False)
    
    if not uploaded_songs:
        st.warning("❌ No shared songs available. Contact admin to share songs.")
    else:
        for idx, song in enumerate(uploaded_songs):
            col1, col2 = st.columns([3,1])
            with col1: st.write(f"✅ {song} (Shared)")
            with col2:
                if st.button("▶ Play", key=f"user_play_{song}_{idx}"):
                    st.session_state.selected_song = song
                    st.session_state.page = "Song Player"
                    save_session_to_db()
                    st.rerun()

    if st.button("🚪 Logout", key="user_logout"):
        st.session_state.clear()
        st.session_state.page = "Login"
        st.rerun()

# =============== ULTRA-FAST SONG PLAYER ===============
elif st.session_state.page == "Song Player" and st.session_state.selected_song:
    save_session_to_db()
    
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none !important;}
    header {visibility: hidden !important;}
    .st-emotion-cache-1pahdxg {display:none !important;}
    .st-emotion-cache-18ni7ap {padding: 0 !important;}
    footer {visibility: hidden !important;}
    div.block-container {padding: 0 !important;margin: 0 !important;width: 100vw !important;}
    html, body {overflow: hidden !important;}
    </style>
    """, unsafe_allow_html=True)

    selected_song = st.session_state.selected_song
    
    # FAST ACCESS CHECK
    conn = get_session_db()
    c = conn.cursor()
    c.execute('SELECT active FROM shared_links WHERE song_name = ?', (selected_song,))
    result = c.fetchone()
    is_shared = bool(result and result[0]) if result else False
    is_admin = st.session_state.role == "admin"
    
    if not (is_shared or is_admin):
        st.error("❌ Access denied!")
        if st.button("Go Back"): 
            st.session_state.page = "Admin Dashboard" if is_admin else "User Dashboard"
            st.rerun()
        st.stop()

    # FAST FILE PATHS
    original_path = os.path.join(songs_dir, f"{selected_song}_original.mp3")
    accompaniment_path = os.path.join(songs_dir, f"{selected_song}_accompaniment.mp3")
    
    lyrics_path = next((os.path.join(lyrics_dir, f"{selected_song}_lyrics_bg{ext}") 
                       for ext in [".jpg", ".jpeg", ".png"] 
                       if os.path.exists(os.path.join(lyrics_dir, f"{selected_song}_lyrics_bg{ext}"))), "")

    # PRE-LOAD BASE64 IN PARALLEL
    original_b64 = file_to_base64(original_path)
    accompaniment_b64 = file_to_base64(accompaniment_path)
    lyrics_b64 = file_to_base64(lyrics_path)

    if not original_b64:
        st.error("❌ Song file not found!")
        if st.button("Go Back"): st.rerun()
        st.stop()

    # ULTRA-FAST OPTIMIZED KARAOKE TEMPLATE
    karaoke_template = """
<!doctype html>
<html><head>
<meta charset="utf-8"/><title>🎤 Karaoke</title>
<style>*{margin:0;padding:0;box-sizing:border-box;}
body{background:#000;font-family:'Poppins',sans-serif;height:100vh;width:100vw;overflow:hidden;}
.reel-container{width:100%;height:100%;position:absolute;background:#111;overflow:hidden;}
#status{position:absolute;top:20px;width:100%;text-align:center;font-size:14px;color:#ccc;z-index:20;text-shadow:1px 1px 6px rgba(0,0,0,0.9);}
.reel-bg{position:absolute;top:0;left:0;width:100%;height:85vh;object-fit:contain;object-position:top;}
.lyrics{position:absolute;bottom:25%;width:100%;text-align:center;font-size:2vw;font-weight:bold;color:white;text-shadow:2px 2px 10px black;}
.controls{position:absolute;bottom:20%;width:100%;text-align:center;z-index:30;}
button{background:linear-gradient(135deg,#ff0066,#ff66cc);border:none;color:white;padding:8px 20px;border-radius:25px;font-size:13px;margin:4px;box-shadow:0px 3px 15px rgba(255,0,128,0.4);cursor:pointer;}
button:active{transform:scale(0.95);}
.final-output{position:fixed;width:100vw;height:100vh;top:0;left:0;background:rgba(0,0,0,0.9);display:none;justify-content:center;align-items:center;z-index:999;}
#logoImg{position:absolute;top:20px;left:20px;width:60px;z-index:50;opacity:0.6;}
canvas{display:none;}
.back-button{position:absolute;top:20px;right:20px;background:rgba(0,0,0,0.7);color:white;padding:8px 16px;border-radius:20px;text-decoration:none;font-size:14px;z-index:100;}
</style>
</head><body>
<div class="reel-container">
<img class="reel-bg" id="mainBg" src="data:image/jpeg;base64,%%LYRICS_B64%%">
<img id="logoImg" src="data:image/png;base64,%%LOGO_B64%%">
<div id="status">Ready 🎤</div>
<audio id="originalAudio" src="data:audio/mp3;base64,%%ORIGINAL_B64%%" preload="auto"></audio>
<audio id="accompaniment" src="data:audio/mp3;base64,%%ACCOMP_B64%%" preload="auto"></audio>
<div class="controls">
<button id="playBtn">▶ Play</button>
<button id="recordBtn">🎙 Record</button>
<button id="stopBtn" style="display:none;">⏹ Stop</button>
</div>
</div>
<div class="final-output" id="finalOutputDiv">
<div class="final-reel-container">
<img class="reel-bg" id="finalBg">
<div id="status"></div>
<div class="lyrics" id="finalLyrics"></div>
<div class="controls">
<button id="playRecordingBtn">▶ Play Recording</button>
<a id="downloadRecordingBtn" href="#" download><button>⬇ Download</button></a>
<button id="newRecordingBtn">🔄 New Recording</button>
</div></div></div>
<canvas id="recordingCanvas" width="1920" height="1080"></canvas>
<script>
let mediaRecorder,recordedChunks=[],playRecordingAudio,lastRecordingURL;
let audioContext,micSource,accSource,canvasRafId,isRecording=false,isPlayingRecording=false;
const playBtn=document.getElementById("playBtn"),recordBtn=document.getElementById("recordBtn"),stopBtn=document.getElementById("stopBtn"),status=document.getElementById("status"),originalAudio=document.getElementById("originalAudio"),accompanimentAudio=document.getElementById("accompaniment"),finalDiv=document.getElementById("finalOutputDiv"),mainBg=document.getElementById("mainBg"),finalBg=document.getElementById("finalBg"),canvas=document.getElementById("recordingCanvas"),ctx=canvas.getContext("2d"),logoImg=new Image();
logoImg.src=document.getElementById("logoImg").src;
async function ensureAudioContext(){if(!audioContext)audioContext=new(window.AudioContext||window.webkitAudioContext)();if(audioContext.state==="suspended")await audioContext.resume();}
async function safePlay(audio){try{await ensureAudioContext();audio.play()}catch(e){}}
playBtn.onclick=async()=>{await ensureAudioContext();if(originalAudio.paused){originalAudio.currentTime=0;await safePlay(originalAudio);playBtn.innerText="⏸ Pause";status.innerText="🎵 Playing song..."}else{originalAudio.pause();playBtn.innerText="▶ Play";status.innerText="⏸ Paused"}};
function drawCanvas(){ctx.fillStyle="#000";ctx.fillRect(0,0,canvas.width,canvas.height);const canvasW=canvas.width,canvasH=canvas.height*0.85,imgRatio=mainBg.naturalWidth/mainBg.naturalHeight,canvasRatio=canvasW/canvasH;let drawW,drawH;if(imgRatio>canvasRatio){drawW=canvasW;drawH=canvasW/imgRatio}else{drawH=canvasH;drawW=canvasH*imgRatio}const x=(canvasW-drawW)/2;y=0;ctx.drawImage(mainBg,x,y,drawW,drawH);ctx.globalAlpha=0.6;ctx.drawImage(logoImg,20,20,60,60);ctx.globalAlpha=1;canvasRafId=requestAnimationFrame(drawCanvas)}
recordBtn.onclick=async()=>{if(isRecording)return;isRecording=true;await ensureAudioContext();recordedChunks=[];const micStream=await navigator.mediaDevices.getUserMedia({audio:true});micSource=audioContext.createMediaStreamSource(micStream);const accRes=await fetch(accompanimentAudio.src),accBuf=await accRes.arrayBuffer(),accDecoded=await audioContext.decodeAudioData(accBuf);accSource=audioContext.createBufferSource();accSource.buffer=accDecoded;const destination=audioContext.createMediaStreamDestination();micSource.connect(destination);accSource.connect(destination);accSource.start();canvas.width=1920;canvas.height=1080;drawCanvas();const stream=new MediaStream([...canvas.captureStream(30).getTracks(),...destination.stream.getTracks()]);mediaRecorder=new MediaRecorder(stream);mediaRecorder.ondataavailable=e=>e.data.size&&recordedChunks.push(e.data);mediaRecorder.onstop=()=>{cancelAnimationFrame(canvasRafId);const blob=new Blob(recordedChunks,{type:"video/webm"}),url=URL.createObjectURL(blob);if(lastRecordingURL)URL.revokeObjectURL(lastRecordingURL);lastRecordingURL=url;finalBg.src=mainBg.src;finalDiv.style.display="flex";downloadRecordingBtn.href=url;downloadRecordingBtn.download=`karaoke_${Date.now()}.webm`;playRecordingBtn.onclick=()=>{if(!isPlayingRecording){playRecordingAudio=new Audio(url);playRecordingAudio.play();playRecordingBtn.innerText="⏹ Stop";isPlayingRecording=true;playRecordingAudio.onended=resetPlayBtn}else{resetPlayBtn()}}};mediaRecorder.start();originalAudio.currentTime=0;accompanimentAudio.currentTime=0;await safePlay(originalAudio);await safePlay(accompanimentAudio);playBtn.style.display="none";recordBtn.style.display="none";stopBtn.style.display="inline-block";status.innerText="🎙 Recording..."}
stopBtn.onclick=()=>{if(!isRecording)return;isRecording=false;try{mediaRecorder.stop()}catch{}try{accSource.stop()}catch{}originalAudio.pause();accompanimentAudio.pause();stopBtn.style.display="none";status.innerText="⏹ Processing..."}
function resetPlayBtn(){if(playRecordingAudio){playRecordingAudio.pause();playRecordingAudio.currentTime=0}playRecordingBtn.innerText="▶ Play Recording";isPlayingRecording=false}
document.getElementById("newRecordingBtn").onclick=()=>{finalDiv.style.display="none";recordedChunks=[];isRecording=isPlayingRecording=false;originalAudio.pause();accompanimentAudio.pause();originalAudio.currentTime=accompanimentAudio.currentTime=0;if(playRecordingAudio){playRecordingAudio.pause();playRecordingAudio=null}playBtn.style.display=recordBtn.style.display="inline-block";stopBtn.style.display="none";playBtn.innerText="▶ Play";status.innerText="Ready 🎤"}
</script></body></html>
"""

    karaoke_html = karaoke_template.replace("%%LYRICS_B64%%", lyrics_b64).replace("%%LOGO_B64%%", logo_b64).replace("%%ORIGINAL_B64%%", original_b64).replace("%%ACCOMP_B64%%", accompaniment_b64)

    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("← Back", key="back_player"):
            st.session_state.page = "Admin Dashboard" if st.session_state.role == "admin" else "User Dashboard"
            st.rerun()

    html(karaoke_html, height=800, width=1920, scrolling=False)

else:
    st.session_state.page = "Login"
    st.rerun()
