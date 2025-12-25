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

st.set_page_config(page_title="𝄞 sing-along", layout="wide")

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

# =============== OPTIMIZATION: CACHE ALL MEDIA FILES ===============
@st.cache_data(ttl=3600)
def get_cached_base64(path):
    """Cache base64 conversion for better performance"""
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# =============== PERSISTENT SESSION DATABASE ===============
def init_session_db():
    """Initialize SQLite database for persistent sessions"""
    try:
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
    except Exception as e:
        st.error(f"Database init error: {e}")

def save_session_to_db():
    """Save current session to database"""
    try:
        conn = sqlite3.connect(session_db_path, check_same_thread=False)
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
        conn.close()
    except Exception as e:
        pass

def load_session_from_db():
    """Load session from database"""
    try:
        session_id = st.session_state.get('session_id', 'default')
        conn = sqlite3.connect(session_db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user, role, page, selected_song FROM sessions WHERE session_id = ?', 
                  (session_id,))
        result = c.fetchone()
        conn.close()
        
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
    except Exception as e:
        pass

def save_shared_link_to_db(song_name, shared_by):
    """Save shared link to database"""
    try:
        conn = sqlite3.connect(session_db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO shared_links 
                     (song_name, shared_by, active, created_at)
                     VALUES (?, ?, ?, ?)''',
                  (song_name, shared_by, True, datetime.now()))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

def delete_shared_link_from_db(song_name):
    """Delete shared link from database"""
    try:
        conn = sqlite3.connect(session_db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('DELETE FROM shared_links WHERE song_name = ?', (song_name,))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

def load_shared_links_from_db():
    """Load shared links from database"""
    links = {}
    try:
        conn = sqlite3.connect(session_db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT song_name, shared_by FROM shared_links WHERE active = 1')
        results = c.fetchall()
        conn.close()
        
        for song_name, shared_by in results:
            links[song_name] = {"shared_by": shared_by, "active": True}
    except Exception as e:
        pass
    return links

def save_metadata_to_db(song_name, uploaded_by):
    """Save metadata to database"""
    try:
        conn = sqlite3.connect(session_db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO metadata 
                     (song_name, uploaded_by, timestamp)
                     VALUES (?, ?, ?)''',
                  (song_name, uploaded_by, time.time()))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

def load_metadata_from_db():
    """Load metadata from database"""
    metadata = {}
    try:
        conn = sqlite3.connect(session_db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT song_name, uploaded_by FROM metadata')
        results = c.fetchall()
        conn.close()
        
        for song_name, uploaded_by in results:
            metadata[song_name] = {"uploaded_by": uploaded_by, "timestamp": str(time.time())}
    except Exception as e:
        pass
    return metadata

# Initialize database
init_session_db()

# =============== OPTIMIZED HELPER FUNCTIONS ===============
def file_to_base64(path):
    """Optimized version using cache"""
    return get_cached_base64(path)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@st.cache_data(ttl=300)
def load_metadata_cached():
    """Load metadata with caching"""
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

def load_metadata():
    """Wrapper for backward compatibility"""
    return load_metadata_cached()

@st.cache_data(ttl=300)
def load_shared_links_cached():
    """Load shared links with caching"""
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

def load_shared_links():
    """Wrapper for backward compatibility"""
    return load_shared_links_cached()

def save_metadata(data):
    """Save metadata to both file and database"""
    # Save to file
    with open(metadata_path, "w") as f:
        json.dump(data, f, indent=2)
    
    # Save to database
    for song_name, info in data.items():
        uploaded_by = info.get("uploaded_by", "unknown")
        save_metadata_to_db(song_name, uploaded_by)
    
    # Clear cache to force reload
    load_metadata_cached.clear()

def save_shared_link(song_name, link_data):
    """Save shared link to both file and database"""
    # Save to file
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    with open(filepath, 'w') as f:
        json.dump(link_data, f)
    
    # Save to database
    shared_by = link_data.get("shared_by", "unknown")
    save_shared_link_to_db(song_name, shared_by)
    
    # Clear cache
    load_shared_links_cached.clear()

def delete_shared_link(song_name):
    """Delete shared link from both file and database"""
    # Delete from file
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
    
    # Delete from database
    delete_shared_link_from_db(song_name)
    
    # Clear cache
    load_shared_links_cached.clear()

@st.cache_data(ttl=300)
def get_uploaded_songs_cached(show_unshared=False):
    """Get list of uploaded songs with caching"""
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

def get_uploaded_songs(show_unshared=False):
    """Wrapper for backward compatibility"""
    return get_uploaded_songs_cached(show_unshared)

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

# Load metadata with caching
metadata = load_metadata()

# Logo with caching
default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
if not os.path.exists(default_logo_path):
    # Don't show uploader on login page to avoid rerun issues
    pass
logo_b64 = file_to_base64(default_logo_path) if os.path.exists(default_logo_path) else ""

# =============== CHECK FOR DIRECT SONG LINK ===============
query_params = st.query_params
if "song" in query_params and st.session_state.page == "Login":
    song_from_url = unquote(query_params["song"])
    shared_links = load_shared_links()
    if song_from_url in shared_links:
        st.session_state.selected_song = song_from_url
        st.session_state.page = "Song Player"
        st.session_state.user = "guest"
        st.session_state.role = "guest"
        save_session_to_db()

# =============== RESPONSIVE LOGIN PAGE ===============
if st.session_state.page == "Login":
    # Save session state
    save_session_to_db()
    
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

        username = st.text_input("Email / Username", placeholder="admin / user1 / user2", value="", key="login_username")
        password = st.text_input("Password", type="password", placeholder="Enter password", value="", key="login_password")

        if st.button("Login", key="login_button"):
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
                        st.rerun()
                with col3:
                    share_url = f"{APP_URL}#song={safe_s}"
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
                status = "✅ SHARED" if is_shared else "❌ **NOT SHARED"
                st.write(f"{song} - {status}")

            with col2:
                if st.button("🔄 Toggle Share", key=f"toggle_share_{song}"):
                    if is_shared:
                        delete_shared_link(song)
                        st.success(f"✅ {song} unshared! Users can no longer see this song.")
                    else:
                        save_shared_link(song, {"shared_by": st.session_state.user, "active": True})
                        share_url = f"{APP_URL}#song={safe_song}"
                        st.success(f"✅ {song} shared! Link: {share_url}")
                    time.sleep(0.5)
                    st.rerun()

            with col3:
                if is_shared:
                    if st.button("🚫 Unshare", key=f"unshare_{song}"):
                        delete_shared_link(song)
                        st.success(f"✅ {song} unshared! Users cannot see this song anymore.")
                        time.sleep(0.5)
                        st.rerun()

            with col4:
                if is_shared:
                    share_url = f"{APP_URL}#song={safe_song}"
                    st.markdown(f"[📱 Open Link]({share_url})")

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
    uploaded_songs = get_uploaded_songs(show_unshared=False)

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
    
    # Clear cache for this song to ensure fresh loading
    get_cached_base64.clear()
    
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

    # Double-check access permission
    shared_links = load_shared_links()
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
    original_path = os.path.join(songs_dir, f"{selected_song}_original.mp3")
    accompaniment_path = os.path.join(songs_dir, f"{selected_song}_accompaniment.mp3")

    # Find lyrics image
    lyrics_path = ""
    for ext in [".jpg", ".jpeg", ".png"]:
        p = os.path.join(lyrics_dir, f"{selected_song}_lyrics_bg{ext}")
        if os.path.exists(p):
            lyrics_path = p
            break

    # Use cached base64 conversion
    original_b64 = file_to_base64(original_path)
    accompaniment_b64 = file_to_base64(accompaniment_path)
    lyrics_b64 = file_to_base64(lyrics_path)

    # ✅ OPTIMIZED KARAOKE PLAYER - LIGHTER AND FASTER
    karaoke_template = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>🎤 Karaoke Reels</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #000; font-family: 'Poppins', sans-serif; height: 100vh; width: 100vw; overflow: hidden; }
    .reel-container { width: 100%; height: 100%; position: relative; background: #111; }
    #status { position: absolute; top: 20px; width: 100%; text-align: center; font-size: 14px; color: #ccc; z-index: 20; }
    .reel-bg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }
    .controls { position: absolute; bottom: 20%; width: 100%; text-align: center; z-index: 30; }
    button { background: linear-gradient(135deg, #ff0066, #ff66cc); border: none; color: white; padding: 10px 25px; border-radius: 25px; font-size: 14px; margin: 5px; cursor: pointer; }
    button:hover { transform: scale(1.05); }
    #logoImg { position: absolute; top: 20px; left: 20px; width: 60px; z-index: 50; opacity: 0.6; }
    .back-button { position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.7); color: white; padding: 8px 16px; border-radius: 20px; text-decoration: none; font-size: 14px; z-index: 100; }
  </style>
</head>
<body>

<div class="reel-container" id="reelContainer">
    <img class="reel-bg" id="mainBg" src="data:image/jpeg;base64,%%LYRICS_B64%%">
    <img id="logoImg" src="data:image/png;base64,%%LOGO_B64%%">
    <div id="status">Ready 🎤</div>
    
    <div class="controls">
      <button id="playBtn">▶ Play Song</button>
      <button id="recordBtn">🎙 Start Recording</button>
      <button id="stopBtn" style="display:none;">⏹ Stop Recording</button>
    </div>
</div>

<audio id="originalAudio" preload="auto" src="data:audio/mp3;base64,%%ORIGINAL_B64%%"></audio>
<audio id="accompaniment" preload="auto" src="data:audio/mp3;base64,%%ACCOMP_B64%%"></audio>

<script>
/* ================== GLOBAL VARIABLES ================== */
let mediaRecorder = null;
let recordedChunks = [];
let isRecording = false;

/* ================== ELEMENTS ================== */
const playBtn = document.getElementById('playBtn');
const recordBtn = document.getElementById('recordBtn');
const stopBtn = document.getElementById('stopBtn');
const status = document.getElementById('status');
const originalAudio = document.getElementById('originalAudio');
const accompanimentAudio = document.getElementById('accompaniment');

/* ================== PLAY SONG ================== */
playBtn.onclick = async () => {
    try {
        if (originalAudio.paused) {
            originalAudio.currentTime = 0;
            await originalAudio.play();
            playBtn.innerText = "⏸ Pause Song";
            status.innerText = "🎵 Playing song...";
        } else {
            originalAudio.pause();
            playBtn.innerText = "▶ Play Song";
            status.innerText = "⏸ Paused";
        }
    } catch (error) {
        console.error("Play error:", error);
        status.innerText = "❌ Playback error - click again";
    }
};

/* ================== START RECORDING ================== */
recordBtn.onclick = async () => {
    try {
        if (isRecording) return;
        
        isRecording = true;
        recordedChunks = [];
        
        // Start both audios
        originalAudio.currentTime = 0;
        accompanimentAudio.currentTime = 0;
        
        await Promise.all([
            originalAudio.play(),
            accompanimentAudio.play()
        ]);
        
        // Get microphone access
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 44100
            }
        });
        
        // Create audio context for mixing
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const micSource = audioContext.createMediaStreamSource(stream);
        
        // Create destination for mixed audio
        const destination = audioContext.createMediaStreamDestination();
        micSource.connect(destination);
        
        // Create mixed stream (mic only for now)
        const mixedStream = new MediaStream([...destination.stream.getTracks()]);
        
        // Start recording
        mediaRecorder = new MediaRecorder(mixedStream, {
            mimeType: 'audio/webm;codecs=opus'
        });
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(recordedChunks, { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(audioBlob);
            
            // Create download link
            const a = document.createElement('a');
            a.href = audioUrl;
            a.download = `karaoke_${Date.now()}.webm`;
            a.click();
            
            URL.revokeObjectURL(audioUrl);
            status.innerText = "✅ Recording saved!";
        };
        
        mediaRecorder.start();
        
        // Update UI
        playBtn.style.display = 'none';
        recordBtn.style.display = 'none';
        stopBtn.style.display = 'inline-block';
        status.innerText = "🎙 Recording... (speak into mic)";
        
    } catch (error) {
        console.error("Recording error:", error);
        status.innerText = "❌ Recording failed - check microphone";
        isRecording = false;
    }
};

/* ================== STOP RECORDING ================== */
stopBtn.onclick = () => {
    if (!isRecording || !mediaRecorder) return;
    
    mediaRecorder.stop();
    originalAudio.pause();
    accompanimentAudio.pause();
    
    // Update UI
    playBtn.style.display = 'inline-block';
    recordBtn.style.display = 'inline-block';
    stopBtn.style.display = 'none';
    isRecording = false;
};

/* ================== PAGE VISIBILITY HANDLING ================== */
document.addEventListener('visibilitychange', () => {
    if (document.hidden && isRecording) {
        stopBtn.click();
    }
});
</script>
</body>
</html>
"""

    # Replace placeholders with actual base64 data
    karaoke_html = karaoke_template.replace("%%LYRICS_B64%%", lyrics_b64 or "")
    karaoke_html = karaoke_html.replace("%%LOGO_B64%%", logo_b64 or "")
    karaoke_html = karaoke_html.replace("%%ORIGINAL_B64%%", original_b64 or "")
    karaoke_html = karaoke_html.replace("%%ACCOMP_B64%%", accompaniment_b64 or "")

    # Add back button with improved styling
    st.markdown("""
    <div style="position: fixed; top: 10px; right: 10px; z-index: 1000;">
        <button onclick="window.history.back()" style="
            background: rgba(0,0,0,0.7); 
            color: white; 
            border: none; 
            padding: 8px 16px; 
            border-radius: 20px; 
            cursor: pointer;
            font-size: 14px;
        ">← Back</button>
    </div>
    """, unsafe_allow_html=True)

    # Display the player
    html(karaoke_html, height=700, width=1000, scrolling=False)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    save_session_to_db()
    st.rerun()

# =============== CLEANUP OLD SESSIONS ===============
def cleanup_old_sessions():
    """Clean up sessions older than 1 day"""
    try:
        conn = sqlite3.connect(session_db_path, check_same_thread=False)
        c = conn.cursor()
        one_day_ago = datetime.now().timestamp() - 86400
        c.execute("DELETE FROM sessions WHERE last_active < ?", (one_day_ago,))
        conn.commit()
        conn.close()
    except:
        pass

# Run cleanup occasionally
if st.session_state.get("role") == "admin":
    cleanup_old_sessions()
