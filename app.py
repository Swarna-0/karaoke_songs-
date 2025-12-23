import streamlit as st
import os
import base64
import json
import hashlib
import requests
import cloudinary
import cloudinary.uploader
import cloudinary.api
from streamlit.components.v1 import html
from urllib.parse import unquote, quote

# --- CLOUDINARY CONFIG ---
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

st.set_page_config(page_title="𝄞 sing-along", layout="wide")

# --------- CONFIG ----------
APP_URL = "https://karaoke-song.onrender.com/"
ADMIN_HASH = os.getenv("ADMIN_HASH", "")
USER1_HASH = os.getenv("USER1_HASH", "")
USER2_HASH = os.getenv("USER2_HASH", "")

# Local directories for metadata and logo
base_dir = os.getcwd()
media_dir = os.path.join(base_dir, "media")
logo_dir = os.path.join(media_dir, "logo")
metadata_path = os.path.join(media_dir, "song_metadata.json")
shared_links_path = os.path.join(media_dir, "shared_links.json")

os.makedirs(logo_dir, exist_ok=True)

# --- HELPER FUNCTIONS ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_url_as_base64(url):
    if not url: return ""
    try:
        response = requests.get(url)
        return base64.b64encode(response.content).decode()
    except Exception as e:
        return ""

def file_to_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def get_uploaded_songs(show_unshared=False):
    meta = load_json(metadata_path)
    links = load_json(shared_links_path)
    if show_unshared:
        return sorted(list(meta.keys()))
    return sorted([s for s in meta.keys() if s in links])

# --- INITIALIZE STATE ---
if "user" not in st.session_state: st.session_state.user = None
if "role" not in st.session_state: st.session_state.role = None
if "page" not in st.session_state: st.session_state.page = "Login"

metadata = load_json(metadata_path)

# Logo logic
default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
logo_b64 = file_to_base64(default_logo_path)

# =============== LOGIN PAGE ===============
if st.session_state.page == "Login":
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    header {visibility:hidden;}
    body { background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%); }
    .login-box { padding: 2rem; background: rgba(0,0,0,0.5); border-radius: 15px; text-align: center; color: white; border: 1px solid rgba(255,255,255,0.1); }
    .stTextInput input { background: rgba(0,0,0,0.3) !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)
    
    left, center, right = st.columns([1, 1.5, 1])
    with center:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        if logo_b64:
            st.markdown(f'<img src="data:image/png;base64,{logo_b64}" style="width:60px; border-radius:50%;">', unsafe_allow_html=True)
        st.markdown('<h3>𝄞 Karaoke Reels</h3>', unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="admin / user1")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            hp = hash_password(password)
            if username == "admin" and hp == ADMIN_HASH:
                st.session_state.user, st.session_state.role, st.session_state.page = "admin", "admin", "Admin Dashboard"
                st.rerun()
            elif (username == "user1" and hp == USER1_HASH) or (username == "user2" and hp == USER2_HASH):
                st.session_state.user, st.session_state.role, st.session_state.page = username, "user", "User Dashboard"
                st.rerun()
            else:
                st.error("Invalid Credentials")
        st.markdown('</div>', unsafe_allow_html=True)

# =============== ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    st.title(f"👑 Admin Dashboard - {st.session_state.user}")
    menu = st.sidebar.radio("Navigate", ["Upload Songs", "Songs List", "Settings"])

    if menu == "Upload Songs":
        st.subheader("📤 Upload to Cloud (Permanent Storage)")
        col1, col2, col3 = st.columns(3)
        with col1: f_orig = st.file_uploader("Original MP3", type=["mp3"])
        with col2: f_acc = st.file_uploader("Accompaniment MP3", type=["mp3"])
        with col3: f_img = st.file_uploader("Lyrics Image", type=["jpg", "png", "jpeg"])

        if st.button("🚀 Process & Store"):
            if f_orig and f_acc and f_img:
                with st.spinner("Uploading to Cloudinary..."):
                    song_name = f_orig.name.replace("_original.mp3", "").strip()
                    # Cloudinary Uploads
                    res_orig = cloudinary.uploader.upload(f_orig, resource_type="video", folder="karaoke/audio")
                    res_acc = cloudinary.uploader.upload(f_acc, resource_type="video", folder="karaoke/audio")
                    res_img = cloudinary.uploader.upload(f_img, resource_type="image", folder="karaoke/images")
                    
                    metadata[song_name] = {
                        "orig": res_orig["secure_url"],
                        "acc": res_acc["secure_url"],
                        "img": res_img["secure_url"],
                        "by": st.session_state.user
                    }
                    save_json(metadata_path, metadata)
                    st.success(f"✅ {song_name} stored permanently!")
                    st.rerun()

    elif menu == "Songs List":
        songs = get_uploaded_songs(show_unshared=True)
        links = load_json(shared_links_path)
        for s in songs:
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.write(f"🎵 **{s}**")
            if c2.button("▶ Play", key=f"p_{s}"):
                st.session_state.selected_song = s
                st.session_state.page = "Song Player"
                st.rerun()
            status = "Shared" if s in links else "Unshared"
            if c3.button(status, key=f"sh_{s}"):
                if s in links: del links[s]
                else: links[s] = True
                save_json(shared_links_path, links)
                st.rerun()
            if c4.button("🗑", key=f"del_{s}"):
                del metadata[s]
                if s in links: del links[s]
                save_json(metadata_path, metadata)
                save_json(shared_links_path, links)
                st.rerun()

    elif menu == "Settings":
        st.subheader("Logo Management")
        l_up = st.file_uploader("Update Logo (PNG)", type=["png"])
        if l_up:
            with open(default_logo_path, "wb") as f: f.write(l_up.getbuffer())
            st.success("Logo updated!")

    if st.sidebar.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard":
    st.title(f"👤 User Dashboard - {st.session_state.user}")
    songs = get_uploaded_songs(show_unshared=False)
    if not songs:
        st.info("No songs shared with you yet.")
    else:
        for s in songs:
            col1, col2 = st.columns([4, 1])
            col1.write(f"🎶 {s}")
            if col2.button("▶ Play", key=f"up_{s}"):
                st.session_state.selected_song = s
                st.session_state.page = "Song Player"
                st.rerun()
    
    if st.sidebar.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

# =============== SONG PLAYER (KARAOKE ENGINE) ===============
elif st.session_state.page == "Song Player" and st.session_state.selected_song:
    s_name = st.session_state.selected_song
    data = metadata.get(s_name)

    st.markdown("""
        <style>
        [data-testid="stSidebar"] {display: none !important;}
        header {visibility: hidden !important;}
        div.block-container { padding: 0 !important; margin: 0 !important; width: 100vw !important; }
        </style>
    """, unsafe_allow_html=True)

    with st.spinner("Fetching audio and lyrics..."):
        b64_orig = get_url_as_base64(data["orig"])
        b64_acc = get_url_as_base64(data["acc"])
        b64_img = get_url_as_base64(data["img"])
        # Logo ni local nundi reload chesthunnam in case upload ayyi unte
        logo_b64 = file_to_base64(default_logo_path)

    # Karaoke Template
    karaoke_template = """
    <!doctype html>
    <html>
    <head>
    <style>
        body { background:#000; margin:0; font-family:sans-serif; height:100vh; overflow:hidden; }
        .reel-container { position:relative; width:100%; height:100vh; background:#111; }
        .reel-bg { width:100%; height:85vh; object-fit:contain; }
        .controls { position:absolute; bottom:15%; width:100%; text-align:center; }
        button { background:linear-gradient(135deg, #ff0066, #ff66cc); border:none; color:white; padding:12px 25px; border-radius:30px; cursor:pointer; margin:5px; }
        #logoImg { position:absolute; top:20px; left:20px; width:60px; opacity:0.7; }
        #status { position:absolute; top:20px; width:100%; text-align:center; color:white; }
        .final-output { position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.9); display:none; flex-direction:column; align-items:center; justify-content:center; z-index:100; }
        canvas { display:none; }
    </style>
    </head>
    <body>
        <div class="reel-container">
            <img class="reel-bg" id="mainBg" src="data:image/jpeg;base64,%%LYRICS_B64%%">
            <img id="logoImg" src="data:image/png;base64,%%LOGO_B64%%">
            <div id="status">Ready to Sing 🎤</div>
            <audio id="originalAudio" src="data:audio/mp3;base64,%%ORIGINAL_B64%%"></audio>
            <audio id="accompaniment" src="data:audio/mp3;base64,%%ACCOMP_B64%%"></audio>
            <div class="controls">
                <button id="playBtn">▶ Play</button>
                <button id="recordBtn">🎙 Start Recording</button>
                <button id="stopBtn" style="display:none; background:red;">⏹ Stop & Save</button>
                <button onclick="window.parent.location.reload();" style="background:#444;">⬅ Exit</button>
            </div>
        </div>

        <div class="final-output" id="finalDiv">
            <h2 style="color:white;">Recording Finished!</h2>
            <video id="recordedVideo" controls style="width:80%; max-height:60vh; border-radius:10px;"></video>
            <div style="margin-top:20px;">
                <a id="downloadBtn" href="#" download="my_karaoke.webm"><button>⬇ Download Reel</button></a>
                <button onclick="location.reload();" style="background:#555;">🔄 Try Again</button>
            </div>
        </div>

        <canvas id="recCanvas" width="1280" height="720"></canvas>

    <script>
    let mediaRecorder, chunks = [], isRecording = false, audioCtx, canvasRaf;
    const playBtn = document.getElementById("playBtn");
    const recordBtn = document.getElementById("recordBtn");
    const stopBtn = document.getElementById("stopBtn");
    const originalAudio = document.getElementById("originalAudio");
    const accompaniment = document.getElementById("accompaniment");
    const status = document.getElementById("status");
    const canvas = document.getElementById("recCanvas");
    const ctx = canvas.getContext("2d");
    const mainBg = document.getElementById("mainBg");

    async function initAudio() {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (audioCtx.state === "suspended") await audioCtx.resume();
    }

    playBtn.onclick = async () => {
        await initAudio();
        if (originalAudio.paused) {
            originalAudio.play(); accompaniment.play();
            playBtn.innerText = "⏸ Pause";
        } else {
            originalAudio.pause(); accompaniment.pause();
            playBtn.innerText = "▶ Play";
        }
    };

    function draw() {
        ctx.fillStyle = "#000"; ctx.fillRect(0,0,canvas.width,canvas.height);
        ctx.drawImage(mainBg, 0, 0, canvas.width, canvas.height);
        canvasRaf = requestAnimationFrame(draw);
    }

    recordBtn.onclick = async () => {
        await initAudio();
        const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const micSource = audioCtx.createMediaStreamSource(micStream);
        const dest = audioCtx.createMediaStreamDestination();
        
        // Combine Mic and Karaoke Track
        const accSource = audioCtx.createMediaElementSource(accompaniment);
        accSource.connect(dest);
        micSource.connect(dest);
        accSource.connect(audioCtx.destination); // For monitoring

        draw();
        const stream = new MediaStream([
            canvas.captureStream(30).getTracks()[0],
            dest.stream.getTracks()[0]
        ]);

        mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
        mediaRecorder.ondataavailable = e => chunks.push(e.data);
        mediaRecorder.onstop = () => {
            const blob = new Blob(chunks, { type: 'video/webm' });
            const url = URL.createObjectURL(blob);
            document.getElementById("recordedVideo").src = url;
            document.getElementById("downloadBtn").href = url;
            document.getElementById("finalDiv").style.display = "flex";
            cancelAnimationFrame(canvasRaf);
        };

        chunks = [];
        mediaRecorder.start();
        originalAudio.currentTime = 0; accompaniment.currentTime = 0;
        originalAudio.play(); accompaniment.play();
        
        recordBtn.style.display = "none";
        stopBtn.style.display = "inline-block";
        status.innerText = "🎙 RECORDING...";
    };

    stopBtn.onclick = () => {
        mediaRecorder.stop();
        originalAudio.pause(); accompaniment.pause();
    };
    </script>
    </body>
    </html>
    """

    final_html = karaoke_template.replace("%%LYRICS_B64%%", b64_img) \
                                 .replace("%%LOGO_B64%%", logo_b64) \
                                 .replace("%%ORIGINAL_B64%%", b64_orig) \
                                 .replace("%%ACCOMP_B64%%", b64_acc)

    html(final_html, height=800, width=1280)

else:
    st.session_state.page = "Login"
    st.rerun()
