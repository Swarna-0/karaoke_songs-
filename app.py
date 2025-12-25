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
import urllib.parse

st.set_page_config(page_title="𝄞 sing-along", layout="wide")

# --------- CONFIG: set your deployed app URL here ----------
APP_URL = "https://karaoke-project-production.up.railway.app/"  # నీ Railway URL ఇక్కడ ఉంచు

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

# =============== PERSISTENT SESSION DATABASE ===============
def init_session_db():
    """Initialize SQLite database for persistent sessions"""
    try:
        conn = sqlite3.connect(session_db_path)
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
        st.error(f"Database error: {e}")

def save_session_to_db():
    """Save current session to database"""
    try:
        conn = sqlite3.connect(session_db_path)
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
        st.error(f"Save session error: {e}")

def load_session_from_db():
    """Load session from database"""
    try:
        session_id = st.session_state.get('session_id', 'default')
        conn = sqlite3.connect(session_db_path)
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
        st.error(f"Load session error: {e}")

def save_shared_link_to_db(song_name, shared_by):
    """Save shared link to database"""
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO shared_links 
                     (song_name, shared_by, active, created_at)
                     VALUES (?, ?, ?, ?)''',
                  (song_name, shared_by, True, datetime.now()))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Save shared link error: {e}")

def delete_shared_link_from_db(song_name):
    """Delete shared link from database"""
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('DELETE FROM shared_links WHERE song_name = ?', (song_name,))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Delete shared link error: {e}")

def load_shared_links_from_db():
    """Load shared links from database"""
    links = {}
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('SELECT song_name, shared_by FROM shared_links WHERE active = 1')
        results = c.fetchall()
        conn.close()
        
        for song_name, shared_by in results:
            links[song_name] = {"shared_by": shared_by, "active": True}
    except Exception as e:
        st.error(f"Load shared links error: {e}")
    return links

def save_metadata_to_db(song_name, uploaded_by):
    """Save metadata to database"""
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO metadata 
                     (song_name, uploaded_by, timestamp)
                     VALUES (?, ?, ?)''',
                  (song_name, uploaded_by, time.time()))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Save metadata error: {e}")

def load_metadata_from_db():
    """Load metadata from database"""
    metadata = {}
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('SELECT song_name, uploaded_by FROM metadata')
        results = c.fetchall()
        conn.close()
        
        for song_name, uploaded_by in results:
            metadata[song_name] = {"uploaded_by": uploaded_by, "timestamp": str(time.time())}
    except Exception as e:
        st.error(f"Load metadata error: {e}")
    return metadata

# Initialize database
init_session_db()

# =============== HELPER FUNCTIONS ===============
def file_to_base64(path):
    """Small files కోసం మాత్రమే base64 ఉపయోగించు (logo, small images)"""
    if os.path.exists(path):
        file_size = os.path.getsize(path)
        # Large files (1MB కంటే ఎక్కువ) base64 లో convert చేయకు
        if file_size > 1024 * 1024:  # 1MB
            return ""
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except:
            return ""
    return ""

def get_file_url(file_path):
    """File కి direct URL ఇవ్వడానికి"""
    if os.path.exists(file_path):
        # Railway లో static files serve చేయడానికి
        relative_path = os.path.relpath(file_path, base_dir)
        return f"{APP_URL.rstrip('/')}/{urllib.parse.quote(relative_path)}"
    return ""

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_metadata():
    """Load metadata from both file and database"""
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

def save_metadata(data):
    """Save metadata to both file and database"""
    # Save to file
    with open(metadata_path, "w") as f:
        json.dump(data, f, indent=2)
    
    # Save to database
    for song_name, info in data.items():
        uploaded_by = info.get("uploaded_by", "unknown")
        save_metadata_to_db(song_name, uploaded_by)

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
                except:
                    pass
    
    # Merge with database links
    db_links = load_shared_links_from_db()
    file_links.update(db_links)
    return file_links

def save_shared_link(song_name, link_data):
    """Save shared link to both file and database"""
    # Save to file
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    with open(filepath, 'w') as f:
        json.dump(link_data, f)
    
    # Save to database
    shared_by = link_data.get("shared_by", "unknown")
    save_shared_link_to_db(song_name, shared_by)

def delete_shared_link(song_name):
    """Delete shared link from both file and database"""
    # Delete from file
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
    
    # Delete from database
    delete_shared_link_from_db(song_name)

def get_uploaded_songs(show_unshared=False):
    """Get list of uploaded songs"""
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

def check_and_create_session_id():
    """Create unique session ID if not exists"""
    if 'session_id' not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())

# =============== STATIC FILE SERVER SETUP ===============
# Railway లో static files serve చేయడానికి
@st.cache_resource
def serve_static_files():
    """Static files serve చేయడానికి setup"""
    import mimetypes
    from pathlib import Path
    
    # మీ media files Railway లో serve అవుతాయి
    st.markdown(f"""
    <script>
    // Static files base URL
    window.STATIC_URL = "{APP_URL.rstrip('/')}";
    </script>
    """, unsafe_allow_html=True)

# =============== INITIALIZE SESSION ===============
check_and_create_session_id()
serve_static_files()

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

metadata = load_metadata()

# Logo
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

    .credentials-info {
        background: rgba(5,10,25,0.8);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 10px;
        padding: 12px;
        margin-top: 16px;
        font-size: 0.85rem;
        color: #b5c2d2;
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
                status = "✅ SHARED" if is_shared else "❌ **NOT SHARED"
                st.write(f"{song} - {status}")

            with col2:
                if st.button("🔄 Toggle Share", key=f"toggle_share_{song}"):
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
                    if st.button("🚫 Unshare", key=f"unshare_{song}"):
                        delete_shared_link(song)
                        st.success(f"✅ {song} unshared! Users cannot see this song anymore.")
                        time.sleep(0.5)
                        st.rerun()

            with col4:
                if is_shared:
                    share_url = f"{APP_URL}?song={safe_song}"
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

    original_path = os.path.join(songs_dir, f"{selected_song}_original.mp3")
    accompaniment_path = os.path.join(songs_dir, f"{selected_song}_accompaniment.mp3")

    lyrics_path = ""
    for ext in [".jpg", ".jpeg", ".png"]:
        p = os.path.join(lyrics_dir, f"{selected_song}_lyrics_bg{ext}")
        if os.path.exists(p):
            lyrics_path = p
            break

    # Large files కోసం direct URLs ఉపయోగించు
    original_url = get_file_url(original_path)
    accompaniment_url = get_file_url(accompaniment_path)
    
    # Small files మాత్రమే base64 లో (logo మరియు lyrics image)
    lyrics_b64 = file_to_base64(lyrics_path) if os.path.exists(lyrics_path) else ""
    # Logo small కాబట్టి base64 లో ఉంచు
    logo_b64 = file_to_base64(default_logo_path) if os.path.exists(default_logo_path) else ""

    # ✅ OPTIMIZED HTML PLAYER WITH DIRECT URLs
    karaoke_template = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>🎤 Karaoke Reels</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      background: #000; 
      font-family: 'Poppins', sans-serif; 
      height: 100vh; 
      width: 100vw; 
      overflow: hidden;
      -webkit-font-smoothing: antialiased;
    }
    
    .reel-container, .final-reel-container { 
      width: 100%; 
      height: 100%; 
      position: absolute; 
      background: #111; 
      overflow: hidden;
      top: 0;
      left: 0;
    }
    
    #status { 
      position: absolute; 
      top: 20px; 
      width: 100%; 
      text-align: center; 
      font-size: 14px; 
      color: #ccc; 
      z-index: 20; 
      text-shadow: 1px 1px 6px rgba(0,0,0,0.9);
      pointer-events: none;
    }
    
    .reel-bg { 
      position: absolute; 
      top: 0; 
      left: 0; 
      width: 100%; 
      height: 85vh; 
      object-fit: contain;
      object-position: top;
      background: #000;
    }
    
    .controls { 
      position: absolute; 
      bottom: 20%; 
      width: 100%; 
      text-align: center; 
      z-index: 30;
    }
    
    button { 
      background: linear-gradient(135deg, #ff0066, #ff66cc);
      border: none; 
      color: white; 
      padding: 12px 24px; 
      border-radius: 25px; 
      font-size: 14px; 
      margin: 8px; 
      box-shadow: 0px 3px 15px rgba(255,0,128,0.4); 
      cursor: pointer;
      font-weight: bold;
      transition: transform 0.2s, opacity 0.2s;
      min-width: 140px;
    }
    
    button:hover {
      transform: scale(1.05);
      opacity: 0.9;
    }
    
    button:active { transform: scale(0.95); }
    
    #logoImg { 
      position: absolute; 
      top: 20px; 
      left: 20px; 
      width: 60px; 
      height: 60px;
      z-index: 50; 
      opacity: 0.7;
      border-radius: 50%;
      border: 2px solid rgba(255,255,255,0.3);
    }
    
    .back-button { 
      position: absolute; 
      top: 20px; 
      right: 20px; 
      background: rgba(0,0,0,0.7); 
      color: white; 
      padding: 10px 20px; 
      border-radius: 20px; 
      text-decoration: none; 
      font-size: 14px; 
      z-index: 100;
      border: 1px solid rgba(255,255,255,0.2);
    }
    
    .back-button:hover {
      background: rgba(0,0,0,0.9);
    }
    
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
    }
    
    canvas { display: none; }
    
    .loading { 
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      color: white;
      font-size: 18px;
      z-index: 1000;
    }
  </style>
</head>
<body>

<!-- Loading Indicator -->
<div class="loading" id="loadingIndicator">
  🎵 Loading song...
</div>

<div class="reel-container" id="reelContainer" style="display:none;">
    <img class="reel-bg" id="mainBg" src="data:image/jpeg;base64,%%LYRICS_B64%%" 
         onload="document.getElementById('loadingIndicator').style.display='none'; document.getElementById('reelContainer').style.display='block';"
         onerror="document.getElementById('loadingIndicator').innerHTML='❌ Image load failed';">
    <img id="logoImg" src="data:image/png;base64,%%LOGO_B64%%">
    <div id="status">Ready 🎤 Click Play to start</div>
    
    <!-- Audio elements with preload="none" for faster loading -->
    <audio id="originalAudio" preload="none">
      <source src="%%ORIGINAL_URL%%" type="audio/mp3">
    </audio>
    <audio id="accompaniment" preload="none">
      <source src="%%ACCOMP_URL%%" type="audio/mp3">
    </audio>
    
    <div class="controls">
      <button id="playBtn">▶ Play Song</button>
      <button id="recordBtn">🎙 Start Recording</button>
      <button id="stopBtn" style="display:none;">⏹ Stop Recording</button>
    </div>
    
    <a href="#" class="back-button" id="backBtn">← Back to Dashboard</a>
</div>

<div class="final-output" id="finalOutputDiv">
  <div class="final-reel-container">
    <img class="reel-bg" id="finalBg">
    <div class="controls">
      <button id="playRecordingBtn">▶ Play Recording</button>
      <a id="downloadRecordingBtn" href="#" download>
        <button>⬇ Download Video</button>
      </a>
      <button id="newRecordingBtn">🔄 New Recording</button>
    </div>
  </div>
</div>

<canvas id="recordingCanvas" width="1920" height="1080"></canvas>

<script>
/* ================== GLOBAL STATE ================== */
let mediaRecorder;
let recordedChunks = [];
let playRecordingAudio = null;
let lastRecordingURL = null;
let audioContext, micSource, accSource;
let canvasRafId = null;
let isRecording = false;
let isPlayingRecording = false;

/* ================== ELEMENTS ================== */
const playBtn = document.getElementById("playBtn");
const recordBtn = document.getElementById("recordBtn");
const stopBtn = document.getElementById("stopBtn");
const status = document.getElementById("status");
const originalAudio = document.getElementById("originalAudio");
const accompanimentAudio = document.getElementById("accompaniment");
const finalDiv = document.getElementById("finalOutputDiv");
const mainBg = document.getElementById("mainBg");
const finalBg = document.getElementById("finalBg");
const playRecordingBtn = document.getElementById("playRecordingBtn");
const downloadRecordingBtn = document.getElementById("downloadRecordingBtn");
const newRecordingBtn = document.getElementById("newRecordingBtn");
const canvas = document.getElementById("recordingCanvas");
const ctx = canvas.getContext("2d");
const logoImg = document.getElementById("logoImg");
const backBtn = document.getElementById("backBtn");

/* ================== INITIAL LOAD ================== */
// Preload audio for faster playback
setTimeout(() => {
    originalAudio.load();
    accompanimentAudio.load();
}, 500);

/* ================== BACK BUTTON ================== */
backBtn.onclick = (e) => {
    e.preventDefault();
    if (window.parent && window.parent.postMessage) {
        window.parent.postMessage({type: 'go_back'}, '*');
    }
};

/* ================== AUDIO CONTEXT FIX ================== */
async function ensureAudioContext() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioContext.state === "suspended") {
        await audioContext.resume();
    }
    return audioContext;
}

async function safePlay(audio) {
    try {
        await ensureAudioContext();
        const playPromise = audio.play();
        if (playPromise !== undefined) {
            await playPromise;
        }
        return true;
    } catch (e) {
        console.log("Playback error:", e);
        status.innerText = "⚠️ Click play again to start audio";
        return false;
    }
}

/* ================== PLAY ORIGINAL ================== */
playBtn.onclick = async () => {
    await ensureAudioContext();
    
    if (originalAudio.paused) {
        originalAudio.currentTime = 0;
        accompanimentAudio.currentTime = 0;
        
        const played = await safePlay(originalAudio);
        if (played) {
            await safePlay(accompanimentAudio);
            playBtn.innerText = "⏸ Pause";
            status.innerText = "🎵 Playing...";
        }
    } else {
        originalAudio.pause();
        accompanimentAudio.pause();
        playBtn.innerText = "▶ Play Song";
        status.innerText = "⏸ Paused";
    }
};

/* ================== CANVAS DRAW ================== */
function drawCanvas() {
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const canvasW = canvas.width;
    const canvasH = canvas.height * 0.85;

    const imgRatio = mainBg.naturalWidth / mainBg.naturalHeight;
    const canvasRatio = canvasW / canvasH;

    let drawW, drawH;
    if (imgRatio > canvasRatio) {
        drawW = canvasW;
        drawH = canvasW / imgRatio;
    } else {
        drawH = canvasH;
        drawW = canvasH * imgRatio;
    }

    const x = (canvasW - drawW) / 2;
    const y = 0;

    ctx.drawImage(mainBg, x, y, drawW, drawH);
    ctx.globalAlpha = 0.7;
    ctx.drawImage(logoImg, 20, 20, 60, 60);
    ctx.globalAlpha = 1;

    canvasRafId = requestAnimationFrame(drawCanvas);
}

/* ================== RECORD ================== */
recordBtn.onclick = async () => {
    if (isRecording) return;
    
    try {
        isRecording = true;
        await ensureAudioContext();
        recordedChunks = [];

        // Start both audios first
        originalAudio.currentTime = 0;
        accompanimentAudio.currentTime = 0;
        
        const played = await safePlay(originalAudio);
        if (!played) {
            isRecording = false;
            status.innerText = "❌ Please click Play first to enable audio";
            return;
        }
        await safePlay(accompanimentAudio);

        // Get microphone
        const micStream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });
        
        micSource = audioContext.createMediaStreamSource(micStream);

        // Get accompaniment as buffer
        const accRes = await fetch("%%ACCOMP_URL%%");
        const accBuf = await accRes.arrayBuffer();
        const accDecoded = await audioContext.decodeAudioData(accBuf);
        accSource = audioContext.createBufferSource();
        accSource.buffer = accDecoded;

        // Create destination
        const destination = audioContext.createMediaStreamDestination();
        micSource.connect(destination);
        accSource.connect(destination);
        accSource.start();

        // Setup canvas
        canvas.width = 1920;
        canvas.height = 1080;
        drawCanvas();

        // Combine video and audio
        const canvasStream = canvas.captureStream(25);
        const combinedStream = new MediaStream([
            ...canvasStream.getVideoTracks(),
            ...destination.stream.getAudioTracks()
        ]);

        // Start recording
        mediaRecorder = new MediaRecorder(combinedStream, {
            mimeType: 'video/webm;codecs=vp9,opus'
        });
        
        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                recordedChunks.push(e.data);
            }
        };

        mediaRecorder.onstop = () => {
            cancelAnimationFrame(canvasRafId);
            
            const blob = new Blob(recordedChunks, { type: "video/webm" });
            const url = URL.createObjectURL(blob);
            
            if (lastRecordingURL) URL.revokeObjectURL(lastRecordingURL);
            lastRecordingURL = url;
            
            finalBg.src = mainBg.src;
            finalDiv.style.display = "flex";
            downloadRecordingBtn.href = url;
            downloadRecordingBtn.download = `karaoke_${Date.now()}.webm`;
        };

        mediaRecorder.start(1000); // Collect data every second
        
        // Update UI
        playBtn.style.display = "none";
        recordBtn.style.display = "none";
        stopBtn.style.display = "inline-block";
        status.innerText = "🎙 Recording... Click Stop when done";

    } catch (error) {
        console.error("Recording error:", error);
        status.innerText = "❌ Recording failed: " + error.message;
        isRecording = false;
        playBtn.style.display = "inline-block";
        recordBtn.style.display = "inline-block";
        stopBtn.style.display = "none";
    }
};

/* ================== STOP ================== */
stopBtn.onclick = () => {
    if (!isRecording) return;
    
    isRecording = false;
    
    try { 
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
    } catch(e) {}
    
    try { 
        if (accSource) {
            accSource.stop();
        }
    } catch(e) {}
    
    // Stop audios
    originalAudio.pause();
    accompanimentAudio.pause();
    
    // Stop all tracks
    if (mediaRecorder && mediaRecorder.stream) {
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    
    stopBtn.style.display = "none";
    status.innerText = "✅ Processing recording...";
};

/* ================== PLAY RECORDING ================== */
playRecordingBtn.onclick = () => {
    if (!isPlayingRecording && lastRecordingURL) {
        if (playRecordingAudio) {
            playRecordingAudio.pause();
            playRecordingAudio.currentTime = 0;
        }
        
        playRecordingAudio = new Audio(lastRecordingURL);
        playRecordingAudio.play();
        playRecordingBtn.innerText = "⏹ Stop";
        isPlayingRecording = true;
        
        playRecordingAudio.onended = () => {
            playRecordingBtn.innerText = "▶ Play Recording";
            isPlayingRecording = false;
        };
    } else {
        if (playRecordingAudio) {
            playRecordingAudio.pause();
            playRecordingAudio.currentTime = 0;
        }
        playRecordingBtn.innerText = "▶ Play Recording";
        isPlayingRecording = false;
    }
};

/* ================== NEW RECORDING ================== */
newRecordingBtn.onclick = () => {
    finalDiv.style.display = "none";
    
    recordedChunks = [];
    isRecording = false;
    isPlayingRecording = false;
    
    originalAudio.pause();
    accompanimentAudio.pause();
    originalAudio.currentTime = 0;
    accompanimentAudio.currentTime = 0;
    
    if (playRecordingAudio) {
        playRecordingAudio.pause();
        playRecordingAudio = null;
    }
    
    playBtn.style.display = "inline-block";
    recordBtn.style.display = "inline-block";
    stopBtn.style.display = "none";
    playBtn.innerText = "▶ Play Song";
    status.innerText = "Ready 🎤";
};

/* ================== CLEANUP ================== */
window.addEventListener('beforeunload', () => {
    if (lastRecordingURL) {
        URL.revokeObjectURL(lastRecordingURL);
    }
    if (canvasRafId) {
        cancelAnimationFrame(canvasRafId);
    }
});

/* ================== ERROR HANDLING ================== */
window.addEventListener('error', (e) => {
    console.error("Global error:", e.error);
    status.innerText = "⚠️ An error occurred. Try refreshing.";
});

</script>
</body>
</html>
"""

    # Replace placeholders in template
    karaoke_html = karaoke_template.replace("%%LYRICS_B64%%", lyrics_b64 or "")
    karaoke_html = karaoke_html.replace("%%LOGO_B64%%", logo_b64 or "")
    karaoke_html = karaoke_html.replace("%%ORIGINAL_URL%%", original_url or "")
    karaoke_html = karaoke_html.replace("%%ACCOMP_URL%%", accompaniment_url or "")

    # Back button handler
    if st.button("← Back to Dashboard", key="back_player"):
        if st.session_state.role == "admin":
            st.session_state.page = "Admin Dashboard"
        elif st.session_state.role == "user":
            st.session_state.page = "User Dashboard"
        else:
            st.session_state.page = "Login"
        save_session_to_db()
        st.rerun()

    # Display the player
    html(karaoke_html, height=800, width=1920, scrolling=False)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    save_session_to_db()
    st.rerun()

# =============== DEBUG INFO ===============
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
                st.session_state.page = "Login"
                save_session_to_db()
                st.rerun()
