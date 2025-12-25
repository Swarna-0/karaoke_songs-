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
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="𝄞 sing-along", layout="wide", initial_sidebar_state="collapsed")

# --------- CONFIG: set your deployed app URL here ----------
APP_URL = "https://karaoke-project-production.up.railway.app/"

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
session_db_path = os.path.join(base_dir, "session_data.db")

# Create directories
os.makedirs(songs_dir, exist_ok=True)
os.makedirs(lyrics_dir, exist_ok=True)
os.makedirs(logo_dir, exist_ok=True)
os.makedirs(shared_links_dir, exist_ok=True)

# =============== CACHE CONFIGURATION ===============
@st.cache_data(ttl=300, show_spinner=False)
def load_metadata_cached():
    """Cache metadata loading"""
    return load_metadata()

@st.cache_data(ttl=300, show_spinner=False)
def load_shared_links_cached():
    """Cache shared links loading"""
    return load_shared_links()

@st.cache_data(ttl=60, show_spinner=False)
def get_songs_list_cached(show_unshared=False):
    """Cache songs list"""
    return get_uploaded_songs(show_unshared)

@st.cache_resource
def get_db_connection():
    """Get cached database connection"""
    return sqlite3.connect(session_db_path, check_same_thread=False)

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
        logger.error(f"Error initializing database: {e}")

def save_session_to_db():
    """Save current session to database"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        session_id = st.session_state.get('session_id', 'default')
        
        c.execute('''INSERT OR REPLACE INTO sessions 
                     (session_id, user, role, page, selected_song, last_active)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (session_id,
                   st.session_state.get('user', ''),
                   st.session_state.get('role', ''),
                   st.session_state.get('page', ''),
                   st.session_state.get('selected_song', ''),
                   datetime.now()))
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving session: {e}")

def load_session_from_db():
    """Load session from database"""
    try:
        session_id = st.session_state.get('session_id', 'default')
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT user, role, page, selected_song FROM sessions WHERE session_id = ?', 
                  (session_id,))
        result = c.fetchone()
        
        if result:
            user, role, page, selected_song = result
            if user and user != 'None' and user != '':
                st.session_state.user = user
            if role and role != 'None' and role != '':
                st.session_state.role = role
            if page and page != 'None' and page != '':
                st.session_state.page = page
            if selected_song and selected_song != 'None' and selected_song != '':
                st.session_state.selected_song = selected_song
    except Exception as e:
        logger.error(f"Error loading session: {e}")

def save_shared_link_to_db(song_name, shared_by):
    """Save shared link to database"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO shared_links 
                     (song_name, shared_by, active, created_at)
                     VALUES (?, ?, ?, ?)''',
                  (song_name, shared_by, True, datetime.now()))
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving shared link: {e}")

def delete_shared_link_from_db(song_name):
    """Delete shared link from database"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM shared_links WHERE song_name = ?', (song_name,))
        conn.commit()
    except Exception as e:
        logger.error(f"Error deleting shared link: {e}")

def load_shared_links_from_db():
    """Load shared links from database"""
    links = {}
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT song_name, shared_by FROM shared_links WHERE active = 1')
        results = c.fetchall()
        
        for song_name, shared_by in results:
            links[song_name] = {"shared_by": shared_by, "active": True}
    except Exception as e:
        logger.error(f"Error loading shared links: {e}")
    return links

def save_metadata_to_db(song_name, uploaded_by):
    """Save metadata to database"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO metadata 
                     (song_name, uploaded_by, timestamp)
                     VALUES (?, ?, ?)''',
                  (song_name, uploaded_by, time.time()))
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving metadata: {e}")

def load_metadata_from_db():
    """Load metadata from database"""
    metadata = {}
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT song_name, uploaded_by FROM metadata')
        results = c.fetchall()
        
        for song_name, uploaded_by in results:
            metadata[song_name] = {"uploaded_by": uploaded_by, "timestamp": str(time.time())}
    except Exception as e:
        logger.error(f"Error loading metadata: {e}")
    return metadata

# Initialize database
init_session_db()

# =============== HELPER FUNCTIONS ===============
def file_to_base64(path):
    """Convert file to base64 with error handling"""
    try:
        if os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    except Exception as e:
        logger.error(f"Error converting file to base64: {e}")
    return ""

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_metadata():
    """Load metadata from both file and database"""
    file_metadata = {}
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                file_metadata = json.load(f)
        except Exception as e:
            logger.error(f"Error loading metadata file: {e}")
            file_metadata = {}
    
    # Merge with database metadata
    db_metadata = load_metadata_from_db()
    file_metadata.update(db_metadata)
    return file_metadata

def save_metadata(data):
    """Save metadata to both file and database"""
    # Save to file
    try:
        with open(metadata_path, "w") as f:
            json.dump(data, f, indent=2)
        
        # Save to database
        for song_name, info in data.items():
            uploaded_by = info.get("uploaded_by", "unknown")
            save_metadata_to_db(song_name, uploaded_by)
    except Exception as e:
        logger.error(f"Error saving metadata: {e}")

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
                except Exception as e:
                    logger.error(f"Error loading shared link file {filename}: {e}")
    
    # Merge with database links
    db_links = load_shared_links_from_db()
    file_links.update(db_links)
    return file_links

def save_shared_link(song_name, link_data):
    """Save shared link to both file and database"""
    try:
        # Save to file
        filepath = os.path.join(shared_links_dir, f"{song_name}.json")
        with open(filepath, 'w') as f:
            json.dump(link_data, f)
        
        # Save to database
        shared_by = link_data.get("shared_by", "unknown")
        save_shared_link_to_db(song_name, shared_by)
    except Exception as e:
        logger.error(f"Error saving shared link: {e}")

def delete_shared_link(song_name):
    """Delete shared link from both file and database"""
    try:
        # Delete from file
        filepath = os.path.join(shared_links_dir, f"{song_name}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Delete from database
        delete_shared_link_from_db(song_name)
    except Exception as e:
        logger.error(f"Error deleting shared link: {e}")

def get_uploaded_songs(show_unshared=False):
    """Get list of uploaded songs"""
    songs = []
    try:
        if not os.path.exists(songs_dir):
            return songs
        
        shared_links = load_shared_links_cached()
        
        for f in os.listdir(songs_dir):
            if f.endswith("_original.mp3"):
                song_name = f.replace("_original.mp3", "")
                if show_unshared or song_name in shared_links:
                    songs.append(song_name)
        return sorted(songs)
    except Exception as e:
        logger.error(f"Error getting uploaded songs: {e}")
        return []

def check_and_create_session_id():
    """Create unique session ID if not exists"""
    if 'session_id' not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())

def get_audio_file_paths(song_name):
    """Get all audio file paths for a song"""
    original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
    accompaniment_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
    return original_path, accompaniment_path

def get_lyrics_image_path(song_name):
    """Get lyrics image path for a song"""
    for ext in [".jpg", ".jpeg", ".png"]:
        path = os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{ext}")
        if os.path.exists(path):
            return path
    return ""

# =============== INITIALIZE SESSION ===============
check_and_create_session_id()

# Initialize session state with default values
default_values = {
    "user": None,
    "role": None,
    "page": "Login",
    "selected_song": None,
    "initialized": False
}

for key, default_value in default_values.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

# Load persistent session data
if not st.session_state.get("initialized", False):
    load_session_from_db()
    st.session_state.initialized = True

metadata = load_metadata_cached()

# Logo handling
default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
logo_b64 = file_to_base64(default_logo_path) if os.path.exists(default_logo_path) else ""

# =============== CHECK FOR DIRECT SONG LINK ===============
@st.cache_data(ttl=5, show_spinner=False)
def check_direct_song_link(query_params):
    """Check if there's a direct song link in query params"""
    if "song" in query_params:
        song_from_url = unquote(query_params["song"])
        shared_links = load_shared_links_cached()
        if song_from_url in shared_links:
            return song_from_url
    return None

# Check direct song link
direct_song = check_direct_song_link(st.query_params)
if direct_song and st.session_state.page == "Login":
    st.session_state.selected_song = direct_song
    st.session_state.page = "Song Player"
    st.session_state.user = "guest"
    st.session_state.role = "guest"
    save_session_to_db()
    st.rerun()

# =============== RESPONSIVE LOGIN PAGE ===============
if st.session_state.page == "Login":
    # Save session state
    save_session_to_db()
    
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    header {visibility:hidden;}
    footer {visibility:hidden;}

    body {
        background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%);
    }

    .login-content {
        padding: 1.8rem 2.2rem 2.2rem 2.2rem;
    }

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
    }

    .login-sub {
        font-size: 0.9rem;
        color: #c3cfdd;
        margin-bottom: 0.5rem;
        width: 100%;
    }

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
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
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

        # Header with better spacing
        st.markdown(f"""
        <div class="login-header">
            <img src="data:image/png;base64,{logo_b64}">
            <div class="login-title">𝄞 Karaoke Reels</div>
            <div class="login-sub">Login to continue</div>
        </div>
        """, unsafe_allow_html=True)

        username = st.text_input("Email / Username", placeholder="admin / user1 / user2", value="", key="login_username")
        password = st.text_input("Password", type="password", placeholder="Enter password", value="", key="login_password")

        if st.button("Login", key="login_button", type="primary"):
            if not username or not password:
                st.error("❌ Enter both username and password")
            else:
                hashed_pass = hash_password(password)
                if username == "admin" and ADMIN_HASH and hashed_pass == ADMIN_HASH:
                    st.session_state.user = username
                    st.session_state.role = "admin"
                    st.session_state.page = "Admin Dashboard"
                    save_session_to_db()
                    st.rerun()
                elif username == "user1" and USER1_HASH and hashed_pass == USER1_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    save_session_to_db()
                    st.rerun()
                elif username == "user2" and USER2_HASH and hashed_pass == USER2_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    save_session_to_db()
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
    # Auto-save session
    save_session_to_db()
    
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

            # Show progress
            with st.spinner(f"Uploading {song_name}..."):
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
            time.sleep(1)
            st.rerun()

    elif page_sidebar == "Songs List":
        st.subheader("🎵 All Songs List (Admin View)")
        uploaded_songs = get_songs_list_cached(show_unshared=True)
        if not uploaded_songs:
            st.warning("❌ No songs uploaded yet.")
        else:
            for idx, s in enumerate(uploaded_songs):
                col1, col2, col3 = st.columns([3, 1, 2])
                safe_s = quote(s)

                with col1:
                    st.write(f"**{s}** - by {metadata.get(s, {}).get('uploaded_by', 'Unknown')}")
                with col2:
                    if st.button("▶ Play", key=f"play_{s}_{idx}", help="Play this song"):
                        st.session_state.selected_song = s
                        st.session_state.page = "Song Player"
                        save_session_to_db()
                        st.rerun()
                with col3:
                    share_url = f"{APP_URL}?song={safe_s}"
                    st.markdown(f"[🔗 Share Link]({share_url})")

    elif page_sidebar == "Share Links":
        st.header("🔗 Manage Shared Links")
        all_songs = get_songs_list_cached(show_unshared=True)
        shared_links_data = load_shared_links_cached()

        for song in all_songs:
            col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1.5])
            safe_song = quote(song)
            is_shared = song in shared_links_data

            with col1:
                status = "✅ SHARED" if is_shared else "❌ **NOT SHARED"
                st.write(f"{song} - {status}")

            with col2:
                if st.button("🔄 Toggle", key=f"toggle_share_{song}", help="Toggle sharing status"):
                    if is_shared:
                        delete_shared_link(song)
                        st.success(f"✅ {song} unshared! Users can no longer see this song.")
                    else:
                        save_shared_link(song, {"shared_by": st.session_state.user, "active": True})
                        share_url = f"{APP_URL}?song={safe_song}"
                        st.success(f"✅ {song} shared! Link: {share_url}")
                    time.sleep(0.5)
                    st.rerun()

            with col3:
                if is_shared:
                    if st.button("🚫 Remove", key=f"unshare_{song}", help="Remove sharing"):
                        delete_shared_link(song)
                        st.success(f"✅ {song} unshared! Users cannot see this song anymore.")
                        time.sleep(0.5)
                        st.rerun()

            with col4:
                if is_shared:
                    share_url = f"{APP_URL}?song={safe_song}"
                    st.markdown(f"[📱 Open]({share_url})")

    if st.sidebar.button("🚪 Logout", key="admin_logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "Login"
        save_session_to_db()
        st.rerun()

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    # Auto-save session
    save_session_to_db()
    
    st.title(f"👤 User Dashboard - {st.session_state.user}")

    st.subheader("🎵 Available Songs (Only Shared Songs)")
    uploaded_songs = get_songs_list_cached(show_unshared=False)

    if not uploaded_songs:
        st.warning("❌ No shared songs available. Contact admin to share songs.")
        st.info("👑 Only admin-shared songs appear here for users.")
    else:
        for idx, song in enumerate(uploaded_songs):
            col1, col2 = st.columns([3,1])
            with col1:
                st.write(f"✅ {song} (Shared)")
            with col2:
                if st.button("▶ Play", key=f"user_play_{song}_{idx}"):
                    st.session_state.selected_song = song
                    st.session_state.page = "Song Player"
                    save_session_to_db()
                    st.rerun()

    if st.button("🚪 Logout", key="user_logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "Login"
        save_session_to_db()
        st.rerun()

# =============== SONG PLAYER ===============
elif st.session_state.page == "Song Player" and st.session_state.get("selected_song"):
    # Auto-save session
    save_session_to_db()
    
    selected_song = st.session_state.get("selected_song", None)
    
    # Double-check access permission
    shared_links = load_shared_links_cached()
    is_shared = selected_song in shared_links
    is_admin = st.session_state.role == "admin"
    is_guest = st.session_state.role == "guest"

    if not (is_shared or is_admin or is_guest):
        st.error("❌ Access denied! This song is not shared with users.")
        if st.button("Go Back"):
            if st.session_state.role == "user":
                st.session_state.page = "User Dashboard"
            else:
                st.session_state.page = "Admin Dashboard"
            save_session_to_db()
            st.rerun()
        st.stop()

    # Get file paths
    original_path, accompaniment_path = get_audio_file_paths(selected_song)
    lyrics_path = get_lyrics_image_path(selected_song)

    # Check if files exist
    if not os.path.exists(original_path) or not os.path.exists(accompaniment_path):
        st.error(f"❌ Audio files not found for {selected_song}")
        if st.button("Go Back"):
            if st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            elif st.session_state.role == "user":
                st.session_state.page = "User Dashboard"
            else:
                st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
        st.stop()

    # Load files with caching
    @st.cache_data(ttl=3600, show_spinner=False)
    def load_audio_files(song_name):
        original_b64 = file_to_base64(original_path)
        accompaniment_b64 = file_to_base64(accompaniment_path)
        lyrics_b64 = file_to_base64(lyrics_path) if lyrics_path else ""
        return original_b64, accompaniment_b64, lyrics_b64

    original_b64, accompaniment_b64, lyrics_b64 = load_audio_files(selected_song)

    # Simple back button at top
    if st.button("← Back to Dashboard", key="back_player_top"):
        if st.session_state.role == "admin":
            st.session_state.page = "Admin Dashboard"
        elif st.session_state.role == "user":
            st.session_state.page = "User Dashboard"
        else:
            st.session_state.page = "Login"
        save_session_to_db()
        st.rerun()

    # Create optimized player HTML
    karaoke_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>🎤 {selected_song} - Karaoke Reels</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: #000;
            font-family: Arial, sans-serif;
            overflow: hidden;
        }}
        #playerContainer {{
            width: 100vw;
            height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: #111;
        }}
        #lyricsImage {{
            max-width: 90%;
            max-height: 70vh;
            object-fit: contain;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        .controls {{
            margin-top: 20px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            justify-content: center;
        }}
        button {{
            background: linear-gradient(135deg, #ff0066, #ff66cc);
            border: none;
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 5px 15px rgba(255,0,128,0.4);
        }}
        button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(255,0,128,0.6);
        }}
        button:active {{
            transform: translateY(0);
        }}
        #status {{
            color: white;
            margin: 15px 0;
            font-size: 18px;
            text-align: center;
            min-height: 30px;
        }}
        .hidden {{
            display: none;
        }}
        #logo {{
            position: absolute;
            top: 20px;
            left: 20px;
            width: 50px;
            opacity: 0.7;
        }}
    </style>
</head>
<body>
    <img id="logo" src="data:image/png;base64,{logo_b64}">
    <div id="playerContainer">
        <img id="lyricsImage" src="data:image/jpeg;base64,{lyrics_b64}">
        <div id="status">Ready to play 🎤</div>
        <div class="controls">
            <button onclick="playOriginal()">▶ Play Original</button>
            <button onclick="startRecording()">🎤 Start Recording</button>
            <button onclick="stopRecording()" class="hidden" id="stopBtn">⏹ Stop</button>
            <button onclick="playRecording()" class="hidden" id="playRecBtn">▶ Play Recording</button>
        </div>
        
        <audio id="originalAudio" preload="auto">
            <source src="data:audio/mp3;base64,{original_b64}" type="audio/mp3">
        </audio>
        
        <audio id="accompanimentAudio" preload="auto">
            <source src="data:audio/mp3;base64,{accompaniment_b64}" type="audio/mp3">
        </audio>
    </div>

    <script>
        let originalAudio = document.getElementById('originalAudio');
        let accompanimentAudio = document.getElementById('accompanimentAudio');
        let mediaRecorder;
        let recordedChunks = [];
        let recordingUrl = null;
        let isRecording = false;
        
        function updateStatus(text) {{
            document.getElementById('status').textContent = text;
        }}
        
        function playOriginal() {{
            try {{
                if (originalAudio.paused) {{
                    originalAudio.currentTime = 0;
                    originalAudio.play();
                    updateStatus('🎵 Playing original...');
                }} else {{
                    originalAudio.pause();
                    updateStatus('⏸ Paused');
                }}
            }} catch (error) {{
                updateStatus('❌ Playback error: ' + error.message);
            }}
        }}
        
        async function startRecording() {{
            if (isRecording) return;
            
            try {{
                updateStatus('🎤 Starting recording...');
                
                // Start both audios
                originalAudio.currentTime = 0;
                accompanimentAudio.currentTime = 0;
                
                await Promise.all([
                    originalAudio.play(),
                    accompanimentAudio.play()
                ]);
                
                // Start recording mic and audio
                const stream = await navigator.mediaDevices.getUserMedia({{
                    audio: {{
                        echoCancellation: true,
                        noiseSuppression: true,
                        sampleRate: 44100
                    }}
                }});
                
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const micSource = audioContext.createMediaStreamSource(stream);
                
                // Create destination for mixed audio
                const destination = audioContext.createMediaStreamDestination();
                micSource.connect(destination);
                
                // Start recording
                mediaRecorder = new MediaRecorder(destination.stream);
                recordedChunks = [];
                
                mediaRecorder.ondataavailable = (event) => {{
                    if (event.data.size > 0) {{
                        recordedChunks.push(event.data);
                    }}
                }};
                
                mediaRecorder.onstop = () => {{
                    const blob = new Blob(recordedChunks, {{ type: 'audio/webm' }});
                    if (recordingUrl) URL.revokeObjectURL(recordingUrl);
                    recordingUrl = URL.createObjectURL(blob);
                    
                    document.getElementById('playRecBtn').classList.remove('hidden');
                    updateStatus('✅ Recording complete!');
                    
                    // Stop audios
                    originalAudio.pause();
                    accompanimentAudio.pause();
                }};
                
                mediaRecorder.start();
                isRecording = true;
                
                document.getElementById('stopBtn').classList.remove('hidden');
                updateStatus('🔴 Recording in progress...');
                
            }} catch (error) {{
                updateStatus('❌ Recording error: ' + error.message);
            }}
        }}
        
        function stopRecording() {{
            if (!isRecording) return;
            
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {{
                mediaRecorder.stop();
            }}
            
            isRecording = false;
            document.getElementById('stopBtn').classList.add('hidden');
            updateStatus('⏹ Processing recording...');
        }}
        
        function playRecording() {{
            if (!recordingUrl) return;
            
            const audio = new Audio(recordingUrl);
            audio.play();
            updateStatus('▶ Playing your recording...');
            
            audio.onended = () => {{
                updateStatus('✅ Recording playback complete!');
            }};
        }}
        
        // Handle page visibility change
        document.addEventListener('visibilitychange', () => {{
            if (document.hidden && isRecording) {{
                stopRecording();
            }}
        }});
        
        // Preload audios for faster playback
        window.addEventListener('load', () => {{
            originalAudio.load();
            accompanimentAudio.load();
        }});
    </script>
</body>
</html>
"""

    # Display the player
    html(karaoke_html, height=800, scrolling=False)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    save_session_to_db()
    st.rerun()

# =============== DEBUG INFO (Hidden by default) ===============
if st.session_state.get("role") == "admin" and st.sidebar.checkbox("Show Debug Info", key="debug_toggle"):
    st.sidebar.write("### Debug Info")
    st.sidebar.write(f"Page: {st.session_state.get('page')}")
    st.sidebar.write(f"User: {st.session_state.get('user')}")
    st.sidebar.write(f"Role: {st.session_state.get('role')}")
    st.sidebar.write(f"Selected Song: {st.session_state.get('selected_song')}")
    st.sidebar.write(f"Session ID: {st.session_state.get('session_id')}")
    
    if st.sidebar.button("Force Reset", key="debug_reset"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "Login"
        save_session_to_db()
        st.rerun()
