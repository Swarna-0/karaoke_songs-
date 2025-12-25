import streamlit as st
import os
import base64
import json
from streamlit.components.v1 import html
import hashlib
from urllib.parse import unquote, quote
import time

st.set_page_config(page_title="𝄞 sing-along", layout="wide", initial_sidebar_state="collapsed")

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

# Initialize session state with default values
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "page" not in st.session_state:
    st.session_state.page = "Login"
if "selected_song" not in st.session_state:
    st.session_state.selected_song = None
if "init" not in st.session_state:
    st.session_state.init = True

metadata = load_metadata()

# Logo handling
default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
logo_b64 = ""
if os.path.exists(default_logo_path):
    logo_b64 = file_to_base64(default_logo_path)
else:
    # Don't show uploader on login page - it causes rerun issues
    pass

# =============== DEPLOYMENT FIX: Add query param handler ===============
# Check for direct song link access
query_params = st.query_params
if "song" in query_params and st.session_state.page == "Login":
    song_from_url = unquote(query_params["song"])
    # Check if song exists and is shared
    shared_links = load_shared_links()
    if song_from_url in shared_links:
        st.session_state.selected_song = song_from_url
        st.session_state.page = "Song Player"
        st.session_state.user = "guest"
        st.session_state.role = "guest"

# =============== RESPONSIVE LOGIN PAGE ===============
if st.session_state.page == "Login":
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none !important;}
    header {visibility:hidden !important;}
    .stDeployButton {display:none !important;}
    
    body {
        background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%);
        margin: 0;
        padding: 0;
    }
    
    .main > div {
        padding-top: 0 !important;
    }

    /* INNER CONTENT PADDING */
    .login-content {
        padding: 1.8rem 2.2rem 2.2rem 2.2rem;
        background: rgba(2, 7, 18, 0.9);
        border-radius: 15px;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }

    /* CENTERED HEADER SECTION */
    .login-header {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.8rem;
        margin-bottom: 1.6rem;
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
        color: white;
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

    /* INPUTS */
    .stTextInput input {
        background: rgba(5,10,25,0.7) !important;
        border-radius: 10px !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        padding: 12px 14px !important;
    }

    .stTextInput input:focus {
        border-color: rgba(255,255,255,0.6) !important;
        box-shadow: 0 0 0 1px rgba(255,255,255,0.3);
    }

    .stButton button {
        width: 100%;
        height: 44px;
        background: linear-gradient(to right, #1f2937, #020712);
        border-radius: 10px;
        font-weight: 600;
        margin-top: 0.6rem;
        color: white;
        border: none;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        background: linear-gradient(to right, #2d3748, #111827);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    
    .stButton button:active {
        transform: translateY(0);
    }
    </style>
    """, unsafe_allow_html=True)

    # -------- CENTER ALIGN COLUMN --------
    left, center, right = st.columns([1, 1.5, 1])

    with center:
        st.markdown('<div class="login-content">', unsafe_allow_html=True)

        # Header
        if logo_b64:
            st.markdown(f"""
            <div class="login-header">
                <img src="data:image/png;base64,{logo_b64}">
                <div class="login-title">𝄞 Karaoke Reels</div>
                <div class="login-sub">Login to continue</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="login-header">
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
                elif username == "user1" and USER1_HASH and hashed_pass == USER1_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                elif username == "user2" and USER2_HASH and hashed_pass == USER2_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
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
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #020617 100%);
    }
    .stButton button {
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        transform: translateY(-1px);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title(f"👑 Admin Dashboard - {st.session_state.user}")
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("### Navigation")
        page_sidebar = st.radio(
            "Navigate", 
            ["Upload Songs", "Songs List", "Share Links"],
            key="admin_nav"
        )
        
        st.markdown("---")
        if st.button("🚪 Logout", key="admin_logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = "Login"
            st.rerun()

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

            metadata[song_name] = {"uploaded_by": st.session_state.user, "timestamp": str(time.time())}
            save_metadata(metadata)
            st.success(f"✅ Uploaded: {song_name}")
            st.balloons()

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
                    if st.button("▶ Play", key=f"admin_play_{s}_{idx}"):
                        st.session_state.selected_song = s
                        st.session_state.page = "Song Player"
                        st.rerun()
                with col3:
                    share_url = f"{APP_URL}?song={safe_s}"
                    st.markdown(f"`{share_url}`")

    elif page_sidebar == "Share Links":
        st.header("🔗 Manage Shared Links")
        all_songs = get_uploaded_songs(show_unshared=True)
        shared_links_data = load_shared_links()

        for idx, song in enumerate(all_songs):
            col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1.5])
            safe_song = quote(song)
            is_shared = song in shared_links_data

            with col1:
                if is_shared:
                    st.success(f"✅ **{song}** - SHARED")
                else:
                    st.warning(f"❌ **{song}** - NOT SHARED")

            with col2:
                if st.button("🔄 Toggle", key=f"toggle_{song}_{idx}"):
                    if is_shared:
                        delete_shared_link(song)
                        st.success(f"✅ {song} unshared!")
                    else:
                        save_shared_link(song, {"shared_by": st.session_state.user, "active": True})
                        share_url = f"{APP_URL}?song={safe_song}"
                        st.success(f"✅ {song} shared!")
                    time.sleep(0.5)
                    st.rerun()

            with col3:
                if is_shared:
                    if st.button("🚫 Unshare", key=f"unshare_{song}_{idx}"):
                        delete_shared_link(song)
                        st.success(f"✅ {song} unshared!")
                        time.sleep(0.5)
                        st.rerun()

            with col4:
                if is_shared:
                    share_url = f"{APP_URL}?song={safe_song}"
                    st.markdown(f"[📱 Open Link]({share_url})")

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #020617 100%);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title(f"👤 User Dashboard - {st.session_state.user}")

    with st.sidebar:
        if st.button("🚪 Logout", key="user_logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = "Login"
            st.rerun()

    st.subheader("🎵 Available Songs (Only Shared Songs)")
    uploaded_songs = get_uploaded_songs(show_unshared=False)

    if not uploaded_songs:
        st.warning("❌ No shared songs available. Contact admin to share songs.")
        st.info("👑 Only admin-shared songs appear here for users.")
    else:
        for idx, song in enumerate(uploaded_songs):
            col1, col2 = st.columns([3,1])
            with col1:
                st.write(f"✅ **{song}** (Shared)")
            with col2:
                if st.button("▶ Play", key=f"user_play_{song}_{idx}"):
                    st.session_state.selected_song = song
                    st.session_state.page = "Song Player"
                    st.rerun()

# =============== SONG PLAYER ===============
elif st.session_state.page == "Song Player" and st.session_state.get("selected_song"):
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none !important;}
    header {visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    footer {visibility: hidden !important;}
    
    .main .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        max-width: 100% !important;
    }
    
    div[data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }
    
    .stButton button {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 1000;
        background: rgba(0,0,0,0.7);
        color: white;
        border: 1px solid rgba(255,255,255,0.3);
    }
    </style>
    """, unsafe_allow_html=True)

    selected_song = st.session_state.get("selected_song", None)
    if not selected_song:
        st.error("No song selected!")
        if st.button("Go Back"):
            if st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            else:
                st.session_state.page = "User Dashboard"
            st.rerun()
        st.stop()

    # Double-check access permission
    shared_links = load_shared_links()
    is_shared = selected_song in shared_links
    is_admin = st.session_state.role == "admin"
    is_guest = st.session_state.role == "guest"

    if not (is_shared or is_admin or is_guest):
        st.error("❌ Access denied! This song is not shared with users.")
        if st.button("Go Back"):
            if st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            else:
                st.session_state.page = "User Dashboard"
            st.rerun()
        st.stop()

    # Find files
    original_path = os.path.join(songs_dir, f"{selected_song}_original.mp3")
    accompaniment_path = os.path.join(songs_dir, f"{selected_song}_accompaniment.mp3")

    lyrics_path = ""
    for ext in [".jpg", ".jpeg", ".png"]:
        p = os.path.join(lyrics_dir, f"{selected_song}_lyrics_bg{ext}")
        if os.path.exists(p):
            lyrics_path = p
            break

    # Convert to base64
    original_b64 = file_to_base64(original_path)
    accompaniment_b64 = file_to_base64(accompaniment_path)
    lyrics_b64 = file_to_base64(lyrics_path)
    
    # Get logo
    logo_b64_display = file_to_base64(default_logo_path) if os.path.exists(default_logo_path) else ""

    # Back button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("← Back", key="back_from_player"):
            if st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            elif st.session_state.role == "user":
                st.session_state.page = "User Dashboard"
            else:
                st.session_state.page = "Login"
            st.rerun()

    # Karaoke HTML
    karaoke_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎤 Karaoke - %%SONG_NAME%%</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: #000;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            height: 100vh;
            width: 100vw;
            overflow: hidden;
        }
        
        .container {
            width: 100%;
            height: 100%;
            position: relative;
        }
        
        .bg-image {
            width: 100%;
            height: 100%;
            object-fit: contain;
            object-position: center;
        }
        
        .logo {
            position: absolute;
            top: 20px;
            left: 20px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            border: 2px solid rgba(255,255,255,0.4);
            z-index: 10;
        }
        
        .status {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            z-index: 10;
        }
        
        .controls {
            position: absolute;
            bottom: 40px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 15px;
            z-index: 10;
        }
        
        .btn {
            background: linear-gradient(135deg, #ff0066, #ff66cc);
            border: none;
            color: white;
            padding: 12px 30px;
            border-radius: 30px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(255,0,128,0.4);
            transition: all 0.3s ease;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(255,0,128,0.6);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .btn-stop {
            background: linear-gradient(135deg, #ff3300, #ff6600);
        }
        
        .lyrics {
            position: absolute;
            bottom: 120px;
            width: 100%;
            text-align: center;
            color: white;
            font-size: 2.5vw;
            font-weight: bold;
            text-shadow: 2px 2px 10px rgba(0,0,0,0.8);
            padding: 0 20px;
            z-index: 5;
        }
        
        .hidden {
            display: none;
        }
        
        .recording-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            display: none;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 100;
        }
        
        .recording-title {
            color: white;
            font-size: 24px;
            margin-bottom: 30px;
        }
        
        .recording-controls {
            display: flex;
            gap: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <img id="bgImage" class="bg-image" src="data:image/jpeg;base64,%%LYRICS_B64%%" alt="Lyrics Background">
        <img id="logo" class="logo" src="data:image/png;base64,%%LOGO_B64%%" alt="Logo">
        <div id="status" class="status">Ready 🎤</div>
        
        <div class="lyrics" id="lyricsText">
            %%SONG_NAME%%
        </div>
        
        <div class="controls">
            <button id="playBtn" class="btn">▶ Play Original</button>
            <button id="recordBtn" class="btn">🎙 Start Recording</button>
            <button id="stopBtn" class="btn btn-stop hidden">⏹ Stop Recording</button>
        </div>
    </div>
    
    <div id="recordingOverlay" class="recording-overlay">
        <div class="recording-title">Recording Complete! 🎉</div>
        <div class="recording-controls">
            <button id="playRecordingBtn" class="btn">▶ Play Recording</button>
            <a id="downloadLink" download="karaoke_recording.webm">
                <button class="btn">⬇ Download</button>
            </a>
            <button id="newRecordingBtn" class="btn">🔄 New Recording</button>
        </div>
    </div>
    
    <!-- Hidden audio elements -->
    <audio id="originalAudio" src="data:audio/mp3;base64,%%ORIGINAL_B64%%"></audio>
    <audio id="accompanimentAudio" src="data:audio/mp3;base64,%%ACCOMP_B64%%"></audio>
    
    <!-- Canvas for recording -->
    <canvas id="recordingCanvas" style="display:none;"></canvas>
    
    <script>
        // Global variables
        let mediaRecorder;
        let recordedChunks = [];
        let isRecording = false;
        let audioContext;
        let canvasStream;
        
        // Elements
        const playBtn = document.getElementById('playBtn');
        const recordBtn = document.getElementById('recordBtn');
        const stopBtn = document.getElementById('stopBtn');
        const status = document.getElementById('status');
        const originalAudio = document.getElementById('originalAudio');
        const accompanimentAudio = document.getElementById('accompanimentAudio');
        const recordingOverlay = document.getElementById('recordingOverlay');
        const playRecordingBtn = document.getElementById('playRecordingBtn');
        const downloadLink = document.getElementById('downloadLink');
        const newRecordingBtn = document.getElementById('newRecordingBtn');
        const canvas = document.getElementById('recordingCanvas');
        const ctx = canvas.getContext('2d');
        const bgImage = document.getElementById('bgImage');
        const logo = document.getElementById('logo');
        
        // Initialize canvas
        canvas.width = 1920;
        canvas.height = 1080;
        
        // Play original audio
        playBtn.addEventListener('click', async () => {
            try {
                if (originalAudio.paused) {
                    await originalAudio.play();
                    playBtn.textContent = '⏸ Pause Original';
                    status.textContent = 'Playing original...';
                } else {
                    originalAudio.pause();
                    playBtn.textContent = '▶ Play Original';
                    status.textContent = 'Paused';
                }
            } catch (error) {
                console.error('Error playing audio:', error);
                status.textContent = 'Error playing audio';
            }
        });
        
        // Start recording
        recordBtn.addEventListener('click', async () => {
            if (isRecording) return;
            
            try {
                isRecording = true;
                status.textContent = 'Setting up recording...';
                
                // Get user media (microphone)
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    }
                });
                
                // Setup audio context
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                
                // Create destination for mixing
                const destination = audioContext.createMediaStreamDestination();
                
                // Add microphone
                const micSource = audioContext.createMediaStreamSource(stream);
                micSource.connect(destination);
                
                // Add accompaniment
                const accSource = audioContext.createMediaStreamSource(accompanimentAudio.captureStream());
                accSource.connect(destination);
                
                // Setup canvas for video recording
                const drawFrame = () => {
                    // Clear canvas
                    ctx.fillStyle = '#000';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    
                    // Draw background image
                    if (bgImage.complete) {
                        const imgRatio = bgImage.naturalWidth / bgImage.naturalHeight;
                        const canvasRatio = canvas.width / (canvas.height * 0.85);
                        
                        let drawWidth, drawHeight;
                        if (imgRatio > canvasRatio) {
                            drawWidth = canvas.width;
                            drawHeight = canvas.width / imgRatio;
                        } else {
                            drawHeight = canvas.height * 0.85;
                            drawWidth = drawHeight * imgRatio;
                        }
                        
                        const x = (canvas.width - drawWidth) / 2;
                        const y = 0;
                        
                        ctx.drawImage(bgImage, x, y, drawWidth, drawHeight);
                    }
                    
                    // Draw logo
                    if (logo.complete) {
                        ctx.globalAlpha = 0.6;
                        ctx.drawImage(logo, 20, 20, 60, 60);
                        ctx.globalAlpha = 1;
                    }
                    
                    // Draw status text
                    ctx.fillStyle = 'white';
                    ctx.font = '24px Arial';
                    ctx.textAlign = 'right';
                    ctx.fillText(status.textContent, canvas.width - 30, 50);
                    
                    if (isRecording) {
                        requestAnimationFrame(drawFrame);
                    }
                };
                
                // Start drawing
                drawFrame();
                
                // Capture canvas stream
                canvasStream = canvas.captureStream(30);
                
                // Combine audio and video streams
                const combinedStream = new MediaStream([
                    ...canvasStream.getVideoTracks(),
                    ...destination.stream.getAudioTracks()
                ]);
                
                // Create media recorder
                mediaRecorder = new MediaRecorder(combinedStream, {
                    mimeType: 'video/webm;codecs=vp9,opus'
                });
                
                recordedChunks = [];
                
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        recordedChunks.push(event.data);
                    }
                };
                
                mediaRecorder.onstop = () => {
                    const blob = new Blob(recordedChunks, { type: 'video/webm' });
                    const url = URL.createObjectURL(blob);
                    
                    // Setup download link
                    downloadLink.href = url;
                    downloadLink.download = `karaoke_${new Date().getTime()}.webm`;
                    
                    // Setup play recording button
                    playRecordingBtn.onclick = () => {
                        const audio = new Audio(url);
                        audio.play();
                    };
                    
                    // Show recording overlay
                    recordingOverlay.style.display = 'flex';
                };
                
                // Start recording
                mediaRecorder.start(1000); // Collect data every second
                
                // Start playback
                originalAudio.currentTime = 0;
                accompanimentAudio.currentTime = 0;
                await Promise.all([
                    originalAudio.play(),
                    accompanimentAudio.play()
                ]);
                
                // Update UI
                recordBtn.classList.add('hidden');
                stopBtn.classList.remove('hidden');
                status.textContent = 'Recording... 🎤';
                
            } catch (error) {
                console.error('Error starting recording:', error);
                status.textContent = 'Error: ' + error.message;
                isRecording = false;
            }
        });
        
        // Stop recording
        stopBtn.addEventListener('click', () => {
            if (!isRecording) return;
            
            isRecording = false;
            
            // Stop recording
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            
            // Stop audio playback
            originalAudio.pause();
            accompanimentAudio.pause();
            
            // Update UI
            stopBtn.classList.add('hidden');
            status.textContent = 'Processing recording...';
        });
        
        // New recording
        newRecordingBtn.addEventListener('click', () => {
            recordingOverlay.style.display = 'none';
            recordBtn.classList.remove('hidden');
            stopBtn.classList.add('hidden');
            playBtn.textContent = '▶ Play Original';
            status.textContent = 'Ready 🎤';
            
            originalAudio.currentTime = 0;
            accompanimentAudio.currentTime = 0;
        });
        
        // Initialize
        window.addEventListener('load', () => {
            status.textContent = 'Ready 🎤';
        });
        
        // Handle page visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && isRecording) {
                stopBtn.click();
            }
        });
    </script>
</body>
</html>
    """

    # Replace placeholders
    karaoke_html = karaoke_template.replace("%%SONG_NAME%%", selected_song)
    karaoke_html = karaoke_html.replace("%%LYRICS_B64%%", lyrics_b64 or "")
    karaoke_html = karaoke_html.replace("%%LOGO_B64%%", logo_b64_display or "")
    karaoke_html = karaoke_html.replace("%%ORIGINAL_B64%%", original_b64 or "")
    karaoke_html = karaoke_html.replace("%%ACCOMP_B64%%", accompaniment_b64 or "")

    # Display the karaoke player
    html(karaoke_html, height=800, scrolling=False)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    st.rerun()

# =============== DEBUG INFO (Hidden by default) ===============
with st.sidebar:
    if st.session_state.get("role") == "admin":
        if st.checkbox("Show Debug Info", key="debug_toggle"):
            st.write("### Debug Info")
            st.write(f"Page: {st.session_state.get('page')}")
            st.write(f"User: {st.session_state.get('user')}")
            st.write(f"Role: {st.session_state.get('role')}")
            st.write(f"Selected Song: {st.session_state.get('selected_song')}")
            st.write(f"Query Params: {dict(st.query_params)}")
            
            if st.button("Force Reset", key="debug_reset"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
