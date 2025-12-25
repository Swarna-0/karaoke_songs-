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
APP_URL = "https://karaoke-project-production.up.railway.app/"

# 🔒 SECURITY: Environment Variables for Password Hashes
ADMIN_HASH = os.getenv("ADMIN_HASH", "")
USER1_HASH = os.getenv("USER1_HASH", "")
USER2_HASH = os.getenv("USER2_HASH", "")

# Base directories - Railway optimized paths
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

# =============== FAST PERSISTENT SESSION DATABASE ===============
@st.cache_resource
def init_session_db():
    """Initialize SQLite database for persistent sessions"""
    conn = sqlite3.connect(session_db_path, check_same_thread=False)
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
    conn.close()

def save_session_fast():
    """Fast session save - minimal writes"""
    try:
        session_id = st.session_state.get('session_id', 'default')
        conn = sqlite3.connect(session_db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO sessions 
                     (session_id, user, role, page, selected_song, last_active)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (session_id,
                   st.session_state.get('user', ''),
                   st.session_state.get('role', ''),
                   st.session_state.get('page', 'Login'),
                   st.session_state.get('selected_song', ''),
                   datetime.now()))
        conn.commit()
        conn.close()
    except:
        pass

def load_session_fast():
    """Fast session load"""
    try:
        session_id = st.session_state.get('session_id', 'default')
        conn = sqlite3.connect(session_db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user, role, page, selected_song FROM sessions WHERE session_id = ?', 
                  (session_id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            st.session_state.user = result[0] if result[0] else None
            st.session_state.role = result[1] if result[1] else None
            st.session_state.page = result[2] if result[2] else "Login"
            st.session_state.selected_song = result[3] if result[3] else None
    except:
        pass

# Initialize once
init_session_db()

# =============== FAST HELPER FUNCTIONS ===============
def file_to_base64_small(path):
    """Optimized base64 for small files only"""
    if os.path.exists(path) and os.path.getsize(path) < 5*1024*1024:  # 5MB limit
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except:
            return ""
    return ""

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_songs():
    """Cached song list"""
    songs = []
    if not os.path.exists(songs_dir):
        return songs
    
    # Simple file scan - no database for speed
    for f in os.listdir(songs_dir):
        if f.endswith("_original.mp3"):
            song_name = f.replace("_original.mp3", "")
            songs.append(song_name)
    return sorted(songs)

def check_session_id():
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

# =============== FAST INITIALIZATION ===============
check_session_id()

# Initialize defaults
defaults = {"user": None, "role": None, "page": "Login", "selected_song": None}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Load session FAST
load_session_fast()

# Logo (cached)
logo_path = os.path.join(logo_dir, "branks3_logo.png")
logo_b64 = file_to_base64_small(logo_path) if os.path.exists(logo_path) else ""

# =============== QUICK DIRECT SONG ACCESS ===============
query_params = st.query_params
if "song" in query_params and st.session_state.page == "Login":
    song_from_url = unquote(query_params["song"])
    songs = get_cached_songs()
    if song_from_url in songs:
        st.session_state.selected_song = song_from_url
        st.session_state.page = "Song Player"
        st.session_state.user = "guest"
        st.session_state.role = "guest"
        save_session_fast()
        st.rerun()

# =============== LOGIN PAGE (UNCHANGED) ===============
if st.session_state.page == "Login":
    save_session_fast()
    
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    header {visibility:hidden;}
    body {background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%);}
    .login-content {padding: 1.8rem 2.2rem 2.2rem 2.2rem;}
    .login-header {display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.8rem; margin-bottom: 1.6rem; text-align: center;}
    .login-header img {width: 60px; height: 60px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.4);}
    .login-title {font-size: 1.6rem; font-weight: 700; width: 100%;}
    .login-sub {font-size: 0.9rem; color: #c3cfdd; margin-bottom: 0.5rem; width: 100%;}
    .credentials-info {background: rgba(5,10,25,0.8); border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; padding: 12px; margin-top: 16px; font-size: 0.85rem; color: #b5c2d2;}
    .stTextInput input {background: rgba(5,10,25,0.7) !important; border-radius: 10px !important; color: white !important; border: 1px solid rgba(255,255,255,0.2) !important; padding: 12px 14px !important;}
    .stTextInput input:focus {border-color: rgba(255,255,255,0.6) !important; box-shadow: 0 0 0 1px rgba(255,255,255,0.3);}
    .stButton button {width: 100%; height: 44px; background: linear-gradient(to right, #1f2937, #020712); border-radius: 10px; font-weight: 600; margin-top: 0.6rem; color: white; border: none;}
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
                    save_session_fast()
                    st.rerun()
                elif username == "user1" and USER1_HASH and hashed_pass == USER1_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    save_session_fast()
                    st.rerun()
                elif username == "user2" and USER2_HASH and hashed_pass == USER2_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    save_session_fast()
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")

        st.markdown("""
        <div style="margin-top:16px;font-size:0.8rem;color:#b5c2d2;text-align:center;padding-bottom:8px;">
            Don't have access? Contact admin.
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

# =============== ADMIN DASHBOARD (OPTIMIZED) ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    save_session_fast()
    
    st.title(f"👑 Admin Dashboard - {st.session_state.user}")
    page_sidebar = st.sidebar.radio("Navigate", ["Upload Songs", "Songs List", "Share Links"], key="admin_nav")

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

            st.success(f"✅ Uploaded: {song_name}")
            st.balloons()
            st.rerun()

    elif page_sidebar == "Songs List":
        st.subheader("🎵 All Songs List")
        songs = get_cached_songs()
        if not songs:
            st.warning("❌ No songs uploaded yet.")
        else:
            for idx, song in enumerate(songs):
                col1, col2, col3 = st.columns([3, 1, 2])
                safe_song = quote(song)
                with col1:
                    st.write(f"**{song}**")
                with col2:
                    if st.button("▶ Play", key=f"play_{song}_{idx}"):
                        st.session_state.selected_song = song
                        st.session_state.page = "Song Player"
                        save_session_fast()
                        st.rerun()
                with col3:
                    share_url = f"{APP_URL}?song={safe_song}"
                    st.markdown(f"[🔗 Share]({share_url})")

    elif page_sidebar == "Share Links":
        st.header("🔗 Manage Shared Links")
        songs = get_cached_songs()
        for song in songs:
            col1, col2 = st.columns([3, 2])
            safe_song = quote(song)
            with col1:
                st.write(f"**{song}**")
            with col2:
                share_url = f"{APP_URL}?song={safe_song}"
                st.markdown(f"[📱 Share Link]({share_url})")
                if st.button("✅ Mark Shared", key=f"share_{song}"):
                    st.success(f"✅ {song} shared!")
                    st.rerun()

    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "Login"
        save_session_fast()
        st.rerun()

# =============== USER DASHBOARD (SIMPLIFIED) ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    save_session_fast()
    
    st.title(f"👤 User Dashboard - {st.session_state.user}")
    st.subheader("🎵 Available Songs")

    songs = get_cached_songs()
    if not songs:
        st.warning("❌ No songs available.")
    else:
        for idx, song in enumerate(songs):
            col1, col2 = st.columns([3,1])
            with col1:
                st.write(f"✅ {song}")
            with col2:
                if st.button("▶ Play", key=f"user_play_{song}_{idx}"):
                    st.session_state.selected_song = song
                    st.session_state.page = "Song Player"
                    save_session_fast()
                    st.rerun()

    if st.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "Login"
        save_session_fast()
        st.rerun()

# =============== ULTRA-FAST SONG PLAYER (RAILWAY OPTIMIZED) ===============
elif st.session_state.page == "Song Player" and st.session_state.selected_song:
    save_session_fast()
    
    selected_song = st.session_state.selected_song
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    div.block-container {padding: 0 !important; margin: 0 !important; width: 100vw !important;}
    html, body {overflow: hidden !important;}
    </style>
    """, unsafe_allow_html=True)

    # Check files exist
    original_path = os.path.join(songs_dir, f"{selected_song}_original.mp3")
    accompaniment_path = os.path.join(songs_dir, f"{selected_song}_accompaniment.mp3")
    
    if not (os.path.exists(original_path) and os.path.exists(accompaniment_path)):
        st.error("❌ Song files missing!")
        if st.button("← Back"):
            st.session_state.page = "Admin Dashboard" if st.session_state.role == "admin" else "User Dashboard"
            st.rerun()
        st.stop()

    # Get lyrics image (small only)
    lyrics_path = ""
    for ext in [".jpg", ".jpeg", ".png"]:
        p = os.path.join(lyrics_dir, f"{selected_song}_lyrics_bg{ext}")
        if os.path.exists(p) and os.path.getsize(p) < 2*1024*1024:  # 2MB limit
            lyrics_path = p
            break

    lyrics_b64 = file_to_base64_small(lyrics_path)
    logo_b64 = file_to_base64_small(logo_path) if os.path.exists(logo_path) else ""

    # RAILWAY-OPTIMIZED LIGHTWEIGHT PLAYER
    lightweight_player = f"""
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>🎤 {selected_song}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #000; color: white; font-family: Arial; height: 100vh; overflow: hidden; }}
        .player {{ width: 100vw; height: 100vh; position: relative; }}
        .bg {{ position: absolute; top: 0; left: 0; width: 100%; height: 85vh; object-fit: contain; object-position: top; }}
        .controls {{ position: absolute; bottom: 20%; width: 100%; text-align: center; }}
        button {{ background: linear-gradient(135deg, #ff0066, #ff66cc); border: none; color: white; padding: 15px 30px; border-radius: 25px; font-size: 18px; margin: 10px; cursor: pointer; box-shadow: 0 5px 20px rgba(255,0,128,0.4); }}
        button:hover {{ transform: scale(1.05); }}
        button:active {{ transform: scale(0.95); }}
        #status {{ position: absolute; top: 20px; width: 100%; text-align: center; font-size: 20px; text-shadow: 2px 2px 10px black; }}
        .back-btn {{ position: absolute; top: 20px; left: 20px; background: rgba(0,0,0,0.7); padding: 10px 20px; border-radius: 20px; font-size: 16px; }}
    </style>
</head>
<body>
    <div class="player">
        <img class="bg" id="bgImg" src="data:image/jpeg;base64,{lyrics_b64}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTkyMCIgaGVpZ2h0PSI5NjAiIGZpbGw9IiMyMjIiLz4='">
        <div id="status">🚀 Fast Player Ready - Click Play!</div>
        
        <audio id="songAudio" preload="auto"></audio>
        
        <div class="controls">
            <button id="playBtn">▶ Play Song</button>
            <button id="recordBtn">🎙 Record</button>
        </div>
        
        <a href="javascript:history.back()" class="back-btn">← Back</a>
    </div>

    <script>
    const playBtn = document.getElementById('playBtn');
    const recordBtn = document.getElementById('recordBtn');
    const status = document.getElementById('status');
    const songAudio = document.getElementById('songAudio');
    let mediaRecorder, recordedChunks = [], isRecording = false;

    // FAST PLAYBACK - Direct file streaming
    playBtn.onclick = async () => {{
        if (songAudio.paused) {{
            songAudio.src = '{APP_URL}media/songs/{selected_song}_original.mp3?' + Date.now();
            songAudio.load();
            await songAudio.play();
            playBtn.textContent = '⏸ Pause';
            status.textContent = '🎵 Playing...';
        }} else {{
            songAudio.pause();
            playBtn.textContent = '▶ Play Song';
            status.textContent = '⏸ Paused';
        }}
    }};

    // QUICK RECORD
    recordBtn.onclick = async () => {{
        if (isRecording) return;
        
        try {{
            const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
            mediaRecorder = new MediaRecorder(stream);
            recordedChunks = [];
            
            mediaRecorder.ondataavailable = e => e.data.size && recordedChunks.push(e.data);
            mediaRecorder.onstop = () => {{
                const blob = new Blob(recordedChunks, {{ type: 'audio/webm' }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'karaoke_' + Date.now() + '.webm';
                a.click();
                stream.getTracks().forEach(track => track.stop());
                status.textContent = '✅ Recording Downloaded!';
            }};
            
            mediaRecorder.start();
            isRecording = true;
            recordBtn.textContent = '⏹ Stop';
            status.textContent = '🎙 Recording... Speak now!';
            
        }} catch(e) {{
            status.textContent = '❌ Mic access denied';
        }}
    }};

    // Auto-resume audio context
    document.addEventListener('click', () => songAudio.play().catch(()=>{{}}), {{ once: true }});
    </script>
</body>
</html>
    """

    # Show lightweight player
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("← Back", key="back_player"):
            st.session_state.page = "Admin Dashboard" if st.session_state.role == "admin" else "User Dashboard"
            save_session_fast()
            st.rerun()

    html(lightweight_player, height=800, width=1920, scrolling=False)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    save_session_fast()
    st.rerun()
