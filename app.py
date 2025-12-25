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
import asyncio

st.set_page_config(page_title="𝄞 sing-along", layout="wide")

# --------- RAILWAY OPTIMIZED SETTINGS ----------
APP_URL = "https://karaoke-project-production.up.railway.app/"

# 🔒 SECURITY: Environment Variables for Password Hashes
ADMIN_HASH = os.getenv("ADMIN_HASH", "")
USER1_HASH = os.getenv("USER1_HASH", "")
USER2_HASH = os.getenv("USER2_HASH", "")

# Base directories (Railway path fix)
base_dir = os.getcwd()
media_dir = os.path.join(base_dir, "media")
songs_dir = os.path.join(media_dir, "songs")
lyrics_dir = os.path.join(media_dir, "lyrics_images")
logo_dir = os.path.join(media_dir, "logo")
shared_links_dir = os.path.join(media_dir, "shared_links")
metadata_path = os.path.join(media_dir, "song_metadata.json")
session_db_path = os.path.join(base_dir, "session_data.db")

# Create directories
os.makedirs(songs_dir, exist_ok=True)
os.makedirs(lyrics_dir, exist_ok=True)
os.makedirs(logo_dir, exist_ok=True)
os.makedirs(shared_links_dir, exist_ok=True)

# =============== PERFORMANCE OPTIMIZATION ===============
# Cache expensive operations
@st.cache_resource
def get_db_connection():
    """Cached database connection to reduce overhead"""
    return sqlite3.connect(session_db_path, check_same_thread=False)

@st.cache_data(ttl=10)  # Cache for 10 seconds
def load_shared_links_cached():
    """Cached version of shared links loading"""
    return load_shared_links()

@st.cache_data(ttl=30)  # Cache for 30 seconds  
def load_metadata_cached():
    """Cached metadata loading"""
    return load_metadata()

# Audio preloading for faster playback
audio_cache = {}

def preload_audio_files():
    """Preload audio files to cache for faster playback"""
    if not os.path.exists(songs_dir):
        return
    
    # Load only first few songs to avoid memory issues
    songs = os.listdir(songs_dir)[:5]
    for song_file in songs:
        if song_file.endswith("_original.mp3"):
            song_name = song_file.replace("_original.mp3", "")
            original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
            acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
            
            # Read file paths only, not full base64
            if os.path.exists(original_path):
                audio_cache[f"{song_name}_original"] = original_path
            if os.path.exists(acc_path):
                audio_cache[f"{song_name}_accompaniment"] = acc_path

# Initialize preloading
preload_audio_files()

# =============== PERSISTENT SESSION DATABASE ===============
def init_session_db():
    """Initialize SQLite database for persistent sessions"""
    try:
        conn = get_db_connection()
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
        st.error(f"Database init error: {e}")

def save_session_to_db():
    """Save current session to database - optimized"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        session_id = st.session_state.get('session_id', 'default')
        
        c.execute('''INSERT OR REPLACE INTO sessions 
                     (session_id, user, role, page, selected_song, last_active)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (session_id,
                   st.session_state.get('user'),
                   st.session_state.get('role'),
                   st.session_state.get('page'),
                   st.session_state.get('selected_song'),
                   datetime.now()))
        conn.commit()
    except:
        pass

def load_session_from_db():
    """Load session from database - optimized"""
    try:
        session_id = st.session_state.get('session_id', 'default')
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT user, role, page, selected_song FROM sessions WHERE session_id = ?', 
                  (session_id,))
        result = c.fetchone()
        
        if result:
            user, role, page, selected_song = result
            if user and user != 'None':
                st.session_state.user = user
            if role and role != 'None':
                st.session_state.role = role
            if page and page != 'None':
                st.session_state.page = page
            if selected_song and selected_song != 'None':
                st.session_state.selected_song = selected_song
    except:
        pass

def save_shared_link_to_db(song_name, shared_by):
    """Save shared link to database - optimized"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO shared_links 
                     (song_name, shared_by, active, created_at)
                     VALUES (?, ?, ?, ?)''',
                  (song_name, shared_by, True, datetime.now()))
        conn.commit()
    except:
        pass

def load_shared_links_from_db():
    """Load shared links from database - optimized"""
    links = {}
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT song_name, shared_by FROM shared_links WHERE active = 1')
        results = c.fetchall()
        
        for song_name, shared_by in results:
            links[song_name] = {"shared_by": shared_by, "active": True}
    except:
        pass
    return links

def load_metadata_from_db():
    """Load metadata from database - optimized"""
    metadata = {}
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT song_name, uploaded_by FROM metadata')
        results = c.fetchall()
        
        for song_name, uploaded_by in results:
            metadata[song_name] = {"uploaded_by": uploaded_by, "timestamp": str(time.time())}
    except:
        pass
    return metadata

# Initialize database
init_session_db()

# =============== HELPER FUNCTIONS ===============
def file_to_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_metadata():
    """Load metadata from both file and database"""
    file_metadata = {}
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                file_metadata = json.load(f)
        except:
            file_metadata = {}
    
    # Merge with database metadata
    db_metadata = load_metadata_from_db()
    file_metadata.update(db_metadata)
    return file_metadata

def load_shared_links():
    """Load shared links from both file and database"""
    file_links = {}
    if os.path.exists(shared_links_dir):
        for filename in os.listdir(shared_links_dir):
            if filename.endswith('.json'):
                song_name = filename[:-5]
                filepath = os.path.join(shared_links_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        if data.get("active", True):
                            file_links[song_name] = data
                except:
                    pass
    
    # Merge with database links
    db_links = load_shared_links_from_db()
    file_links.update(db_links)
    return file_links

def get_uploaded_songs(show_unshared=False):
    """Get list of uploaded songs - optimized"""
    songs = []
    if not os.path.exists(songs_dir):
        return songs
    
    shared_links = load_shared_links_cached()
    
    for f in os.listdir(songs_dir):
        if f.endswith("_original.mp3"):
            song_name = f.replace("_original.mp3", "")
            if show_unshared or song_name in shared_links:
                songs.append(song_name)
    return sorted(songs)

def check_and_create_session_id():
    """Create unique session ID if not exists"""
    if 'session_id' not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())

# =============== INITIALIZE SESSION ===============
check_and_create_session_id()

# Initialize session state with default values
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "page" not in st.session_state:
    st.session_state.page = "Login"
if "selected_song" not in st.session_state:
    st.session_state.selected_song = None

# Load persistent session data
load_session_from_db()

metadata = load_metadata_cached()

# Logo handling with cache
@st.cache_data
def get_logo_base64():
    default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
    if os.path.exists(default_logo_path):
        with open(default_logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

logo_b64 = get_logo_base64()

# =============== CHECK FOR DIRECT SONG LINK ===============
query_params = st.query_params
if "song" in query_params and st.session_state.page == "Login":
    song_from_url = unquote(query_params["song"])
    shared_links = load_shared_links_cached()
    if song_from_url in shared_links:
        st.session_state.selected_song = song_from_url
        st.session_state.page = "Song Player"
        st.session_state.user = "guest"
        st.session_state.role = "guest"
        save_session_to_db()
        st.rerun()

# =============== RESPONSIVE LOGIN PAGE ===============
if st.session_state.page == "Login":
    # Save session state
    save_session_to_db()
    
    # [Your existing login page CSS and HTML remains exactly the same]
    # ... (copy all your login page code here exactly as you have it)

# =============== ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    # Auto-save session
    save_session_to_db()
    
    st.title(f"👑 Admin Dashboard - {st.session_state.user}")

    page_sidebar = st.sidebar.radio("Navigate", ["Upload Songs", "Songs List", "Share Links"], key="admin_nav")

    if page_sidebar == "Upload Songs":
        # [Your existing upload songs code remains the same]
        # ... (copy all your upload songs code here)

    elif page_sidebar == "Songs List":
        st.subheader("🎵 All Songs List (Admin View)")
        uploaded_songs = get_uploaded_songs(show_unshared=True)
        if not uploaded_songs:
            st.warning("❌ No songs uploaded yet.")
        else:
            for idx, s in enumerate(uploaded_songs):
                col1, col2, col3 = st.columns([3, 1, 2])
                safe_s = quote(s)

                with col1:
                    st.write(f"**{s}** - by {metadata.get(s, {}).get('uploaded_by', 'Unknown')}")
                with col2:
                    if st.button("▶ Play", key=f"play_{s}_{idx}"):
                        st.session_state.selected_song = s
                        st.session_state.page = "Song Player"
                        save_session_to_db()
                        # Pre-load audio for this song
                        original_path = os.path.join(songs_dir, f"{s}_original.mp3")
                        acc_path = os.path.join(songs_dir, f"{s}_accompaniment.mp3")
                        if os.path.exists(original_path):
                            with open(original_path, "rb") as f:
                                audio_cache[f"{s}_original_base64"] = base64.b64encode(f.read()).decode()
                        if os.path.exists(acc_path):
                            with open(acc_path, "rb") as f:
                                audio_cache[f"{s}_accompaniment_base64"] = base64.b64encode(f.read()).decode()
                        st.rerun()
                with col3:
                    share_url = f"{APP_URL}?song={safe_s}"
                    st.markdown(f"[🔗 Share Link]({share_url})")

    elif page_sidebar == "Share Links":
        # [Your existing share links code remains the same]
        # ... (copy all your share links code here)

    if st.sidebar.button("🚪 Logout", key="admin_logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "Login"
        save_session_to_db()
        st.rerun()

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    # [Your existing user dashboard code remains exactly the same]
    # ... (copy all your user dashboard code here)

# =============== OPTIMIZED SONG PLAYER ===============
elif st.session_state.page == "Song Player" and st.session_state.get("selected_song"):
    # Auto-save session
    save_session_to_db()
    
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
    
    # FAST LOADING: Check cache first
    if f"{selected_song}_original_base64" in audio_cache:
        original_b64 = audio_cache[f"{selected_song}_original_base64"]
        accompaniment_b64 = audio_cache[f"{selected_song}_accompaniment_base64"]
    else:
        # Load from files if not in cache
        original_path = os.path.join(songs_dir, f"{selected_song}_original.mp3")
        accompaniment_path = os.path.join(songs_dir, f"{selected_song}_accompaniment.mp3")
        
        original_b64 = file_to_base64(original_path)
        accompaniment_b64 = file_to_base64(accompaniment_path)
        
        # Cache for next time
        audio_cache[f"{selected_song}_original_base64"] = original_b64
        audio_cache[f"{selected_song}_accompaniment_base64"] = accompaniment_b64

    # Find lyrics image
    lyrics_path = ""
    for ext in [".jpg", ".jpeg", ".png"]:
        p = os.path.join(lyrics_dir, f"{selected_song}_lyrics_bg{ext}")
        if os.path.exists(p):
            lyrics_path = p
            break
    
    lyrics_b64 = file_to_base64(lyrics_path)

    # OPTIMIZED HTML PLAYER with preloaded audio
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
.back-button { position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.7); color: white; padding: 8px 16px; border-radius: 20px; text-decoration: none; font-size: 14px; z-index: 100; }
</style>
</head>
<body>

<!-- PRELOAD AUDIO ELEMENTS FOR INSTANT PLAYBACK -->
<audio id="originalAudio" preload="auto" style="display:none;">
  <source src="data:audio/mp3;base64,%%ORIGINAL_B64%%" type="audio/mp3">
</audio>
<audio id="accompaniment" preload="auto" style="display:none;">
  <source src="data:audio/mp3;base64,%%ACCOMP_B64%%" type="audio/mp3">
</audio>

<div class="reel-container" id="reelContainer">
    <img class="reel-bg" id="mainBg" src="data:image/jpeg;base64,%%LYRICS_B64%%" onload="audioLoaded()">
    <img id="logoImg" src="data:image/png;base64,%%LOGO_B64%%">
    <div id="status">Loading audio... ⏳</div>
    <div class="controls">
      <button id="playBtn" disabled>⏳ Loading...</button>
      <button id="recordBtn" disabled>🎙 Record</button>
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
/* ================== GLOBAL STATE ================== */
let mediaRecorder;
let recordedChunks = [];
let playRecordingAudio = null;
let lastRecordingURL = null;

let audioContext, micSource, accSource;
let canvasRafId = null;
let isRecording = false;
let isPlayingRecording = false;
let audioLoadedCount = 0;
const totalAudioToLoad = 2;

/* ================== ELEMENTS ================== */
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

const logoImg = new Image();
logoImg.src = document.getElementById("logoImg").src;

/* ================== FAST AUDIO LOADING ================== */
function audioLoaded() {
    audioLoadedCount++;
    if(audioLoadedCount >= totalAudioToLoad) {
        playBtn.disabled = false;
        recordBtn.disabled = false;
        playBtn.innerText = "▶ Play";
        recordBtn.innerText = "🎙 Record";
        status.innerText = "Ready 🎤";
        console.log("Audio loaded successfully!");
    }
}

// Force audio loading
originalAudio.load();
accompanimentAudio.load();

// Set timeout just in case
setTimeout(() => {
    if(audioLoadedCount < totalAudioToLoad) {
        audioLoadedCount = totalAudioToLoad;
        audioLoaded();
    }
}, 2000);

/* ================== AUDIO CONTEXT FIX ================== */
async function ensureAudioContext() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioContext.state === "suspended") {
        await audioContext.resume();
    }
}

async function safePlay(audio) {
    try {
        await ensureAudioContext();
        audio.currentTime = 0;
        await audio.play();
        return true;
    } catch (e) {
        console.log("Autoplay blocked:", e);
        // Show play button to user
        status.innerText = "Click Play button to start";
        return false;
    }
}

/* ================== PLAY ORIGINAL ================== */
playBtn.onclick = async () => {
    await ensureAudioContext();
    if (originalAudio.paused) {
        const played = await safePlay(originalAudio);
        if(played) {
            playBtn.innerText = "⏸ Pause";
            status.innerText = "🎵 Playing song...";
        }
    } else {
        originalAudio.pause();
        playBtn.innerText = "▶ Play";
        status.innerText = "⏸ Paused";
    }
};

/* ================== CANVAS DRAW ================== */
function drawCanvas() {
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const canvasW = canvas.width;
    const canvasH = canvas.height * 0.85;

    const imgRatio = mainBg.naturalWidth / mainBg.naturalHeight;
    const canvasRatio = canvasW / canvasH;

    let drawW, drawH;
    if (imgRatio > canvasRatio) {
        drawW = canvasW;
        drawH = canvasW / imgRatio;
    } else {
        drawH = canvasH;
        drawW = canvasH * imgRatio;
    }

    const x = (canvasW - drawW) / 2;
    const y = 0;

    ctx.drawImage(mainBg, x, y, drawW, drawH);

    /* LOGO */
    ctx.globalAlpha = 0.6;
    ctx.drawImage(logoImg, 20, 20, 60, 60);
    ctx.globalAlpha = 1;

    canvasRafId = requestAnimationFrame(drawCanvas);
}

/* ================== RECORD ================== */
recordBtn.onclick = async () => {
    if (isRecording) return;
    isRecording = true;

    await ensureAudioContext();
    recordedChunks = [];

    /* MIC */
    const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    micSource = audioContext.createMediaStreamSource(micStream);

    /* ACCOMPANIMENT */
    const accRes = await fetch(accompanimentAudio.src);
    const accBuf = await accRes.arrayBuffer();
    const accDecoded = await audioContext.decodeAudioData(accBuf);

    accSource = audioContext.createBufferSource();
    accSource.buffer = accDecoded;

    const destination = audioContext.createMediaStreamDestination();
    micSource.connect(destination);
    accSource.connect(destination);

    accSource.start();

    canvas.width = 1920;
    canvas.height = 1080;
    drawCanvas();

    const stream = new MediaStream([
        ...canvas.captureStream(30).getTracks(),
        ...destination.stream.getTracks()
    ]);

    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = e => e.data.size && recordedChunks.push(e.data);

    mediaRecorder.onstop = () => {
        cancelAnimationFrame(canvasRafId);

        const blob = new Blob(recordedChunks, { type: "video/webm" });
        const url = URL.createObjectURL(blob);

        if (lastRecordingURL) URL.revokeObjectURL(lastRecordingURL);
        lastRecordingURL = url;

        finalBg.src = mainBg.src;
        finalDiv.style.display = "flex";

        downloadRecordingBtn.href = url;
        downloadRecordingBtn.download = `karaoke_${Date.now()}.webm`;

        playRecordingBtn.onclick = () => {
            if (!isPlayingRecording) {
                playRecordingAudio = new Audio(url);
                playRecordingAudio.play();
                playRecordingBtn.innerText = "⏹ Stop";
                isPlayingRecording = true;
                playRecordingAudio.onended = resetPlayBtn;
            } else {
                resetPlayBtn();
            }
        };
    };

    mediaRecorder.start();

    originalAudio.currentTime = 0;
    accompanimentAudio.currentTime = 0;
    
    // Play both audios
    await safePlay(originalAudio);
    await safePlay(accompanimentAudio);

    playBtn.style.display = "none";
    recordBtn.style.display = "none";
    stopBtn.style.display = "inline-block";
    status.innerText = "🎙 Recording...";
};

/* ================== STOP ================== */
stopBtn.onclick = () => {
    if (!isRecording) return;
    isRecording = false;

    try { mediaRecorder.stop(); } catch {}
    try { accSource.stop(); } catch {}

    originalAudio.pause();
    accompanimentAudio.pause();

    stopBtn.style.display = "none";
    status.innerText = "⏹ Processing...";
};

/* ================== HELPERS ================== */
function resetPlayBtn() {
    if (playRecordingAudio) {
        playRecordingAudio.pause();
        playRecordingAudio.currentTime = 0;
    }
    playRecordingBtn.innerText = "▶ Play Recording";
    isPlayingRecording = false;
}

/* ================== NEW RECORDING ================== */
newRecordingBtn.onclick = () => {
    finalDiv.style.display = "none";

    recordedChunks = [];
    isRecording = false;
    isPlayingRecording = false;

    originalAudio.pause();
    accompanimentAudio.pause();
    originalAudio.currentTime = 0;
    accompanimentAudio.currentTime = 0;

    if (playRecordingAudio) {
        playRecordingAudio.pause();
        playRecordingAudio = null;
    }

    playBtn.style.display = "inline-block";
    recordBtn.style.display = "inline-block";
    stopBtn.style.display = "none";
    playBtn.innerText = "▶ Play";
    status.innerText = "Ready 🎤";
};
</script>
</body>
</html>
"""

    # Replace placeholders
    karaoke_html = karaoke_template.replace("%%LYRICS_B64%%", lyrics_b64 or "")
    karaoke_html = karaoke_html.replace("%%LOGO_B64%%", logo_b64 or "")
    karaoke_html = karaoke_html.replace("%%ORIGINAL_B64%%", original_b64 or "")
    karaoke_html = karaoke_html.replace("%%ACCOMP_B64%%", accompaniment_b64 or "")

    # Add back button
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("← Back", key="back_player"):
            if st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            elif st.session_state.role == "user":
                st.session_state.page = "User Dashboard"
            else:
                st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()

    html(karaoke_html, height=800, width=1920, scrolling=False)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    save_session_to_db()
    st.rerun()

# =============== DEBUG INFO ===============
with st.sidebar:
    if st.session_state.get("role") == "admin":
        if st.checkbox("Show Debug Info", key="debug_toggle"):
            st.write("### Debug Info")
            st.write(f"Page: {st.session_state.get('page')}")
            st.write(f"User: {st.session_state.get('user')}")
            st.write(f"Role: {st.session_state.get('role')}")
            st.write(f"Selected Song: {st.session_state.get('selected_song')}")
            st.write(f"Audio Cache Size: {len(audio_cache)} items")
            st.write(f"Query Params: {dict(st.query_params)}")
            
            if st.button("Clear Cache", key="clear_cache"):
                audio_cache.clear()
                st.success("Cache cleared!")
            
            if st.button("Force Reset", key="debug_reset"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.page = "Login"
                save_session_to_db()
                st.rerun()
