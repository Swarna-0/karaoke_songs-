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

# --------- CONFIG: Update for Railway ----------
APP_URL = "https://karaoke-project-production.up.railway.app/"

# 🔒 SECURITY: Environment Variables
ADMIN_HASH = os.getenv("ADMIN_HASH", "")
USER1_HASH = os.getenv("USER1_HASH", "")
USER2_HASH = os.getenv("USER2_HASH", "")

# Base directories - Railway optimized
base_dir = os.getcwd()
media_dir = os.path.join(base_dir, "media")
songs_dir = os.path.join(media_dir, "songs")
lyrics_dir = os.path.join(media_dir, "lyrics_images")
logo_dir = os.path.join(media_dir, "logo")
shared_links_dir = os.path.join(media_dir, "shared_links")
metadata_path = os.path.join(media_dir, "song_metadata.json")
session_db_path = os.path.join(base_dir, "sessions.db")

# Create directories
os.makedirs(songs_dir, exist_ok=True)
os.makedirs(lyrics_dir, exist_ok=True)
os.makedirs(logo_dir, exist_ok=True)
os.makedirs(shared_links_dir, exist_ok=True)

# =============== FAST PERSISTENT DATABASE ===============
@st.cache_resource
def init_db():
    """Fast SQLite database initialization"""
    conn = sqlite3.connect(session_db_path, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (session_id TEXT PRIMARY KEY, user TEXT, role TEXT, page TEXT, 
                  selected_song TEXT, last_active REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS shared_links
                 (song_name TEXT PRIMARY KEY, shared_by TEXT, active INTEGER, created_at REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS metadata
                 (song_name TEXT PRIMARY KEY, uploaded_by TEXT, timestamp REAL)''')
    conn.commit()
    return conn

db_conn = init_db()

def save_session():
    """Fast session save"""
    try:
        session_id = st.session_state.get('session_id', str(uuid.uuid4()))
        db_conn.execute('''INSERT OR REPLACE INTO sessions 
                         (session_id, user, role, page, selected_song, last_active)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (session_id, st.session_state.get('user'), 
                       st.session_state.get('role'), st.session_state.get('page'),
                       st.session_state.get('selected_song'), time.time()))
        db_conn.commit()
        if 'session_id' not in st.session_state:
            st.session_state.session_id = session_id
    except:
        pass

def load_session():
    """Fast session load"""
    try:
        session_id = st.session_state.get('session_id', 'default')
        result = db_conn.execute('SELECT user, role, page, selected_song FROM sessions WHERE session_id = ?', 
                               (session_id,)).fetchone()
        if result:
            user, role, page, selected_song = result
            if user: st.session_state.user = user
            if role: st.session_state.role = role
            if page: st.session_state.page = page
            if selected_song: st.session_state.selected_song = selected_song
    except:
        pass

def get_shared_links():
    """Fast shared links"""
    try:
        return dict(db_conn.execute('SELECT song_name, shared_by FROM shared_links WHERE active = 1').fetchall())
    except:
        return {}

def get_metadata():
    """Fast metadata"""
    try:
        return dict(db_conn.execute('SELECT song_name, uploaded_by FROM metadata').fetchall())
    except:
        return {}

# =============== FAST FILE HELPERS ===============
@st.cache_data(ttl=300)
def get_uploaded_songs(show_unshared=False):
    """Cached song listing"""
    songs = []
    if not os.path.exists(songs_dir):
        return songs
    
    shared_links = get_shared_links()
    for f in os.listdir(songs_dir):
        if f.endswith("_original.mp3"):
            song_name = f.replace("_original.mp3", "")
            if show_unshared or song_name in shared_links:
                songs.append(song_name)
    return sorted(songs)

def file_to_base64_cached(_path):
    """Fast base64 conversion"""
    if os.path.exists(_path):
        try:
            with open(_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except:
            return ""
    return ""

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# =============== SESSION INIT ===============
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "page" not in st.session_state:
    st.session_state.page = "Login"
if "selected_song" not in st.session_state:
    st.session_state.selected_song = None

# Load session FAST
load_session()

# Global caches
metadata = get_metadata()
shared_links = get_shared_links()

# Logo
logo_path = os.path.join(logo_dir, "branks3_logo.png")
logo_b64 = file_to_base64_cached(logo_path) if os.path.exists(logo_path) else ""

# =============== DIRECT SONG ACCESS ===============
query_params = st.query_params
if "song" in query_params and st.session_state.page == "Login":
    song_from_url = unquote(query_params["song"])
    if song_from_url in shared_links:
        st.session_state.selected_song = song_from_url
        st.session_state.page = "Song Player"
        st.session_state.user = "guest"
        st.session_state.role = "guest"
        save_session()
        st.rerun()

# =============== LOGIN PAGE ===============
if st.session_state.page == "Login":
    save_session()
    
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    header {visibility:hidden;}
    body {background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%);}
    .login-content {padding: 1.8rem 2.2rem 2.2rem;}
    .login-header {display: flex; flex-direction: column; align-items: center; gap: 0.8rem; margin-bottom: 1.6rem; text-align: center;}
    .login-header img {width: 60px; height: 60px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.4);}
    .login-title {font-size: 1.6rem; font-weight: 700;}
    .login-sub {font-size: 0.9rem; color: #c3cfdd;}
    .stTextInput input {background: rgba(5,10,25,0.7) !important; border-radius: 10px !important; color: white !important; border: 1px solid rgba(255,255,255,0.2) !important; padding: 12px 14px !important;}
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
                    save_session()
                    st.rerun()
                elif username == "user1" and USER1_HASH and hashed_pass == USER1_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    save_session()
                    st.rerun()
                elif username == "user2" and USER2_HASH and hashed_pass == USER2_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    save_session()
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")

        st.markdown('</div>', unsafe_allow_html=True)

# =============== ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    save_session()
    st.title(f"👑 Admin Dashboard - {st.session_state.user}")
    
    page_sidebar = st.sidebar.radio("Navigate", ["Upload Songs", "Songs List", "Share Links"])

    if page_sidebar == "Upload Songs":
        st.subheader("📤 Upload New Song")
        col1, col2, col3 = st.columns(3)
        with col1: uploaded_original = st.file_uploader("Original Song", type=["mp3"], key="orig")
        with col2: uploaded_accompaniment = st.file_uploader("Accompaniment", type=["mp3"], key="acc")
        with col3: uploaded_lyrics = st.file_uploader("Lyrics Image", type=["jpg", "jpeg", "png"], key="lyrics")

        if uploaded_original and uploaded_accompaniment and uploaded_lyrics:
            song_name = uploaded_original.name.replace("_original.mp3", "").strip() or os.path.splitext(uploaded_original.name)[0]
            
            # Fast file save
            original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
            acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
            lyrics_path = os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{os.path.splitext(uploaded_lyrics.name)[1]}")

            with open(original_path, "wb") as f: f.write(uploaded_original.getbuffer())
            with open(acc_path, "wb") as f: f.write(uploaded_accompaniment.getbuffer())
            with open(lyrics_path, "wb") as f: f.write(uploaded_lyrics.getbuffer())

            db_conn.execute("INSERT OR REPLACE INTO metadata (song_name, uploaded_by, timestamp) VALUES (?, ?, ?)",
                          (song_name, st.session_state.user, time.time()))
            db_conn.commit()
            st.success(f"✅ Uploaded: {song_name}")
            st.rerun()

    elif page_sidebar == "Songs List":
        st.subheader("🎵 All Songs")
        uploaded_songs = get_uploaded_songs(show_unshared=True)
        if uploaded_songs:
            for idx, song in enumerate(uploaded_songs):
                col1, col2, col3 = st.columns([3, 1, 2])
                with col1: st.write(f"**{song}**")
                with col2:
                    if st.button("▶ Play", key=f"play_{idx}"):
                        st.session_state.selected_song = song
                        st.session_state.page = "Song Player"
                        save_session()
                        st.rerun()
                with col3:
                    st.markdown(f"[🔗 Share]({APP_URL}?song={quote(song)})")

    elif page_sidebar == "Share Links":
        st.header("🔗 Manage Shared Links")
        all_songs = get_uploaded_songs(show_unshared=True)
        for song in all_songs:
            col1, col2 = st.columns([3, 1])
            is_shared = song in shared_links
            with col1: st.write(f"{'✅' if is_shared else '❌'} {song}")
            with col2:
                if st.button("🔄 Toggle", key=f"toggle_{song}"):
                    if is_shared:
                        db_conn.execute("UPDATE shared_links SET active = 0 WHERE song_name = ?", (song,))
                    else:
                        db_conn.execute("INSERT OR REPLACE INTO shared_links (song_name, shared_by, active, created_at) VALUES (?, ?, 1, ?)",
                                      (song, st.session_state.user, time.time()))
                    db_conn.commit()
                    st.rerun()

    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.session_state.page = "Login"
        st.rerun()

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    save_session()
    st.title(f"👤 User Dashboard - {st.session_state.user}")
    
    st.subheader("🎵 Available Songs")
    uploaded_songs = get_uploaded_songs(show_unshared=False)
    
    if uploaded_songs:
        for idx, song in enumerate(uploaded_songs):
            col1, col2 = st.columns([3, 1])
            with col1: st.write(f"✅ {song}")
            with col2:
                if st.button("▶ Play", key=f"user_{idx}"):
                    st.session_state.selected_song = song
                    st.session_state.page = "Song Player"
                    save_session()
                    st.rerun()
    else:
        st.warning("❌ No shared songs available")

    if st.button("🚪 Logout"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.session_state.page = "Login"
        st.rerun()

# =============== OPTIMIZED SONG PLAYER (RAILWAY FAST) ===============
elif st.session_state.page == "Song Player":
    save_session()
    
    # Hide Streamlit UI
    st.markdown("""
    <style>
    [data-testid="stSidebar"], header, footer, .st-emotion-cache-1pahdxg {display:none !important;}
    div.block-container {padding:0 !important; margin:0 !important; width:100vw !important;}
    html, body {overflow:hidden !important;}
    </style>
    """, unsafe_allow_html=True)

    selected_song = st.session_state.selected_song
    if not selected_song:
        st.error("No song selected!")
        st.stop()

    # Fast permission check
    is_admin = st.session_state.role == "admin"
    if st.session_state.role != "admin" and selected_song not in shared_links:
        st.error("❌ Access denied!")
        st.stop()

    # FAST file paths
    original_path = os.path.join(songs_dir, f"{selected_song}_original.mp3")
    accompaniment_path = os.path.join(songs_dir, f"{selected_song}_accompaniment.mp3")
    
    lyrics_path = next((os.path.join(lyrics_dir, f"{selected_song}_lyrics_bg{ext}") 
                       for ext in ['.jpg', '.jpeg', '.png'] if os.path.exists(os.path.join(lyrics_dir, f"{selected_song}_lyrics_bg{ext}"))), "")

    # FAST base64 - Railway optimized
    original_b64 = file_to_base64_cached(original_path)
    accompaniment_b64 = file_to_base64_cached(accompaniment_path)
    lyrics_b64 = file_to_base64_cached(lyrics_path)

    if not original_b64:
        st.error("❌ Song file not found!")
        st.stop()

    # ULTRA-FAST Karaoke Player (Railway optimized)
    karaoke_template = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>🎤 Karaoke</title>
<style>
* {margin:0;padding:0;box-sizing:border-box;}
body {background:#000;font-family:Arial;height:100vh;width:100vw;overflow:hidden;}
.reel-container {width:100%;height:100%;position:relative;background:#111;overflow:hidden;}
#status {position:absolute;top:20px;width:100%;text-align:center;font-size:14px;color:#ccc;z-index:20;}
.reel-bg {position:absolute;top:0;left:0;width:100%;height:85vh;object-fit:contain;object-position:top;}
.controls {position:absolute;bottom:20%;width:100%;text-align:center;z-index:30;}
button {background:linear-gradient(135deg,#ff0066,#ff66cc);border:none;color:white;padding:12px 24px;border-radius:25px;font-size:16px;margin:8px;box-shadow:0 4px 15px rgba(255,0,128,0.4);cursor:pointer;}
button:active {transform:scale(0.95);}
#logoImg {position:absolute;top:20px;left:20px;width:60px;z-index:50;opacity:0.7;}
.back-button {position:absolute;top:20px;right:20px;background:rgba(0,0,0,0.8);color:white;padding:10px 20px;border-radius:25px;text-decoration:none;font-size:14px;z-index:100;}
</style>
</head>
<body>
<div class="reel-container">
    <img class="reel-bg" id="mainBg" src="data:image/jpeg;base64,%%LYRICS%%">
    <img id="logoImg" src="data:image/png;base64,%%LOGO%%">
    <div id="status">Ready to sing! 🎤</div>
    <audio id="originalAudio" src="data:audio/mp3;base64,%%ORIGINAL%%" preload="auto"></audio>
    <audio id="accompaniment" src="data:audio/mp3;base64,%%ACCOMP%%" preload="auto"></audio>
    <div class="controls">
        <button id="playBtn">▶ Play</button>
    </div>
</div>
<a href="javascript:history.back()" class="back-button">← Back</a>

<script>
const playBtn = document.getElementById('playBtn');
const originalAudio = document.getElementById('originalAudio');
const status = document.getElementById('status');

// AUTO-PLAY READY - Railway optimized
document.addEventListener('click', () => {
    if (originalAudio.paused) originalAudio.play().catch(()=>{});
}, {once: true});

playBtn.onclick = () => {
    if (originalAudio.paused) {
        originalAudio.currentTime = 0;
        originalAudio.play();
        playBtn.innerText = '⏸ Pause';
        playBtn.style.background = 'linear-gradient(135deg, #00ff88, #66ffcc)';
        status.innerText = '🎵 Playing...';
    } else {
        originalAudio.pause();
        playBtn.innerText = '▶ Play';
        playBtn.style.background = 'linear-gradient(135deg, #ff0066, #ff66cc)';
        status.innerText = '⏸ Paused';
    }
};

// Auto-resume on focus
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && originalAudio.paused) {
        originalAudio.play().catch(()=>{});
    }
});
</script>
</body>
</html>
"""

    # FAST template replacement
    karaoke_html = karaoke_template.replace("%%LYRICS%%", lyrics_b64)
    karaoke_html = karaoke_html.replace("%%LOGO%%", logo_b64)
    karaoke_html = karaoke_html.replace("%%ORIGINAL%%", original_b64)
    karaoke_html = karaoke_html.replace("%%ACCOMP%%", accompaniment_b64)

    # RENDER FAST
    html(karaoke_html, height=800, width=1920, scrolling=False)

# Cleanup on exit
if st.button("Force Reset", key="reset_all"):
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()
