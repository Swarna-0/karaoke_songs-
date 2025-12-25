import streamlit as st
import os
import base64
import json
from streamlit.components.v1 import html
import hashlib
from urllib.parse import unquote, quote

# --- INITIAL SETUP ---
st.set_page_config(page_title="𝄞 sing-along", layout="wide")

# --------- CONFIG ----------
APP_URL = "https://karaoke-song.onrender.com/"

# 🔒 SECURITY: Environment Variables
ADMIN_HASH = os.getenv("ADMIN_HASH", "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918") # Default 'admin' if not set
USER1_HASH = os.getenv("USER1_HASH", "")
USER2_HASH = os.getenv("USER2_HASH", "")

# Directories
base_dir = os.getcwd()
media_dir = os.path.join(base_dir, "media")
songs_dir = os.path.join(media_dir, "songs")
lyrics_dir = os.path.join(media_dir, "lyrics_images")
logo_dir = os.path.join(media_dir, "logo")
shared_links_dir = os.path.join(media_dir, "shared_links")
metadata_path = os.path.join(media_dir, "song_metadata.json")

for d in [songs_dir, lyrics_dir, logo_dir, shared_links_dir]:
    os.makedirs(d, exist_ok=True)

# --- HELPER FUNCTIONS ---
def file_to_base64(path):
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_metadata():
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_metadata(data):
    with open(metadata_path, "w") as f:
        json.dump(data, f, indent=2)

def load_shared_links():
    links = {}
    if not os.path.exists(shared_links_dir): return links
    for filename in os.listdir(shared_links_dir):
        if filename.endswith('.json'):
            song_name = filename[:-5]
            try:
                with open(os.path.join(shared_links_dir, filename), 'r') as f:
                    data = json.load(f)
                    if data.get("active", True): links[song_name] = data
            except: pass
    return links

def save_shared_link(song_name, link_data):
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    with open(filepath, 'w') as f:
        json.dump(link_data, f)

def delete_shared_link(song_name):
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    if os.path.exists(filepath): os.remove(filepath)

def get_uploaded_songs(show_unshared=False):
    songs = []
    if not os.path.exists(songs_dir): return songs
    shared_links = load_shared_links()
    for f in os.listdir(songs_dir):
        if f.endswith("_original.mp3"):
            song_name = f.replace("_original.mp3", "")
            if show_unshared or song_name in shared_links:
                songs.append(song_name)
    return sorted(songs)

# --- SESSION STATE ---
if "user" not in st.session_state: st.session_state.user = None
if "role" not in st.session_state: st.session_state.role = None
if "page" not in st.session_state: st.session_state.page = "Login"

metadata = load_metadata()
default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
logo_b64 = file_to_base64(default_logo_path)

# =============== LOGIN PAGE ===============
if st.session_state.page == "Login":
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    .stApp { background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%); }
    .login-box {
        background: rgba(15, 23, 42, 0.8);
        padding: 40px;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.1);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        if logo_b64:
            st.image(f"data:image/png;base64,{logo_b64}", width=80)
        st.title("𝄞 Karaoke Reels")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login", use_container_width=True):
            h = hash_password(password)
            if username == "admin" and h == ADMIN_HASH:
                st.session_state.user, st.session_state.role, st.session_state.page = "admin", "admin", "Admin Dashboard"
                st.rerun()
            elif (username == "user1" and h == USER1_HASH) or (username == "user2" and h == USER2_HASH):
                st.session_state.user, st.session_state.role, st.session_state.page = username, "user", "User Dashboard"
                st.rerun()
            else:
                st.error("Invalid Credentials")
        st.markdown('</div>', unsafe_allow_html=True)

# =============== ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    st.title(f"👑 Admin: {st.session_state.user}")
    menu = st.sidebar.radio("Navigate", ["Upload", "Songs", "Logout"])

    if menu == "Upload":
        with st.form("upload_form"):
            u_orig = st.file_uploader("Original MP3", type=["mp3"])
            u_acc = st.file_uploader("Accompaniment MP3", type=["mp3"])
            u_img = st.file_uploader("Lyrics Image", type=["jpg","png","jpeg"])
            if st.form_submit_button("Save Song"):
                if u_orig and u_acc and u_img:
                    name = u_orig.name.replace("_original.mp3", "").strip()
                    with open(os.path.join(songs_dir, f"{name}_original.mp3"), "wb") as f: f.write(u_orig.getbuffer())
                    with open(os.path.join(songs_dir, f"{name}_accompaniment.mp3"), "wb") as f: f.write(u_acc.getbuffer())
                    ext = os.path.splitext(u_img.name)[1]
                    with open(os.path.join(lyrics_dir, f"{name}_lyrics_bg{ext}"), "wb") as f: f.write(u_img.getbuffer())
                    metadata[name] = {"uploaded_by": "admin"}
                    save_metadata(metadata)
                    st.success("Uploaded!")

    elif menu == "Songs":
        songs = get_uploaded_songs(True)
        links = load_shared_links()
        for s in songs:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"🎵 {s}")
            if c2.button("▶ Play", key=f"p_{s}"):
                st.session_state.selected_song = s
                st.session_state.page = "Song Player"
                st.rerun()
            state = "Unshare" if s in links else "Share"
            if c3.button(state, key=f"s_{s}"):
                if s in links: delete_shared_link(s)
                else: save_shared_link(s, {"active":True})
                st.rerun()
    
    if menu == "Logout":
        st.session_state.clear()
        st.rerun()

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard":
    st.title(f"🎤 Welcome {st.session_state.user}")
    songs = get_uploaded_songs(False)
    for s in songs:
        c1, c2 = st.columns([4, 1])
        c1.write(f"🌟 {s}")
        if c2.button("Play", key=f"up_{s}"):
            st.session_state.selected_song = s
            st.session_state.page = "Song Player"
            st.rerun()
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

# =============== SONG PLAYER (UPDATED JS) ===============
elif st.session_state.page == "Song Player":
    song = st.session_state.selected_song
    
    # Header area to go back
    if st.button("⬅ Back to Dashboard"):
        st.session_state.page = "Admin Dashboard" if st.session_state.role == "admin" else "User Dashboard"
        st.rerun()

    orig_b64 = file_to_base64(os.path.join(songs_dir, f"{song}_original.mp3"))
    acc_b64 = file_to_base64(os.path.join(songs_dir, f"{song}_accompaniment.mp3"))
    
    lyr_path = ""
    for e in [".jpg",".png",".jpeg"]:
        if os.path.exists(os.path.join(lyrics_dir, f"{song}_lyrics_bg{e}")):
            lyr_path = os.path.join(lyrics_dir, f"{song}_lyrics_bg{e}")
            break
    lyr_b64 = file_to_base64(lyr_path)

    karaoke_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ background: #000; color: white; font-family: sans-serif; text-align: center; margin: 0; overflow: hidden; }}
            .container {{ position: relative; width: 100vw; height: 100vh; }}
            #mainBg {{ width: 100%; height: 80vh; object-fit: contain; }}
            .controls {{ padding: 20px; background: #111; height: 20vh; }}
            button {{ padding: 12px 25px; margin: 5px; border-radius: 30px; border: none; cursor: pointer; font-weight: bold; }}
            .btn-play {{ background: #22c55e; color: white; }}
            .btn-rec {{ background: #ef4444; color: white; }}
            .btn-stop {{ background: #6b7280; color: white; display: none; }}
            #status {{ color: #fbbf24; margin-bottom: 10px; }}
            canvas {{ display: none; }}
            .overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); display: none; flex-direction: column; justify-content: center; align-items: center; z-index: 100; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div id="status">Ready to Sing 🎤</div>
            <img id="mainBg" src="data:image/jpeg;base64,{lyr_b64}">
            <div class="controls">
                <button class="btn-play" id="playBtn">▶ Preview Song</button>
                <button class="btn-rec" id="recordBtn">🎙 Start Recording</button>
                <button class="btn-stop" id="stopBtn">⏹ Stop</button>
            </div>
        </div>

        <div class="overlay" id="finishLayer">
            <h2>Recording Finished!</h2>
            <button class="btn-play" id="playBack">▶ Play Recording</button>
            <a id="dlLink"><button class="btn-play">⬇ Download Video</button></a>
            <button onclick="location.reload()">🔄 New Record</button>
        </div>

        <audio id="audioOrig" src="data:audio/mp3;base64,{orig_b64}"></audio>
        <audio id="audioAcc" src="data:audio/mp3;base64,{acc_b64}"></audio>
        <canvas id="recCanvas" width="1280" height="720"></canvas>

        <script>
            let audioCtx, recorder, chunks = [], stream, animationId;
            const btnPlay = document.getElementById('playBtn');
            const btnRec = document.getElementById('recordBtn');
            const btnStop = document.getElementById('stopBtn');
            const audioOrig = document.getElementById('audioOrig');
            const audioAcc = document.getElementById('audioAcc');
            const status = document.getElementById('status');
            const canvas = document.getElementById('recCanvas');
            const ctx = canvas.getContext('2d');
            const img = document.getElementById('mainBg');

            async function initAudio() {{
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                if (audioCtx.state === 'suspended') await audioCtx.resume();
            }}

            btnPlay.onclick = async () => {{
                await initAudio();
                if (audioOrig.paused) {{ audioOrig.play(); btnPlay.innerText = "⏸ Pause"; }}
                else {{ audioOrig.pause(); btnPlay.innerText = "▶ Preview Song"; }}
            }};

            function draw() {{
                ctx.fillStyle = "black";
                ctx.fillRect(0,0,canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                animationId = requestAnimationFrame(draw);
            }}

            btnRec.onclick = async () => {{
                await initAudio();
                status.innerText = "🎙 Recording...";
                btnRec.style.display = "none";
                btnStop.style.display = "inline-block";
                
                const micStream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                const micSource = audioCtx.createMediaStreamSource(micStream);
                const dest = audioCtx.createMediaStreamDestination();
                
                // Mix mic + accompaniment
                micSource.connect(dest);
                const accSource = audioCtx.createMediaElementSource(audioAcc);
                accSource.connect(dest);
                accSource.connect(audioCtx.destination);

                draw();
                const videoStream = canvas.captureStream(30);
                const combinedStream = new MediaStream([...videoStream.getTracks(), ...dest.stream.getTracks()]);
                
                recorder = new MediaRecorder(combinedStream, {{ mimeType: 'video/webm' }});
                recorder.ondataavailable = e => chunks.push(e.data);
                recorder.onstop = () => {{
                    cancelAnimationFrame(animationId);
                    const blob = new Blob(chunks, {{ type: 'video/webm' }});
                    const url = URL.createObjectURL(blob);
                    document.getElementById('finishLayer').style.display = "flex";
                    document.getElementById('dlLink').href = url;
                    document.getElementById('dlLink').download = `karaoke_${{Date.now()}}.webm`;
                    document.getElementById('playBack').onclick = () => {{
                        let a = new Audio(url); a.play();
                    }};
                }};

                recorder.start();
                audioAcc.play();
                audioOrig.play();
                audioOrig.muted = true; // Use orig for timing, acc for audio
            }};

            btnStop.onclick = () => {{
                recorder.stop();
                audioAcc.pause();
                audioOrig.pause();
                status.innerText = "Done!";
            }};
        </script>
    </body>
    </html>
    """
    html(karaoke_html, height=800)

else:
    st.session_state.page = "Login"
    st.rerun()
