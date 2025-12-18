import streamlit as st
import os
import base64
import json
from streamlit.components.v1 import html
import hashlib
from urllib.parse import unquote, quote

st.set_page_config(page_title="🎙 sing-along", layout="wide")

# NEON Dark Theme CSS for Streamlit
st.markdown("""
<style>
/* ================= GLOBAL DARK THEME ================= */
.stApp {
    background-color: #05070d;
    color: #e6f1ff;
    font-family: 'Poppins', sans-serif;
}

/* ================= PRIMARY NEON BUTTON ================= */
.stButton > button {
    background: linear-gradient(135deg, #00f5ff, #00c8ff);
    color: #021018;
    border: 1px solid rgba(0,245,255,0.6);
    border-radius: 14px;
    padding: 10px 20px;
    font-weight: 600;
    letter-spacing: 0.4px;
    cursor: pointer;

    box-shadow:
        0 0 8px rgba(0,245,255,0.6),
        0 0 16px rgba(0,200,255,0.4),
        inset 0 0 6px rgba(255,255,255,0.3);

    transition: all 0.25s ease;
}

/* Hover Glow */
.stButton > button:hover {
    background: linear-gradient(135deg, #00ffff, #38bdf8);
    transform: translateY(-2px) scale(1.02);

    box-shadow:
        0 0 12px rgba(0,255,255,0.9),
        0 0 28px rgba(56,189,248,0.7),
        inset 0 0 8px rgba(255,255,255,0.35);
}

/* Click Effect */
.stButton > button:active {
    transform: scale(0.97);
    box-shadow:
        0 0 6px rgba(0,255,255,0.6),
        inset 0 0 6px rgba(0,0,0,0.6);
}

/* ================= PLAY / SUCCESS BUTTON ================= */
.stButton > button[data-testid*="play"],
.stButton > button[data-testid*="toggle"] {
    background: linear-gradient(135deg, #22ff88, #00ffcc);
    color: #022015;
    border: 1px solid rgba(0,255,170,0.6);

    box-shadow:
        0 0 10px rgba(0,255,170,0.8),
        0 0 22px rgba(0,255,204,0.5);
}

.stButton > button[data-testid*="play"]:hover {
    box-shadow:
        0 0 14px rgba(0,255,170,1),
        0 0 30px rgba(0,255,204,0.8);
}

/* ================= DANGER / LOGOUT BUTTON ================= */
.stButton > button[data-testid*="logout"] {
    background: linear-gradient(135deg, #ff2a6d, #ff0055);
    color: white;
    border: 1px solid rgba(255,0,85,0.6);

    box-shadow:
        0 0 10px rgba(255,42,109,0.8),
        0 0 22px rgba(255,0,85,0.6);
}

.stButton > button[data-testid*="logout"]:hover {
    box-shadow:
        0 0 14px rgba(255,42,109,1),
        0 0 32px rgba(255,0,85,0.9);
}

/* ================= INPUT BOXES ================= */
.stTextInput > div > div > input {
    background: #0b1220;
    color: #e6f1ff;
    border-radius: 10px;
    border: 1px solid rgba(0,245,255,0.35);
    padding: 10px;

    box-shadow: inset 0 0 6px rgba(0,245,255,0.2);
}

/* ================= SIDEBAR ================= */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #030712, #050b1a);
    border-right: 1px solid rgba(0,245,255,0.15);
}

/* ================= METRICS / RADIO ================= */
.stMetric, .stRadio > div {
    background: #0b1220;
    border-radius: 12px;
    border: 1px solid rgba(0,245,255,0.2);
}
</style>
""", unsafe_allow_html=True)


# --------- CONFIG: set your deployed app URL here ----------
APP_URL = "https://karaoke-song.onrender.com/"
# ----------------------------------------------------------

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
    for filename in os.listdir(shared_links_dir):
        if filename.endswith('.json'):
            song_name = filename[:-5]
            with open(os.path.join(shared_links_dir, filename), 'r') as f:
                try:
                    links[song_name] = json.load(f)
                except:
                    links[song_name] = {}
    return links

def save_shared_link(song_name, link_data):
    with open(os.path.join(shared_links_dir, f"{song_name}.json"), 'w') as f:
        json.dump(link_data, f)

# Get songs function
def get_uploaded_songs():
    songs = []
    if not os.path.exists(songs_dir):
        return songs
    for f in os.listdir(songs_dir):
        if f.endswith("_original.mp3"):
            songs.append(f.replace("_original.mp3", ""))
    return sorted(songs)

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "page" not in st.session_state:
    st.session_state.page = "Login"
if "selected_song" not in st.session_state:
    st.session_state.selected_song = None
if "shared_song" not in st.session_state:
    st.session_state.shared_song = None

# Logo
default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
if not os.path.exists(default_logo_path):
    logo_upload = st.file_uploader("Upload Logo (PNG) (optional)", type=["png"], key="logo_upload")
    if logo_upload:
        with open(default_logo_path, "wb") as f:
            f.write(logo_upload.getbuffer())
        st.rerun()
logo_b64 = file_to_base64(default_logo_path)

# Load metadata and shared links
metadata = load_metadata()
shared_links = load_shared_links()

# Handle direct URL ?song=... (deep link)
query_params = st.query_params
direct_song = query_params.get("song", None)

if direct_song:
    try:
        ds_decoded = unquote(direct_song) 
        candidate_path = os.path.join(songs_dir, f"{ds_decoded}_original.mp3")
        if os.path.exists(candidate_path):
            st.session_state.selected_song = ds_decoded
            st.session_state.page = "Song Player"
        elif os.path.exists(os.path.join(songs_dir, f"{direct_song}_original.mp3")):
            st.session_state.selected_song = direct_song
            st.session_state.page = "Song Player"
    except Exception as e:
        pass

# =============== LOGIN PAGE ===============
if st.session_state.page == "Login":
    if st.session_state.get("selected_song"):
        st.session_state.page = "Song Player"
        st.rerun()

    st.title("🎤 Karaoke Reels - Login")

    col1, col2 = st.columns([1,1])
    with col1:
        st.subheader("👤 User Login")
        username = st.text_input("Username", key="user_login")
        password = st.text_input("Password", type="password", key="user_pass")
        if st.button("User Login", key="user_login_btn"):
            if username == "user1" and USER1_HASH and hash_password(password) == USER1_HASH:
                st.session_state.user = username
                st.session_state.role = "user"
                st.session_state.page = "User Dashboard"
                st.rerun()
            elif username == "user2" and USER2_HASH and hash_password(password) == USER2_HASH:
                st.session_state.user = username
                st.session_state.role = "user"
                st.session_state.page = "User Dashboard"
                st.rerun()
            else:
                st.error("❌ wrong credentials!")

    with col2:
        st.subheader("👑 Admin Login")
        admin_user = st.text_input("Admin Username", key="admin_login")
        admin_pass = st.text_input("Admin Password", type="password", key="admin_pass")
        if st.button("Admin Login", key="admin_login_btn"):
            if admin_user == "admin" and ADMIN_HASH and hash_password(admin_pass) == ADMIN_HASH:
                st.session_state.user = admin_user
                st.session_state.role = "admin"
                st.session_state.page = "Admin Dashboard"
                st.rerun()
            else:
                st.error("❌ wrong admin credentials!")

    # 🔒 SECURITY NOTICE
    st.warning("🔒 **Security Notice**: Credentials are now managed via Environment Variables. Contact admin for access.")

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
            song_name = uploaded_original.name
            if song_name.endswith("_original.mp3"):
                song_name = song_name.replace("_original.mp3", "")
            else:
                song_name = os.path.splitext(song_name)[0]

            with open(os.path.join(songs_dir, f"{song_name}_original.mp3"), "wb") as f:
                f.write(uploaded_original.getbuffer())
            with open(os.path.join(songs_dir, f"{song_name}_accompaniment.mp3"), "wb") as f:
                f.write(uploaded_accompaniment.getbuffer())
            ext = os.path.splitext(uploaded_lyrics_image.name)[1]
            with open(os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{ext}"), "wb") as f:
                f.write(uploaded_lyrics_image.getbuffer())

            metadata[song_name] = {"uploaded_by": st.session_state.user}
            save_metadata(metadata)
            st.success(f"✅ Uploaded: **{song_name}**")
            st.rerun()

    elif page_sidebar == "Songs List":
        st.subheader("🎵 Songs List")
        uploaded_songs = get_uploaded_songs()
        if not uploaded_songs:
            st.warning("❌ No songs uploaded yet.")
        else:
            for s in uploaded_songs:
                col1, col2, col3 = st.columns([3, 1, 2])
                safe_s = quote(s)
                
                with col1:
                    st.write(f"**{s}** - by {metadata.get(s, {}).get('uploaded_by', 'Unknown')}")
                with col2:
                    if st.button("▶ Play", key=f"play_{s}"):
                        st.session_state.selected_song = s
                        st.session_state.page = "Song Player"
                        st.rerun()
                with col3:
                    share_url = f"{APP_URL}?song={safe_s}"
                    st.markdown(f"🔗 **[Share Link]({share_url})**", unsafe_allow_html=True) 

    elif page_sidebar == "Share Links":
        st.header("🔗 Manage Shared Links")
        uploaded_songs = get_uploaded_songs()
        shared_links_data = load_shared_links()

        for song in uploaded_songs:
            col1, col2, col3 = st.columns([3, 1, 2])
            safe_song = quote(song)
            
            with col1:
                link_status = "✅ Shared" if song in shared_links_data else "❌ Not Shared"
                st.write(f"**{song}** - {link_status}")
            with col2:
                if st.button("Toggle", key=f"toggle_{song}"):
                    if song in shared_links_data:
                        try:
                            os.remove(os.path.join(shared_links_dir, f"{song}.json"))
                        except Exception:
                            pass
                        st.success(f"**{song}** unshared!")
                    else:
                        save_shared_link(song, {"shared_by": st.session_state.user, "active": True})
                        share_url = f"{APP_URL}?song={safe_song}"
                        st.success(f"**{song}** shared! Link: {share_url}")
                    st.rerun()
            with col3:
                if song in shared_links_data:
                    share_url = f"{APP_URL}?song={safe_song}"
                    st.link_button("📱 Open", url=share_url)

    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    st.title(f"👤 User Dashboard - {st.session_state.user}")

    st.subheader("Available Songs")
    st.warning("❌ No songs available here.")

    if st.session_state.get("selected_song"):
        direct = st.session_state.selected_song
        if direct in get_uploaded_songs():
            st.success(f"🎉 Direct access: **{direct}**")
            if st.button(f"▶ Play {direct}"):
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

    # NEON Karaoke Player Template
    karaoke_template = """
    <!doctype html>
    <html>
    <head>
    <meta charset="utf-8">
    <title>Karaoke Reels</title>
    <style>
    * { box-sizing: border-box; }
    html, body {
    margin:0; padding:0; width:100vw; height:100vh; overflow:hidden;
    background: linear-gradient(135deg, #0a0e17 0%, #1a1f2e 50%, #16213e 100%);
    font-family: 'Poppins', Arial, sans-serif; color:#e1e5e9;
    }
    .reel-container {width:100vw;height:100vh;position:relative;background:#111;display:flex;align-items:center;justify-content:center;flex-direction:column;}
    .reel-bg {max-width:100%;max-height:75vh;object-fit:contain;border-radius:12px;box-shadow: 0 0 40px rgba(0,212,255,0.3);}
    .controls {position:relative;margin-top:20px;text-align:center;z-index:30;}
    button, a {
        background: linear-gradient(135deg, #00d4ff, #0099cc);
        border: 2px solid rgba(0,212,255,0.4);
        color: white;
        padding: 14px 28px;
        border-radius: 30px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        margin: 10px;
        box-shadow: 
            0 0 25px rgba(0,212,255,0.5),
            0 6px 25px rgba(0,212,255,0.3),
            inset 0 1px 0 rgba(255,255,255,0.2);
        transition: all 0.4s ease;
        min-width: 100px;
        text-decoration: none;
        display: inline-block;
        text-shadow: 0 0 12px rgba(0,212,255,0.6);
        position: relative;
        overflow: hidden;
    }
    button::before, a::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        transition: left 0.5s;
    }
    button:hover::before, a:hover::before { left: 100%; }
    button:hover, a:hover {
        transform: translateY(-3px);
        box-shadow: 
            0 0 40px rgba(0,212,255,0.7),
            0 8px 30px rgba(0,212,255,0.4);
        border-color: rgba(0,212,255,0.8);
    }
    button:active, a:active {
        transform: scale(0.97) translateY(0);
    }
    #playBtn {
        background: linear-gradient(135deg, #00ff88, #00cc6a);
        border-color: rgba(0,255,136,0.5);
        box-shadow: 
            0 0 25px rgba(0,255,136,0.5),
            0 6px 25px rgba(0,255,136,0.3);
        text-shadow: 0 0 12px rgba(0,255,136,0.6);
    }
    #playBtn.pause-state {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border-color: rgba(99,102,241,0.5);
        box-shadow: 
            0 0 25px rgba(99,102,241,0.5),
            0 6px 25px rgba(99,102,241,0.3);
        text-shadow: 0 0 12px rgba(99,102,241,0.6);
    }
    #recordBtn {
        background: linear-gradient(135deg, #ff4757, #ff3742);
        border-color: rgba(255,71,87,0.5);
        box-shadow: 
            0 0 25px rgba(255,71,87,0.5),
            0 6px 25px rgba(255,71,87,0.3);
        text-shadow: 0 0 12px rgba(255,71,87,0.6);
    }
    #stopBtn, #newBtn {
        background: linear-gradient(135deg, #6b7280, #9ca3af);
        border-color: rgba(107,114,128,0.4);
        box-shadow: 
            0 0 20px rgba(107,114,128,0.4),
            0 4px 20px rgba(107,114,128,0.2);
        text-shadow: 0 0 8px rgba(107,114,128,0.5);
    }
    #playRecordingBtn {
        background: linear-gradient(135deg, #00ff88, #00cc6a);
        border-color: rgba(0,255,136,0.5);
        box-shadow: 
            0 0 25px rgba(0,255,136,0.5),
            0 6px 25px rgba(0,255,136,0.3);
        text-shadow: 0 0 12px rgba(0,255,136,0.6);
    }
    #downloadBtn {
        background: linear-gradient(135deg, #ffd700, #ffed4a);
        color: #1a1f2e;
        border-color: rgba(255,215,0,0.6);
        box-shadow: 
            0 0 25px rgba(255,215,0,0.5),
            0 6px 25px rgba(255,215,0,0.3);
        text-shadow: 0 0 12px rgba(255,215,0,0.6);
        font-weight: 700;
    }
    #status {position:absolute;top:20px;width:100%;text-align:center;font-size:16px;color:#00d4ff;text-shadow: 0 0 15px rgba(0,212,255,0.8);}
    #logoImg {position:absolute;top:20px;left:20px;width:70px;opacity:0.9;z-index:40;filter: drop-shadow(0 0 10px rgba(0,212,255,0.5));}
    .final-screen {display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(10,14,23,0.98);justify-content:center;align-items:center;flex-direction:column;z-index:999;gap:15px;}
    #canvasPreview { display:none; }
    .note { font-size:14px; color:#a0a0a0; margin-top:10px; text-shadow: 0 0 10px rgba(0,212,255,0.2); }
    .download-container { display: flex; align-items: center; justify-content: center; gap: 15px; margin: 10px; }
    </style>
    </head>
    <body>
    <div class="reel-container" id="mainScreen">
    <img id="lyricsImg" class="reel-bg" src="data:image/jpeg;base64,%%LYRICS_B64%%" onerror="this.onerror=null; this.src='';">
    <img id="logoImg" src="data:image/png;base64,%%LOGO_B64%%">
    <div id="status">Ready 🎤</div>
    <audio id="originalAudio" src="data:audio/mp3;base64,%%ORIGINAL_B64%%"></audio>
    <audio id="accompaniment" src="data:audio/mp3;base64,%%ACCOMP_B64%%"></audio>
    <div class="controls">
    <button id="playBtn">▶ Play</button>
    <button id="recordBtn">🎙 Record</button>
    <button id="stopBtn" style="display:none;">⏹ Stop</button>
    </div>
    <div class="note">Recording happens in your browser. Play Recording in same page.</div>
    </div>
    <div class="final-screen" id="finalScreen">
    <div style="text-align:center;"><img id="finalPreviewImg" class="reel-bg" style="max-height:60vh;"></div>
    <div class="download-container">
    <button id="playRecordingBtn">▶ Play Recording</button>
    <a id="downloadBtn" download="karaoke_output.webm">⬇ Download</a>
    <button id="newBtn">🔄 Create New</button>
    </div>
    <div class="note">Recording playback stays on the same page.</div>
    </div>
    <canvas id="canvasPreview"></canvas>
    <script>
    let mediaRecorder, recordedChunks = [], mixedBlob = null, playRecordingAudio = null, isPlaying = false;
    const original = document.getElementById('originalAudio'), acc = document.getElementById('accompaniment');
    const status = document.getElementById('status');
    const playBtn = document.getElementById('playBtn'), recordBtn = document.getElementById('recordBtn'), stopBtn = document.getElementById('stopBtn');
    const mainScreen = document.getElementById('mainScreen'), finalScreen = document.getElementById('finalScreen');
    const playRecordingBtn = document.getElementById('playRecordingBtn'), downloadBtn = document.getElementById('downloadBtn'), newBtn = document.getElementById('newBtn');
    const lyricsImg = document.getElementById('lyricsImg'), finalPreviewImg = document.getElementById('finalPreviewImg');
    const canvas = document.getElementById('canvasPreview'), ctx = canvas.getContext('2d');
    const logoImg = new Image(); logoImg.src = "data:image/png;base64,%%LOGO_B64%%";
    
    async function safePlay(a){try{await a.play();}catch(e){console.log('play blocked',e);}}
    
    playBtn.onclick = async () => {
        if(original.paused){
            await safePlay(original);
            playBtn.innerText = "⏸ Pause";
            playBtn.classList.add('pause-state');
            status.innerText="🎵 Playing Song...";
        } else {
            original.pause();
            playBtn.innerText = "▶ Play";
            playBtn.classList.remove('pause-state');
            status.innerText="⏸ Paused";
        }
    };
    
    recordBtn.onclick = async () => {
        recordedChunks = []; status.innerText="🎙 Preparing mic...";
        let micStream; 
        try {micStream = await navigator.mediaDevices.getUserMedia({audio:{ echoCancellation:true, noiseSuppression:true },video:false});} 
        catch(err){alert('Allow microphone access');return;}
        
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)(); 
        const micSource = audioCtx.createMediaStreamSource(micStream);
        const accResp = await fetch(acc.src); 
        const accBuf = await accResp.arrayBuffer(); 
        const accDecoded = await audioCtx.decodeAudioData(accBuf);
        const accSource = audioCtx.createBufferSource(); 
        accSource.buffer = accDecoded; 
        const dest = audioCtx.createMediaStreamDestination();
        const micGain = audioCtx.createGain(); 
        micGain.gain.value=1.0; 
        const accGain = audioCtx.createGain(); 
        accGain.gain.value=0.7;
        micSource.connect(micGain).connect(dest); 
        accSource.connect(accGain).connect(dest);
        const accOutSource = audioCtx.createBufferSource(); 
        accOutSource.buffer = accDecoded; 
        accOutSource.connect(audioCtx.destination);
        accSource.start(); 
        accOutSource.start(); 
        await new Promise(res=>setTimeout(res,150));
        
        const img = lyricsImg; 
        const w = img.naturalWidth||1280; 
        const h = img.naturalHeight||720; 
        canvas.width=w; 
        canvas.height=h; 
        let rafId;
        function drawFrame(){
            ctx.fillStyle='#000';
            ctx.fillRect(0,0,canvas.width,canvas.height);
            if(img && img.src){
                const iw=img.naturalWidth||canvas.width;
                const ih=img.naturalHeight||canvas.height;
                const scale=Math.max(canvas.width/iw,canvas.height/ih);
                const dw=iw*scale;
                const dh=ih*scale;
                const dx=(canvas.width-dw)/2;
                const dy=(canvas.height-dh)/2;
                ctx.drawImage(img,dx,dy,dw,dh);
            }
            if(logoImg.complete){
                const logoWidth = 100;
                const logoHeight = logoImg.naturalHeight * (logoWidth / logoImg.naturalWidth);
                ctx.globalAlpha = 0.7;
                ctx.drawImage(logoImg, 20, 20, logoWidth, logoHeight);
                ctx.globalAlpha = 1.0;
            }
            rafId=requestAnimationFrame(drawFrame);
        }
        drawFrame();
        
        const canvasStream = canvas.captureStream(25); 
        const mixedAudioStream = dest.stream; 
        const combinedStream = new MediaStream();
        canvasStream.getVideoTracks().forEach(t => combinedStream.addTrack(t)); 
        mixedAudioStream.getAudioTracks().forEach(t => combinedStream.addTrack(t));
        
        try{mediaRecorder = new MediaRecorder(combinedStream, {mimeType:'video/webm;codecs=vp8,opus'});}catch(e){mediaRecorder = new MediaRecorder(combinedStream);}
        mediaRecorder.ondataavailable = (e) => {if(e.data && e.data.size > 0) recordedChunks.push(e.data);}; 
        mediaRecorder.start();
        original.currentTime=0; 
        acc.currentTime=0; 
        try{ await original.play(); }catch(e){}
        try{ await acc.play(); }catch(e){}
        
        playBtn.style.display = "none"; 
        recordBtn.style.display = "none"; 
        stopBtn.style.display = "inline-block"; 
        status.innerText = "🎙 Recording...";
        
        original.onended = async () => { stopRecording(); }; 
        stopBtn.onclick = async () => { stopRecording(); };
        
        async function stopRecording(){
            try{ mediaRecorder.stop(); }catch(e){}
            try{ accSource.stop(); accOutSource.stop(); audioCtx.close(); }catch(e){}
            cancelAnimationFrame(rafId); 
            try{ original.pause(); acc.pause(); }catch(e){}
            try{ micStream.getTracks().forEach(t=>t.stop()); }catch(e){}
            status.innerText="⏳ Processing mix... Please wait"; 
            stopBtn.style.display = "none";
            
            mediaRecorder.onstop = async () => {
                mixedBlob = new Blob(recordedChunks, { type:'video/webm' }); 
                const url = URL.createObjectURL(mixedBlob);
                finalPreviewImg.src = lyricsImg.src; 
                downloadBtn.href = url; 
                downloadBtn.setAttribute('download', `karaoke_output_${Date.now()}.webm`);
                mainScreen.style.display = 'none'; 
                finalScreen.style.display = 'flex';
                
                playRecordingBtn.onclick = () => {
                    if (!mixedBlob) return; 
                    if (!isPlaying) {
                        playRecordingAudio = new Audio(url); 
                        playRecordingAudio.play(); 
                        isPlaying = true; 
                        playRecordingBtn.innerText = "⏹ Stop";
                        playRecordingAudio.onended = () => {
                            isPlaying = false; 
                            playRecordingBtn.innerText = "▶ Play Recording";
                        };
                    } else {
                        playRecordingAudio.pause(); 
                        playRecordingAudio.currentTime = 0; 
                        isPlaying = false; 
                        playRecordingBtn.innerText = "▶ Play Recording";
                    }
                };
                
                newBtn.onclick = () => {
                    finalScreen.style.display = 'none'; 
                    mainScreen.style.display = 'flex'; 
                    status.innerText = "Ready 🎤"; 
                    playBtn.style.display = "inline-block"; 
                    playBtn.innerText = "▶ Play";
                    playBtn.classList.remove('pause-state');
                    recordBtn.style.display = "inline-block"; 
                    stopBtn.style.display = "none"; 
                    if(playRecordingAudio){
                        playRecordingAudio.pause(); 
                        playRecordingAudio = null; 
                        isPlaying = false;
                    } 
                    mixedBlob = null; 
                    recordedChunks = [];
                };
            };
        }
    };
    </script>
    </body>
    </html>
    """

    karaoke_html = karaoke_template.replace("%%LYRICS_B64%%", lyrics_b64 or "")
    karaoke_html = karaoke_html.replace("%%LOGO_B64%%", logo_b64 or "")
    karaoke_html = karaoke_html.replace("%%ORIGINAL_B64%%", original_b64 or "")
    karaoke_html = karaoke_html.replace("%%ACCOMP_B64%%", accompaniment_b64 or "")

    html(karaoke_html, height=700, width=1920)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    st.rerun()
