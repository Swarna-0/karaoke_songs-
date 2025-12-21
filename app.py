import streamlit as st
import os
import base64
import json
from streamlit.components.v1 import html
import hashlib
from urllib.parse import unquote, quote

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
if "previous_page" not in st.session_state:
    st.session_state.previous_page = None
if "navigation_history" not in st.session_state:
    st.session_state.navigation_history = []
if "history_index" not in st.session_state:
    st.session_state.history_index = -1

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

# Navigation function
def navigate_to(page, save_history=True):
    if save_history:
        current_page = st.session_state.get("page", "Login")
        if st.session_state.navigation_history and st.session_state.history_index < len(st.session_state.navigation_history) - 1:
            st.session_state.navigation_history = st.session_state.navigation_history[:st.session_state.history_index + 1]
        st.session_state.navigation_history.append(current_page)
        st.session_state.history_index += 1
    
    st.session_state.previous_page = st.session_state.get("page", "Login")
    st.session_state.page = page

def go_back():
    if st.session_state.history_index > 0:
        st.session_state.history_index -= 1
        prev_page = st.session_state.navigation_history[st.session_state.history_index]
        st.session_state.page = prev_page
        st.rerun()
    else:
        st.session_state.page = "Login"
        st.rerun()

def go_forward():
    if st.session_state.history_index < len(st.session_state.navigation_history) - 1:
        st.session_state.history_index += 1
        st.session_state.page = st.session_state.navigation_history[st.session_state.history_index]
        st.rerun()

# =============== RESPONSIVE LOGIN PAGE ===============
if st.session_state.page == "Login":

    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    header {visibility:hidden;}
    body { background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%); }
    .login-content { padding: 1.8rem 2.2rem 2.2rem 2.2rem; }
    .login-header { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.8rem; margin-bottom: 1.6rem; text-align: center; }
    .login-header img { width: 60px; height: 60px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.4); }
    .login-title { font-size: 1.6rem; font-weight: 700; width: 100%; }
    .login-sub { font-size: 0.9rem; color: #c3cfdd; margin-bottom: 0.5rem; width: 100%; }
    .stTextInput input { background: rgba(5,10,25,0.7) !important; border-radius: 10px !important; color: white !important; border: 1px solid rgba(255,255,255,0.2) !important; padding: 12px 14px !important; }
    .stTextInput input:focus { border-color: rgba(255,255,255,0.6) !important; box-shadow: 0 0 0 1px rgba(255,255,255,0.3); }
    .stButton button { width: 100%; height: 44px; background: linear-gradient(to right, #1f2937, #020712); border-radius: 10px; font-weight: 600; margin-top: 0.6rem; color: white; border: none; }
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
                    navigate_to("Admin Dashboard")
                    st.rerun()
                elif username == "user1" and USER1_HASH and hashed_pass == USER1_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    navigate_to("User Dashboard")
                    st.rerun()
                elif username == "user2" and USER2_HASH and hashed_pass == USER2_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    navigate_to("User Dashboard")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")

        st.markdown("""
        <div style="margin-top:16px;font-size:0.8rem;color:#b5c2d2;text-align:center;padding-bottom:8px;">
            Don't have access? Contact admin.
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# =============== ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    st.markdown("""
    <style>
    .nav-buttons { position: fixed; top: 10px; left: 10px; z-index: 1000; display: flex; gap: 5px; }
    .nav-btn { background: linear-gradient(135deg, #667eea, #764ba2) !important; color: white !important; border-radius: 20px !important; padding: 8px 12px !important; font-size: 14px !important; font-weight: 600 !important; border: none !important; box-shadow: 0 2px 10px rgba(102,126,234,0.4) !important; }
    .nav-btn:hover { transform: scale(1.05) !important; }
    .nav-btn:disabled { opacity: 0.5 !important; cursor: not-allowed !important; }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 8, 1])
    with col1:
        st.markdown('<div class="nav-buttons">', unsafe_allow_html=True)
        col_back, col_forward = st.columns([1,1])
        with col_back:
            if st.button("⬅ Back", key="admin_back"):
                go_back()
        with col_forward:
            if st.button("➡️ Forward", key="admin_forward", disabled=st.session_state.history_index >= len(st.session_state.navigation_history)-1):
                go_forward()
        st.markdown('</div>', unsafe_allow_html=True)

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
                        navigate_to("Song Player")
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
                status = "✅ *SHARED" if is_shared else "❌ **NOT SHARED*"
                st.write(f"{song} - {status}")

            with col2:
                if st.button("🔄 Toggle Share", key=f"toggle_share_{song}"):
                    if is_shared:
                        delete_shared_link(song)
                        st.success(f"✅ *{song}* unshared! Users can no longer see this song.")
                    else:
                        save_shared_link(song, {"shared_by": st.session_state.user, "active": True})
                        share_url = f"{APP_URL}?song={safe_song}"
                        st.success(f"✅ *{song}* shared! Link: {share_url}")
                    st.rerun()

            with col3:
                if is_shared:
                    if st.button("🚫 Unshare", key=f"unshare_{song}"):
                        delete_shared_link(song)
                        st.success(f"✅ *{song}* unshared! Users cannot see this song anymore.")
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
    st.markdown("""
    <style>
    .nav-buttons { position: fixed; top: 10px; left: 10px; z-index: 1000; display: flex; gap: 5px; }
    .nav-btn { background: linear-gradient(135deg, #667eea, #764ba2) !important; color: white !important; border-radius: 20px !important; padding: 8px 12px !important; font-size: 14px !important; font-weight: 600 !important; border: none !important; box-shadow: 0 2px 10px rgba(102,126,234,0.4) !important; }
    .nav-btn:hover { transform: scale(1.05) !important; }
    .nav-btn:disabled { opacity: 0.5 !important; cursor: not-allowed !important; }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 8, 1])
    with col1:
        st.markdown('<div class="nav-buttons">', unsafe_allow_html=True)
        col_back, col_forward = st.columns([1,1])
        with col_back:
            if st.button("⬅ Back", key="user_back"):
                go_back()
        with col_forward:
            if st.button("➡️ Forward", key="user_forward", disabled=st.session_state.history_index >= len(st.session_state.navigation_history)-1):
                go_forward()
        st.markdown('</div>', unsafe_allow_html=True)

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
                st.write(f"✅ *{song}* (Shared)")
            with col2:
                if st.button("▶ Play", key=f"user_play_{song}"):
                    st.session_state.selected_song = song
                    navigate_to("Song Player")
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
    div.block-container { padding: 0 !important; margin: 0 !important; width: 100vw !important; }
    html, body { overflow: hidden !important; }
    .top-nav { position: fixed; top: 10px; left: 10px; z-index: 10000; display: flex; gap: 5px; background: rgba(0,0,0,0.9); padding: 8px; border-radius: 25px; }
    .nav-btn { background: linear-gradient(135deg, #667eea, #764ba2) !important; color: white !important; border-radius: 20px !important; padding: 10px 15px !important; font-size: 16px !important; font-weight: 600 !important; border: none !important; box-shadow: 0 3px 15px rgba(102,126,234,0.5) !important; cursor: pointer !important; }
    .nav-btn:hover { transform: scale(1.05) !important; }
    .nav-btn:disabled { opacity: 0.5 !important; cursor: not-allowed !important; }
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

    # TOP NAVIGATION BAR
    col1, col2 = st.columns([1,10])
    with col1:
        if st.button("⬅ Back", key="player_back"):
            go_back()
        if st.button("➡️ Forward", key="player_forward", disabled=st.session_state.history_index >= len(st.session_state.navigation_history)-1):
            go_forward()

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

    # FIXED KARAOKE TEMPLATE - No f-string issues
    karaoke_template = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>🎤 Karaoke Reels</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #000; font-family: 'Poppins', sans-serif; height: 100vh; width: 100vw; overflow: hidden; }
.reel-container, .final-reel-container { width: 100%; height: 100%; position: absolute; background: #111; overflow: hidden; }
#status { position: absolute; top: 20px; width: 100%; text-align: center; font-size: 14px; color: #ccc; z-index: 20; text-shadow: 1px 1px 6px rgba(0,0,0,0.9); }
.reel-bg { position: absolute; top: 0; left: 0; width: 100%; height: 85vh; object-fit: contain; object-position: top; }
.lyrics { position: absolute; bottom: 25%; width: 100%; text-align: center; font-size: 2vw; font-weight: bold; color: white; text-shadow: 2px 2px 10px black; }
.controls { position: absolute; bottom: 20%; width: 100%; text-align: center; z-index: 30; }
button { background: linear-gradient(135deg, #ff0066, #ff66cc); border: none; color: white; padding: 8px 20px; border-radius: 25px; font-size: 13px; margin: 4px; box-shadow: 0px 3px 15px rgba(255,0,128,0.4); cursor: pointer; }
button:active { transform: scale(0.95); }
.final-output { position: fixed; width: 100vw; height: 100vh; top: 0; left: 0; background: rgba(0,0,0,0.9); display: none; justify-content: center; align-items: center; z-index: 999; }
#logoImg { position: absolute; top: 20px; left: 20px; width: 60px; z-index: 50; opacity: 0.6; }
canvas { display: none; }
</style>
</head>
<body>

<div class="reel-container" id="reelContainer">
    <img class="reel-bg" id="mainBg" src="data:image/jpeg;base64,%s">
    <img id="logoImg" src="data:image/png;base64,%s">
    <div id="status">Ready 🎤</div>
    <audio id="originalAudio" src="data:audio/mp3;base64,%s"></audio>
    <audio id="accompaniment" src="data:audio/mp3;base64,%s"></audio>
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
      <a id="downloadRecordingBtn" href="#" download>
        <button>⬇ Download</button>
      </a>
      <button id="newRecordingBtn">🔄 New Recording</button>
    </div>
  </div>
</div>

<canvas id="recordingCanvas" width="1920" height="1080"></canvas>

<script>
let mediaRecorder, recordedChunks = [], playRecordingAudio = null, isPlayingRecording = false;
let audioContext, micSource, accSource, canvasRafId, logoImg;

const playBtn = document.getElementById("playBtn");
const recordBtn = document.getElementById("recordBtn");
const stopBtn = document.getElementById("stopBtn");
const status = document.getElementById("status");
const originalAudio = document.getElementById("originalAudio");
const accompanimentAudio = document.getElementById("accompaniment");
const finalDiv = document.getElementById("finalOutputDiv");
const mainBg = document.getElementById("mainBg");
const finalBg = document.getElementById("finalBg");
const finalLyrics = document.getElementById("finalLyrics");
const playRecordingBtn = document.getElementById("playRecordingBtn");
const downloadRecordingBtn = document.getElementById("downloadRecordingBtn");
const newRecordingBtn = document.getElementById("newRecordingBtn");
const canvas = document.getElementById("recordingCanvas");
const ctx = canvas.getContext('2d');

// Preload logo for canvas
logoImg = new Image();
logoImg.src = document.getElementById("logoImg").src;

async function safePlay(audio){ 
    try{ await audio.play(); }catch(e){console.log("Autoplay blocked:", e);} 
}

playBtn.onclick = async () => { 
    if (originalAudio.paused) {
        originalAudio.currentTime = 0; 
        await safePlay(originalAudio); 
        status.innerText = "🎵 Playing song..."; 
        playBtn.innerText = "⏸ Pause";
    } else {
        originalAudio.pause();
        status.innerText = "⏸ Paused";
        playBtn.innerText = "▶ Play";
    }
};

recordBtn.onclick = async () => {
    recordedChunks = [];
    
    let micStream = await navigator.mediaDevices.getUserMedia({ 
        audio: { echoCancellation: true, noiseSuppression: true },
        video: false 
    });
    
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    micSource = audioContext.createMediaStreamSource(micStream);
    
    const accResponse = await fetch(accompanimentAudio.src);
    const accBuffer = await accResponse.arrayBuffer();
    const accDecoded = await audioContext.decodeAudioData(accBuffer);
    
    accSource = audioContext.createBufferSource();
    accSource.buffer = accDecoded;
    
    const destination = audioContext.createMediaStreamDestination();
    const micGain = audioContext.createGain();
    const accGain = audioContext.createGain();
    
    micGain.gain.value = 1.0;
    accGain.gain.value = 0.7;
    
    micSource.connect(micGain).connect(destination);
    accSource.connect(accGain).connect(destination);
    
    const userAccSource = audioContext.createBufferSource();
    userAccSource.buffer = accDecoded;
    userAccSource.connect(audioContext.destination);
    
    accSource.start();
    userAccSource.start();
    
    canvas.width = 1920;
    canvas.height = 1080;
    
    function animateCanvas() {
        ctx.fillStyle = '#111';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        if (mainBg.complete && mainBg.naturalWidth > 0) {
            const imgRatio = mainBg.naturalWidth / mainBg.naturalHeight;
            let videoHeight = 0.85 * canvas.height;
            let videoWidth = videoHeight * imgRatio;
            
            if (videoWidth > canvas.width) {
                videoWidth = canvas.width;
                videoHeight = videoWidth / imgRatio;
            }
            
            const x = (canvas.width - videoWidth) / 2;
            const y = 0;
            
            ctx.drawImage(mainBg, x, y, videoWidth, videoHeight);
        }
        
        if (logoImg.complete && logoImg.naturalWidth > 0) {
            ctx.globalAlpha = 0.6;
            ctx.drawImage(logoImg, 20, 20, 60, 60);
            ctx.globalAlpha = 1.0;
        }
        
        canvasRafId = requestAnimationFrame(animateCanvas);
    }
    animateCanvas();
    
    const canvasStream = canvas.captureStream(30);
    const mixedAudioStream = destination.stream;
    
    const combinedStream = new MediaStream();
    canvasStream.getVideoTracks().forEach(track => combinedStream.addTrack(track));
    mixedAudioStream.getAudioTracks().forEach(track => combinedStream.addTrack(track));
    
    try {
        mediaRecorder = new MediaRecorder(combinedStream, { 
            mimeType: 'video/webm;codecs=vp9,opus' 
        });
    } catch(e) {
        mediaRecorder = new MediaRecorder(combinedStream);
    }
    
    mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) recordedChunks.push(e.data);
    };
    
    mediaRecorder.onstop = async () => {
        const videoBlob = new Blob(recordedChunks, { type: 'video/webm' });
        const url = URL.createObjectURL(videoBlob);
        
        finalBg.src = mainBg.src;
        finalLyrics.innerText = "";
        finalDiv.style.display = "flex";
        downloadRecordingBtn.href = url;
        downloadRecordingBtn.download = `karaoke_${Date.now()}.webm`;
        
        playRecordingBtn.onclick = () => {
            if(!isPlayingRecording){
                playRecordingAudio = new Audio(url);
                playRecordingAudio.play();
                isPlayingRecording=true;
                playRecordingBtn.innerText="⏹ Stop";
                playRecordingAudio.onended=()=>{
                    isPlayingRecording=false; 
                    playRecordingBtn.innerText="▶ Play Recording"; 
                };
            }else{
                playRecordingAudio.pause(); 
                playRecordingAudio.currentTime=0;
                isPlayingRecording=false; 
                playRecordingBtn.innerText="▶ Play Recording";
            }
        };
        
        newRecordingBtn.onclick = () => {
            finalDiv.style.display = "none";
            status.innerText = "Ready 🎤";
            playBtn.style.display="inline-block";
            playBtn.innerText = "▶ Play";
            recordBtn.style.display="inline-block";
            stopBtn.style.display="none";
            if(playRecordingAudio){
                playRecordingAudio.pause();
                playRecordingAudio = null;
            }
            recordedChunks = [];
        };
    };
    
    await new Promise(res=>setTimeout(res,150));
    mediaRecorder.start();
    originalAudio.currentTime=0; accompanimentAudio.currentTime=0;
    await safePlay(originalAudio); await safePlay(accompanimentAudio);
    
    playBtn.style.display="none"; recordBtn.style.display="none"; stopBtn.style.display="inline-block";
    status.innerText="🎙 Recording... (Mic + Music + Video)";
};

stopBtn.onclick = () => {
    try{ mediaRecorder.stop(); }catch(e){}
    try {
        accSource.stop();
        audioContext.close();
        cancelAnimationFrame(canvasRafId);
    } catch(e) {}
    originalAudio.pause(); accompanimentAudio.pause();
    status.innerText="⏹ Processing video...";
    stopBtn.style.display="none";
};
</script>
</body>
</html>
    """ % (lyrics_b64 or "", logo_b64 or "", original_b64 or "", accompaniment_b64 or "")

    html(karaoke_template, height=800, width=1920)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    st.rerun()
