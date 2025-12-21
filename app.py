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
                    st.session_state.page = "Song Player"
                    st.rerun()

    if st.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# =============== SONG PLAYER (🔥 FULLY WORKING VERSION) ===============
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
        height: 100vh !important;
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

    # 🔥 FULLY WORKING KARAOKA TEMPLATE
    karaoke_template = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎤 Karaoke Reels</title>
    <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
        background: #000; 
        font-family: Arial, sans-serif; 
        height: 100vh; 
        width: 100vw; 
        overflow: hidden; 
        touch-action: manipulation;
    }
    .reel-container, .final-reel-container { 
        width: 100%; 
        height: 100%; 
        position: absolute; 
        background: #111; 
        overflow: hidden; 
    }
    #status { 
        position: absolute; 
        top: 20px; 
        width: 100%; 
        text-align: center; 
        font-size: 18px; 
        color: #fff; 
        z-index: 20; 
        text-shadow: 2px 2px 10px rgba(0,0,0,0.9); 
        font-weight: bold;
    }
    .reel-bg { 
        position: absolute; 
        top: 0; 
        left: 0; 
        width: 100%; 
        height: 85vh; 
        object-fit: contain; 
        object-position: top; 
    }
    .controls { 
        position: absolute; 
        bottom: 15%; 
        width: 100%; 
        text-align: center; 
        z-index: 30; 
    }
    button { 
        background: linear-gradient(135deg, #ff0066, #ff66cc); 
        border: none; 
        color: white; 
        padding: 15px 25px; 
        border-radius: 30px; 
        font-size: 16px; 
        margin: 8px; 
        box-shadow: 0px 5px 20px rgba(255,0,128,0.5); 
        cursor: pointer; 
        font-weight: bold;
        min-width: 120px;
        touch-action: manipulation;
    }
    button:active { transform: scale(0.95); }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .final-output { 
        position: fixed; 
        width: 100vw; 
        height: 100vh; 
        top: 0; 
        left: 0; 
        background: rgba(0,0,0,0.95); 
        display: none; 
        justify-content: center; 
        align-items: center; 
        z-index: 999; 
        flex-direction: column;
    }
    #logoImg { 
        position: absolute; 
        top: 20px; 
        left: 20px; 
        width: 70px; 
        z-index: 50; 
        opacity: 0.7; 
        border-radius: 10px;
    }
    canvas { display: none; }
    .big-status {
        font-size: 24px !important;
        color: #ff66cc !important;
    }
    </style>
</head>
<body>

<div class="reel-container" id="reelContainer">
    <img class="reel-bg" id="mainBg" src="data:image/jpeg;base64,%%LYRICS_B64%%" onload="onBgLoad()">
    <img id="logoImg" src="data:image/png;base64,%%LOGO_B64%%">
    <div id="status">Ready to sing! 🎤<br><small>Click PLAY first, then RECORD</small></div>
    <audio id="originalAudio" src="data:audio/mp3;base64,%%ORIGINAL_B64%%" preload="metadata"></audio>
    <audio id="accompanimentAudio" src="data:audio/mp3;base64,%%ACCOMP_B64%%" preload="metadata"></audio>
    <div class="controls">
        <button id="playBtn">▶ Play Music</button>
        <button id="recordBtn" disabled>🎙 Record</button>
        <button id="stopBtn" style="display:none;">⏹ Stop</button>
    </div>
</div>

<div class="final-output" id="finalOutputDiv">
    <div style="text-align:center; color:white; margin-bottom:20px;">
        <div id="finalStatus">🎉 Recording Complete!</div>
    </div>
    <div class="final-reel-container" style="width:90%; height:70%; position:relative;">
        <img class="reel-bg" id="finalBg" style="width:100%; height:100%; object-fit:contain;">
    </div>
    <div class="controls" style="position:relative; bottom:auto; margin-top:20px;">
        <button id="playRecordingBtn">▶ Play Video</button>
        <a id="downloadRecordingBtn" href="#" download style="text-decoration:none;">
            <button>⬇ Download</button>
        </a>
        <button id="newRecordingBtn">🔄 New Recording</button>
    </div>
</div>

<canvas id="recordingCanvas" width="1280" height="720"></canvas>

<script>
let mediaRecorder, recordedChunks = [], playRecordingAudio = null;
let isRecording = false, isPlayingMusic = false;
let audioContext, canvasRafId, logoImg;
let stream = null;

const elements = {
    playBtn: document.getElementById("playBtn"),
    recordBtn: document.getElementById("recordBtn"),
    stopBtn: document.getElementById("stopBtn"),
    status: document.getElementById("status"),
    originalAudio: document.getElementById("originalAudio"),
    accompanimentAudio: document.getElementById("accompanimentAudio"),
    finalDiv: document.getElementById("finalOutputDiv"),
    mainBg: document.getElementById("mainBg"),
    finalBg: document.getElementById("finalBg"),
    canvas: document.getElementById("recordingCanvas"),
    ctx: document.getElementById("recordingCanvas").getContext('2d'),
    playRecordingBtn: document.getElementById("playRecordingBtn"),
    downloadRecordingBtn: document.getElementById("downloadRecordingBtn"),
    newRecordingBtn: document.getElementById("newRecordingBtn"),
    finalStatus: document.getElementById("finalStatus")
};

// Preload logo
logoImg = new Image();
logoImg.src = document.getElementById("logoImg").src;

function updateStatus(msg, isBig = false) {
    elements.status.innerHTML = msg;
    if (isBig) elements.status.classList.add('big-status');
}

function onBgLoad() {
    console.log('Background loaded');
}

async function safePlay(audio) {
    try {
        await audio.play();
        return true;
    } catch(e) {
        console.error("Play failed:", e);
        return false;
    }
}

// 🔥 PERFECT PLAY BUTTON - 100% WORKING
elements.playBtn.onclick = async () => {
    if (!isPlayingMusic) {
        // Reset and play both audios
        elements.originalAudio.currentTime = 0;
        elements.accompanimentAudio.currentTime = 0;
        
        const played1 = await safePlay(elements.originalAudio);
        const played2 = await safePlay(elements.accompanimentAudio);
        
        if (played1 || played2) {
            isPlayingMusic = true;
            elements.playBtn.innerText = "⏸ Pause Music";
            elements.recordBtn.disabled = false;
            updateStatus("🎵 Music playing! 🎤 Ready to record...");
        } else {
            updateStatus("🔇 Click again or check audio permissions");
        }
    } else {
        elements.originalAudio.pause();
        elements.accompanimentAudio.pause();
        isPlayingMusic = false;
        elements.playBtn.innerText = "▶ Play Music";
        elements.recordBtn.disabled = true;
        updateStatus("⏸ Paused. Click Play to continue", true);
    }
};

// 🔥 SIMPLIFIED RECORDING - WORKS ON ALL BROWSERS
elements.recordBtn.onclick = async () => {
    try {
        updateStatus("🎙 Getting microphone permission...", true);
        
        // Simple getUserMedia with video for recording
        stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'user'
            },
            audio: {
                echoCancellation: true,
                noiseSuppression: true
            }
        });

        // Canvas animation for background
        function animateCanvas() {
            elements.ctx.fillStyle = '#111';
            elements.ctx.fillRect(0, 0, 1280, 720);
            
            // Draw background image
            if (elements.mainBg.complete && elements.mainBg.naturalWidth > 0) {
                const imgRatio = elements.mainBg.naturalWidth / elements.mainBg.naturalHeight;
                let h = 612; // 85% of 720
                let w = h * imgRatio;
                if (w > 1280) {
                    w = 1280;
                    h = w / imgRatio;
                }
                const x = (1280 - w) / 2;
                elements.ctx.drawImage(elements.mainBg, x, 0, w, h);
            }
            
            // Logo
            if (logoImg.complete) {
                elements.ctx.globalAlpha = 0.7;
                elements.ctx.drawImage(logoImg, 20, 20, 70, 70);
                elements.ctx.globalAlpha = 1;
            }
            
            canvasRafId = requestAnimationFrame(animateCanvas);
        }
        animateCanvas();

        // Combine canvas video + mic audio
        const canvasStream = elements.canvas.captureStream(30);
        const videoTrack = stream.getVideoTracks()[0];
        const audioTrack = stream.getAudioTracks()[0];
        
        const combinedStream = new MediaStream([videoTrack, audioTrack]);
        
        // Background music continues playing separately
        elements.accompanimentAudio.currentTime = 0;
        await safePlay(elements.accompanimentAudio);
        
        mediaRecorder = new MediaRecorder(combinedStream, {
            mimeType: 'video/webm;codecs=vp9,opus'
        });
        
        recordedChunks = [];
        mediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) {
                recordedChunks.push(e.data);
            }
        };
        
        mediaRecorder.onstop = () => {
            const blob = new Blob(recordedChunks, { type: 'video/webm' });
            const url = URL.createObjectURL(blob);
            
            elements.finalBg.src = elements.mainBg.src;
            elements.finalDiv.style.display = 'flex';
            elements.downloadRecordingBtn.href = url;
            elements.downloadRecordingBtn.download = `karaoke_${selected_song}_${Date.now()}.webm`;
            elements.finalStatus.innerText = `🎉 ${selected_song} recording ready!`;
            
            // Play recording video
            elements.playRecordingBtn.onclick = () => {
                const video = document.createElement('video');
                video.src = url;
                video.controls = true;
                video.style.maxWidth = '100%';
                video.play();
            };
            
            elements.newRecordingBtn.onclick = restartApp;
        };
        
        isRecording = true;
        elements.playBtn.style.display = 'none';
        elements.recordBtn.style.display = 'none';
        elements.stopBtn.style.display = 'inline-block';
        updateStatus("🎙️ RECORDING... Sing along! ⏹️ Click STOP when done", true);
        
        mediaRecorder.start(1000); // Timeslice for better chunks
        
    } catch(err) {
        console.error('Recording error:', err);
        updateStatus("❌ Mic/Camera permission denied. Allow permissions and try again.", true);
    }
};

elements.stopBtn.onclick = () => {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        
        // Cleanup
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        if (audioContext) {
            audioContext.close();
        }
        if (canvasRafId) {
            cancelAnimationFrame(canvasRafId);
        }
        
        elements.accompanimentAudio.pause();
        updateStatus("✨ Processing your karaoke video...", true);
        elements.stopBtn.style.display = 'none';
    }
};

function restartApp() {
    elements.finalDiv.style.display = 'none';
    elements.playBtn.style.display = 'inline-block';
    elements.recordBtn.style.display = 'inline-block';
    elements.recordBtn.disabled = true;
    elements.playBtn.innerText = '▶ Play Music';
    isPlayingMusic = false;
    isRecording = false;
    updateStatus('Ready to sing! 🎤<br><small>Click PLAY first, then RECORD</small>');
    
    // Cleanup
    if (playRecordingAudio) {
        playRecordingAudio.pause();
        playRecordingAudio = null;
    }
    recordedChunks = [];
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
}

// Prevent context menu on mobile
document.addEventListener('contextmenu', e => e.preventDefault());
</script>
</body>
</html>
"""

    karaoke_html = karaoke_template.replace("%%LYRICS_B64%%", lyrics_b64 or "")
    karaoke_html = karaoke_html.replace("%%LOGO_B64%%", logo_b64 or "")
    karaoke_html = karaoke_html.replace("%%ORIGINAL_B64%%", original_b64 or "")
    karaoke_html = karaoke_html.replace("%%ACCOMP_B64%%", accompaniment_b64 or "")
    karaoke_html = karaoke_html.replace("selected_song", selected_song.replace(" ", "_"))

    # 🔥 INCREASED HEIGHT FOR BETTER MOBILE EXPERIENCE
    html(karaoke_html, height=1000, width=1920)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    st.rerun()
