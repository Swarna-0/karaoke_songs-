import streamlit as st
import os
import base64
import json
from streamlit.components.v1 import html
import hashlib
from urllib.parse import unquote, quote

st.set_page_config(page_title="𝄞 sing-along", layout="wide")

APP_URL = "https://karaoke-song.onrender.com/"

# 🔒 SECURITY: Environment Variables for Password Hashes
ADMIN_HASH = os.getenv("ADMIN_HASH", "")
USER1_HASH = os.getenv("USER1_HASH", "")
USER2_HASH = os.getenv("USER2_HASH", "")

# Base directories
BASE_STORAGE = "/data" if os.path.exists("/data") else os.getcwd()
media_dir = os.path.join(BASE_STORAGE, "media")
songs_dir = os.path.join(media_dir, "songs")
lyrics_dir = os.path.join(media_dir, "lyrics_images")
logo_dir = os.path.join(media_dir, "logo")
shared_links_dir = os.path.join(media_dir, "shared_links")
metadata_path = os.path.join(media_dir, "song_metadata.json")

os.makedirs(songs_dir, exist_ok=True)
os.makedirs(lyrics_dir, exist_ok=True)
os.makedirs(logo_dir, exist_ok=True)
os.makedirs(shared_links_dir, exist_ok=True)

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

# Check for song parameter in URL
query_params = st.query_params
url_song = query_params.get("song", None)

if url_song:
    song_name = unquote(url_song)
    original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
    song_exists = os.path.exists(original_path)
    
    if song_exists:
        shared_links = load_shared_links()
        is_shared = song_name in shared_links
        
        if is_shared:
            st.session_state.selected_song = song_name
            st.session_state.page = "Song Player"
            if "user" not in st.session_state:
                st.session_state.user = "guest"
                st.session_state.role = "guest"
        else:
            st.session_state.page = "Login"
    else:
        st.session_state.page = "Login"

# Logo
default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
if not os.path.exists(default_logo_path):
    logo_upload = st.file_uploader("Upload Logo (PNG) (optional)", type=["png"], key="logo_upload")
    if logo_upload:
        with open(default_logo_path, "wb") as f:
            f.write(logo_upload.getbuffer())
        st.rerun()
logo_b64 = file_to_base64(default_logo_path)

# =============== LOGIN PAGE ===============
if st.session_state.page == "Login":
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    header {visibility:hidden;}
    body {background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%);}
    .login-content {padding: 2rem;}
    </style>
    """, unsafe_allow_html=True)
    
    left, center, right = st.columns([1, 1.5, 1])
    with center:
        st.markdown(f"""
        <div style='text-align:center;margin-bottom:2rem;'>
            <img src='data:image/png;base64,{logo_b64}' style='width:60px;height:60px;border-radius:50%;border:2px solid rgba(255,255,255,0.4);'>
            <h2>𝄞 Karaoke Reels</h2>
            <p>Login to continue</p>
        </div>
        """, unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="admin / user1 / user2")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        
        if st.button("Login"):
            if username and password:
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
            else:
                st.error("❌ Enter both username and password")

# =============== ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    st.title(f"👑 Admin Dashboard - {st.session_state.user}")
    page_sidebar = st.sidebar.radio("Navigate", ["Upload Songs", "Songs List", "Share Links"])
    
    if page_sidebar == "Upload Songs":
        st.subheader("📤 Upload New Song")
        col1, col2, col3 = st.columns(3)
        with col1:
            uploaded_original = st.file_uploader("Original Song (_original.mp3)", type=["mp3"])
        with col2:
            uploaded_accompaniment = st.file_uploader("Accompaniment (_accompaniment.mp3)", type=["mp3"])
        with col3:
            uploaded_lyrics_image = st.file_uploader("Lyrics Image (_lyrics_bg.jpg/png)", type=["jpg", "jpeg", "png"])
        
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
            
            metadata[song_name] = {"uploaded_by": st.session_state.user}
            save_metadata(metadata)
            st.success(f"✅ Uploaded: {song_name}")
            st.rerun()
    
    elif page_sidebar == "Songs List":
        st.subheader("🎵 All Songs List")
        uploaded_songs = get_uploaded_songs(show_unshared=True)
        if not uploaded_songs:
            st.warning("❌ No songs uploaded yet.")
        else:
            for s in uploaded_songs:
                col1, col2, col3 = st.columns([3, 1, 2])
                with col1:
                    st.write(f"**{s}** - by {metadata.get(s, {}).get('uploaded_by', 'Unknown')}")
                with col2:
                    if st.button("▶ Play", key=f"play_{s}"):
                        st.session_state.selected_song = s
                        st.session_state.page = "Song Player"
                        st.rerun()
                with col3:
                    share_url = f"{APP_URL}?song={quote(s)}"
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
                status = "✅ SHARED" if is_shared else "❌ NOT SHARED"
                st.write(f"{song} - {status}")
            
            with col2:
                if st.button("🔄 Toggle", key=f"toggle_{song}"):
                    if is_shared:
                        delete_shared_link(song)
                    else:
                        save_shared_link(song, {"shared_by": st.session_state.user, "active": True})
                    st.rerun()
            
            with col3:
                if is_shared and st.button("🚫 Unshare", key=f"unshare_{song}"):
                    delete_shared_link(song)
                    st.rerun()
            
            with col4:
                if is_shared:
                    share_url = f"{APP_URL}?song={safe_song}"
                    st.markdown(f"[📱 Open]({share_url})")
    
    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    st.title(f"👤 User Dashboard - {st.session_state.user}")
    st.subheader("🎵 Available Songs")
    uploaded_songs = get_uploaded_songs(show_unshared=False)
    
    if not uploaded_songs:
        st.warning("❌ No shared songs available.")
    else:
        for song in uploaded_songs:
            col1, col2 = st.columns([3,1])
            with col1:
                st.write(f"✅ {song} (Shared)")
            with col2:
                if st.button("▶ Play", key=f"user_play_{song}"):
                    st.session_state.selected_song = song
                    st.session_state.page = "Song Player"
                    st.rerun()
    
    if st.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# =============== SONG PLAYER ===============
elif st.session_state.page == "Song Player" and st.session_state.get("selected_song"):
    selected_song = st.session_state.get("selected_song")
    
    # Check access
    shared_links = load_shared_links()
    is_shared = selected_song in shared_links
    is_admin = st.session_state.role == "admin"
    is_guest = st.session_state.role == "guest"
    
    if not (is_shared or is_admin or is_guest):
        st.error("❌ Access denied!")
        st.session_state.page = "User Dashboard" if st.session_state.role == "user" else "Admin Dashboard"
        st.rerun()
    
    # Get file paths
    original_path = os.path.join(songs_dir, f"{selected_song}_original.mp3")
    accompaniment_path = os.path.join(songs_dir, f"{selected_song}_accompaniment.mp3")
    
    # Get lyrics image
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
    
    # Simple back button
    if st.button("← Back"):
        if st.session_state.role == "guest":
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        else:
            st.session_state.page = "User Dashboard" if st.session_state.role == "user" else "Admin Dashboard"
            st.rerun()
    
    # SIMPLIFIED KARAOKE PLAYER - FIXED VERSION
    karaoke_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Karaoke Player</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: #000;
            font-family: Arial, sans-serif;
        }}
        .container {{
            position: relative;
            width: 100vw;
            height: 100vh;
            overflow: hidden;
        }}
        .bg-image {{
            width: 100%;
            height: 100%;
            object-fit: contain;
        }}
        .logo {{
            position: absolute;
            top: 20px;
            left: 20px;
            width: 60px;
            height: 60px;
            opacity: 0.7;
        }}
        .controls {{
            position: absolute;
            bottom: 50px;
            left: 0;
            right: 0;
            text-align: center;
            z-index: 100;
        }}
        button {{
            background: linear-gradient(45deg, #FF416C, #FF4B2B);
            color: white;
            border: none;
            padding: 15px 30px;
            margin: 10px;
            border-radius: 50px;
            font-size: 16px;
            cursor: pointer;
            min-width: 150px;
        }}
        button:hover {{
            opacity: 0.9;
        }}
        .status {{
            position: absolute;
            top: 20px;
            left: 0;
            right: 0;
            text-align: center;
            color: white;
            font-size: 18px;
            z-index: 100;
        }}
        audio {{ display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <img class="bg-image" src="data:image/jpeg;base64,{lyrics_b64}" alt="Lyrics">
        <img class="logo" src="data:image/png;base64,{logo_b64}" alt="Logo">
        <div class="status" id="status">Ready to play 🎤</div>
        
        <audio id="originalAudio" controls>
            <source src="data:audio/mp3;base64,{original_b64}" type="audio/mp3">
        </audio>
        
        <audio id="accompanimentAudio" controls>
            <source src="data:audio/mp3;base64,{accompaniment_b64}" type="audio/mp3">
        </audio>
        
        <div class="controls">
            <button onclick="playSong()" id="playBtn">▶ Play Song</button>
            <button onclick="stopSong()" id="stopBtn" style="display:none;">⏸ Pause</button>
            <button onclick="startRecording()" id="recordBtn">🎙 Start Recording</button>
        </div>
    </div>

    <script>
        const originalAudio = document.getElementById('originalAudio');
        const accompanimentAudio = document.getElementById('accompanimentAudio');
        const playBtn = document.getElementById('playBtn');
        const stopBtn = document.getElementById('stopBtn');
        const recordBtn = document.getElementById('recordBtn');
        const status = document.getElementById('status');
        
        let isPlaying = false;
        let isRecording = false;
        let mediaRecorder;
        let recordedChunks = [];
        
        // Preload audio
        originalAudio.load();
        accompanimentAudio.load();
        
        function playSong() {{
            if (!isPlaying) {{
                originalAudio.currentTime = 0;
                accompanimentAudio.currentTime = 0;
                
                // Play both tracks
                const playPromise1 = originalAudio.play();
                const playPromise2 = accompanimentAudio.play();
                
                Promise.all([playPromise1, playPromise2])
                    .then(() => {{
                        isPlaying = true;
                        playBtn.style.display = 'none';
                        stopBtn.style.display = 'inline-block';
                        status.textContent = '🎵 Playing...';
                    }})
                    .catch(error => {{
                        console.log('Play error:', error);
                        status.textContent = '⚠️ Error playing audio. Click play again.';
                    }});
            }}
        }}
        
        function stopSong() {{
            if (isPlaying) {{
                originalAudio.pause();
                accompanimentAudio.pause();
                isPlaying = false;
                playBtn.style.display = 'inline-block';
                stopBtn.style.display = 'none';
                status.textContent = '⏸ Paused';
            }}
        }}
        
        function startRecording() {{
            if (isRecording) return;
            
            if (!isPlaying) {{
                playSong();
            }}
            
            status.textContent = '🎙 Recording... Click pause to stop';
            isRecording = true;
            recordBtn.disabled = true;
            
            // Note: Full recording functionality would require more code
            // This is a simplified version
        }}
        
        // Handle audio ended
        originalAudio.onended = function() {{
            if (isPlaying) {{
                stopSong();
                status.textContent = '✅ Song finished';
            }}
        }};
        
        // Initial status
        setTimeout(() => {{
            status.textContent = '✅ Audio loaded. Click Play Song to start';
        }}, 1000);
    </script>
</body>
</html>
"""
    
    html(karaoke_html, height=800, width=1000)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    st.rerun()
