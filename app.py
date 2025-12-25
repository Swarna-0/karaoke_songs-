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
import mimetypes

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
session_db_path = os.path.join(base_dir, "session_data.db")

# Create directories
os.makedirs(songs_dir, exist_ok=True)
os.makedirs(lyrics_dir, exist_ok=True)
os.makedirs(logo_dir, exist_ok=True)
os.makedirs(shared_links_dir, exist_ok=True)

# =============== CACHE FUNCTIONS ===============
@st.cache_data(ttl=300)
def get_audio_files_b64(song_name):
    """Cache audio files for better performance"""
    original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
    accompaniment_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
    
    original_b64 = ""
    accompaniment_b64 = ""
    
    if os.path.exists(original_path):
        with open(original_path, "rb") as f:
            original_b64 = base64.b64encode(f.read()).decode()
    
    if os.path.exists(accompaniment_path):
        with open(accompaniment_path, "rb") as f:
            accompaniment_b64 = base64.b64encode(f.read()).decode()
    
    return original_b64, accompaniment_b64

@st.cache_data(ttl=300)
def get_lyrics_image_b64(song_name):
    """Cache lyrics images"""
    lyrics_b64 = ""
    for ext in [".jpg", ".jpeg", ".png"]:
        p = os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{ext}")
        if os.path.exists(p):
            with open(p, "rb") as f:
                lyrics_b64 = base64.b64encode(f.read()).decode()
            break
    return lyrics_b64

@st.cache_data(ttl=600)
def load_metadata_cached():
    """Cache metadata loading"""
    file_metadata = {}
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                file_metadata = json.load(f)
        except:
            file_metadata = {}
    return file_metadata

@st.cache_data(ttl=300)
def load_shared_links_cached():
    """Cache shared links"""
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
    return file_links

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
        st.error(f"Save session error: {e}")

def load_session_from_db():
    """Load session from database - simplified to avoid conflicts"""
    try:
        session_id = st.session_state.get('session_id', 'default')
        conn = sqlite3.connect(session_db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user, role FROM sessions WHERE session_id = ?', 
                  (session_id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            user, role = result
            if user and user != 'None' and 'user' not in st.session_state:
                st.session_state.user = user
            if role and role != 'None' and 'role' not in st.session_state:
                st.session_state.role = role
    except:
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
    except:
        pass

def delete_shared_link_from_db(song_name):
    """Delete shared link from database"""
    try:
        conn = sqlite3.connect(session_db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('DELETE FROM shared_links WHERE song_name = ?', (song_name,))
        conn.commit()
        conn.close()
    except:
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
    except:
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
    except:
        pass

# Initialize database
init_session_db()

# =============== HELPER FUNCTIONS ===============
def file_to_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_metadata():
    """Load metadata from cache"""
    return load_metadata_cached()

def save_metadata(data):
    """Save metadata to file"""
    with open(metadata_path, "w") as f:
        json.dump(data, f, indent=2)
    
    # Save to database for important songs
    for song_name, info in data.items():
        uploaded_by = info.get("uploaded_by", "unknown")
        save_metadata_to_db(song_name, uploaded_by)

def load_shared_links():
    """Load shared links from cache"""
    file_links = load_shared_links_cached()
    db_links = load_shared_links_from_db()
    file_links.update(db_links)
    return file_links

def save_shared_link(song_name, link_data):
    """Save shared link"""
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    with open(filepath, 'w') as f:
        json.dump(link_data, f)
    
    shared_by = link_data.get("shared_by", "unknown")
    save_shared_link_to_db(song_name, shared_by)
    
    # Clear cache
    load_shared_links_cached.clear()

def delete_shared_link(song_name):
    """Delete shared link"""
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
    
    delete_shared_link_from_db(song_name)
    
    # Clear cache
    load_shared_links_cached.clear()

@st.cache_data(ttl=300)
def get_uploaded_songs_cached(show_unshared=False):
    """Cache song list retrieval"""
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

def get_uploaded_songs(show_unshared=False):
    """Get list of uploaded songs"""
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

# Load persistent session data - only on login page
if st.session_state.page == "Login":
    load_session_from_db()

metadata = load_metadata()

# Logo
default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
logo_b64 = ""
if os.path.exists(default_logo_path):
    logo_b64 = file_to_base64(default_logo_path)

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
        st.rerun()

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
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
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
                with st.spinner("Logging in..."):
                    time.sleep(0.5)  # Small delay for better UX
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
        
        # Song name input
        song_name = st.text_input("Song Name (without extensions)", 
                                  placeholder="e.g., MyFavoriteSong",
                                  help="Enter a unique name for the song")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            uploaded_original = st.file_uploader("Original Song (*.mp3)", type=["mp3"], key="original_upload")
        with col2:
            uploaded_accompaniment = st.file_uploader("Accompaniment (*.mp3)", type=["mp3"], key="acc_upload")
        with col3:
            uploaded_lyrics_image = st.file_uploader("Lyrics Image (*.jpg, *.png)", type=["jpg", "jpeg", "png"], key="lyrics_upload")

        if uploaded_original and uploaded_accompaniment and uploaded_lyrics_image:
            if not song_name:
                # Extract from filename if not provided
                song_name = uploaded_original.name.replace("_original.mp3", "").replace(".mp3", "").strip()
            
            # Remove any special characters
            song_name = "".join(c for c in song_name if c.isalnum() or c in (' ', '-', '_')).strip()
            
            original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
            acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
            lyrics_ext = os.path.splitext(uploaded_lyrics_image.name)[1].lower()
            lyrics_path = os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{lyrics_ext}")

            if st.button("Upload Song", type="primary"):
                with st.spinner(f"Uploading {song_name}..."):
                    try:
                        with open(original_path, "wb") as f:
                            f.write(uploaded_original.getbuffer())
                        with open(acc_path, "wb") as f:
                            f.write(uploaded_accompaniment.getbuffer())
                        with open(lyrics_path, "wb") as f:
                            f.write(uploaded_lyrics_image.getbuffer())

                        metadata[song_name] = {"uploaded_by": st.session_state.user, "timestamp": str(time.time())}
                        save_metadata(metadata)
                        
                        # Clear caches
                        get_uploaded_songs_cached.clear()
                        get_audio_files_b64.clear()
                        get_lyrics_image_b64.clear()
                        
                        st.success(f"✅ Successfully uploaded: {song_name}")
                        st.balloons()
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Upload failed: {str(e)}")

    elif page_sidebar == "Songs List":
        st.subheader("🎵 All Songs List (Admin View)")
        uploaded_songs = get_uploaded_songs(show_unshared=True)
        
        if not uploaded_songs:
            st.warning("❌ No songs uploaded yet.")
        else:
            st.info(f"Found {len(uploaded_songs)} songs")
            
            for idx, s in enumerate(uploaded_songs):
                col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
                safe_s = quote(s)

                with col1:
                    uploader = metadata.get(s, {}).get('uploaded_by', 'Unknown')
                    st.write(f"**{idx+1}. {s}**")
                    st.caption(f"by {uploader}")
                
                with col2:
                    if st.button("▶ Play", key=f"play_{s}_{idx}", help="Play this song"):
                        st.session_state.selected_song = s
                        st.session_state.page = "Song Player"
                        save_session_to_db()
                        st.rerun()
                
                with col3:
                    share_url = f"{APP_URL}?song={safe_s}"
                    st.markdown(f"[🔗 Copy Share Link]({share_url})", unsafe_allow_html=True)
                
                with col4:
                    if st.button("🗑️", key=f"delete_{s}_{idx}", help="Delete song"):
                        # Delete song files
                        original_path = os.path.join(songs_dir, f"{s}_original.mp3")
                        acc_path = os.path.join(songs_dir, f"{s}_accompaniment.mp3")
                        
                        for ext in [".jpg", ".jpeg", ".png"]:
                            lyrics_path = os.path.join(lyrics_dir, f"{s}_lyrics_bg{ext}")
                            if os.path.exists(lyrics_path):
                                os.remove(lyrics_path)
                        
                        if os.path.exists(original_path):
                            os.remove(original_path)
                        if os.path.exists(acc_path):
                            os.remove(acc_path)
                        
                        # Remove from metadata and shared links
                        if s in metadata:
                            del metadata[s]
                            save_metadata(metadata)
                        
                        delete_shared_link(s)
                        
                        # Clear caches
                        get_uploaded_songs_cached.clear()
                        
                        st.success(f"✅ Deleted: {s}")
                        time.sleep(1)
                        st.rerun()

    elif page_sidebar == "Share Links":
        st.header("🔗 Manage Shared Links")
        all_songs = get_uploaded_songs(show_unshared=True)
        shared_links_data = load_shared_links()

        if not all_songs:
            st.warning("No songs available to share.")
        else:
            for song in all_songs:
                col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1.5])
                safe_song = quote(song)
                is_shared = song in shared_links_data

                with col1:
                    if is_shared:
                        st.success(f"✅ **{song}** - SHARED")
                    else:
                        st.warning(f"❌ **{song}** - NOT SHARED")

                with col2:
                    if st.button("🔄 Toggle", key=f"toggle_share_{song}", help="Toggle sharing status"):
                        if is_shared:
                            delete_shared_link(song)
                            st.success(f"✅ {song} unshared! Users can no longer see this song.")
                        else:
                            save_shared_link(song, {"shared_by": st.session_state.user, "active": True})
                            share_url = f"{APP_URL}?song={safe_song}"
                            st.success(f"✅ {song} shared! Link: {share_url}")
                        time.sleep(0.8)
                        st.rerun()

                with col3:
                    if is_shared:
                        if st.button("🚫 Remove", key=f"unshare_{song}"):
                            delete_shared_link(song)
                            st.success(f"✅ {song} unshared!")
                            time.sleep(0.8)
                            st.rerun()

                with col4:
                    if is_shared:
                        share_url = f"{APP_URL}?song={safe_song}"
                        st.markdown(f'<a href="{share_url}" target="_blank" style="text-decoration:none;"><button style="background:#4CAF50;color:white;border:none;padding:5px 10px;border-radius:5px;cursor:pointer;">📱 Open</button></a>', unsafe_allow_html=True)

    if st.sidebar.button("🚪 Logout", key="admin_logout", type="primary"):
        with st.spinner("Logging out..."):
            time.sleep(0.5)
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
        st.info(f"You have access to {len(uploaded_songs)} shared songs")
        
        for idx, song in enumerate(uploaded_songs):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{idx+1}. {song}**")
                st.caption("Shared song")
            with col2:
                if st.button("▶ Play", key=f"user_play_{song}_{idx}", type="primary"):
                    st.session_state.selected_song = song
                    st.session_state.page = "Song Player"
                    save_session_to_db()
                    st.rerun()
            with col3:
                safe_song = quote(song)
                share_url = f"{APP_URL}?song={safe_song}"
                st.markdown(f"[🔗 Link]({share_url})", unsafe_allow_html=True)

    if st.button("🚪 Logout", key="user_logout", type="primary"):
        with st.spinner("Logging out..."):
            time.sleep(0.5)
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
    
    # Show loading state
    with st.spinner(f"Loading {selected_song}..."):
        # Check access permission
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
        
        # Get cached data
        original_b64, accompaniment_b64 = get_audio_files_b64(selected_song)
        lyrics_b64 = get_lyrics_image_b64(selected_song)
        
        if not original_b64 or not accompaniment_b64:
            st.error("❌ Song files not found or corrupted!")
            if st.button("Go Back"):
                if st.session_state.role == "user":
                    st.session_state.page = "User Dashboard"
                else:
                    st.session_state.page = "Admin Dashboard"
                save_session_to_db()
                st.rerun()
            st.stop()

    # CSS for player
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    div.block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Back button
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("← Back to Dashboard", key="back_player", type="primary"):
            if st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            elif st.session_state.role == "user":
                st.session_state.page = "User Dashboard"
            else:
                st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()

    # HTML Player Template
    karaoke_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Karaoke Player - %%SONG_NAME%%</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #000;
            color: white;
            overflow: hidden;
            height: 100vh;
            width: 100vw;
        }
        
        .player-container {
            width: 100%;
            height: 100%;
            position: relative;
            display: flex;
            flex-direction: column;
        }
        
        .video-container {
            flex: 1;
            position: relative;
            background: #000;
            overflow: hidden;
        }
        
        .lyrics-image {
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
            border: 2px solid rgba(255, 255, 255, 0.4);
            z-index: 10;
        }
        
        .controls-container {
            background: rgba(0, 0, 0, 0.85);
            padding: 15px 20px;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
            justify-content: center;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .control-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
            min-width: 140px;
            justify-content: center;
        }
        
        .control-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .control-btn:active {
            transform: translateY(0);
        }
        
        .control-btn.stop {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
        .control-btn.record {
            background: linear-gradient(135deg, #ff0844 0%, #ffb199 100%);
        }
        
        .status-bar {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.7);
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 14px;
            z-index: 10;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .hidden {
            display: none;
        }
        
        .recording-indicator {
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        
        .modal-content {
            background: rgba(30, 30, 40, 0.95);
            padding: 30px;
            border-radius: 15px;
            max-width: 500px;
            width: 90%;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .modal-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 25px;
        }
        
        .modal-btn {
            padding: 10px 25px;
            border-radius: 20px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .modal-btn.download {
            background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
            color: white;
        }
        
        .modal-btn.new {
            background: linear-gradient(135deg, #2196F3 0%, #0D47A1 100%);
            color: white;
        }
        
        .modal-btn.close {
            background: linear-gradient(135deg, #f44336 0%, #c62828 100%);
            color: white;
        }
    </style>
</head>
<body>
    <div class="player-container">
        <div class="video-container">
            <img class="lyrics-image" id="lyricsImage" src="data:image/jpeg;base64,%%LYRICS_B64%%" alt="Lyrics">
            <img class="logo" id="logoImg" src="data:image/png;base64,%%LOGO_B64%%" alt="Logo">
            <div class="status-bar" id="statusBar">Ready 🎤</div>
            <canvas id="recordingCanvas" width="1920" height="1080" class="hidden"></canvas>
        </div>
        
        <div class="controls-container">
            <button class="control-btn" id="playBtn">
                <span>▶</span> Play Original
            </button>
            <button class="control-btn record" id="recordBtn">
                <span>🎙</span> Start Recording
            </button>
            <button class="control-btn stop hidden" id="stopBtn">
                <span>⏹</span> Stop Recording
            </button>
        </div>
    </div>
    
    <!-- Recording Modal -->
    <div class="modal" id="recordingModal">
        <div class="modal-content">
            <h2 style="margin-bottom: 15px;">🎉 Recording Complete!</h2>
            <p style="color: #ccc; margin-bottom: 20px;">Your karaoke recording is ready. You can download it or start a new recording.</p>
            
            <div class="modal-buttons">
                <button class="modal-btn download" id="downloadBtn">
                    ⬇ Download Recording
                </button>
                <button class="modal-btn new" id="newRecordingBtn">
                    🔄 New Recording
                </button>
                <button class="modal-btn close" id="closeModalBtn">
                    ✕ Close
                </button>
            </div>
        </div>
    </div>
    
    <!-- Hidden audio elements -->
    <audio id="originalAudio" src="data:audio/mp3;base64,%%ORIGINAL_B64%%" preload="auto"></audio>
    <audio id="accompanimentAudio" src="data:audio/mp3;base64,%%ACCOMP_B64%%" preload="auto"></audio>
    
    <script>
        // Global variables
        let mediaRecorder;
        let recordedChunks = [];
        let audioContext;
        let micSource;
        let accSource;
        let canvasStream;
        let isRecording = false;
        let isPlaying = false;
        let currentRecordingUrl = null;
        
        // DOM Elements
        const playBtn = document.getElementById('playBtn');
        const recordBtn = document.getElementById('recordBtn');
        const stopBtn = document.getElementById('stopBtn');
        const statusBar = document.getElementById('statusBar');
        const originalAudio = document.getElementById('originalAudio');
        const accompanimentAudio = document.getElementById('accompanimentAudio');
        const lyricsImage = document.getElementById('lyricsImage');
        const canvas = document.getElementById('recordingCanvas');
        const ctx = canvas.getContext('2d');
        const recordingModal = document.getElementById('recordingModal');
        const downloadBtn = document.getElementById('downloadBtn');
        const newRecordingBtn = document.getElementById('newRecordingBtn');
        const closeModalBtn = document.getElementById('closeModalBtn');
        
        // Initialize audio context
        async function initAudioContext() {
            if (!audioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }
            return audioContext;
        }
        
        // Play original audio
        playBtn.addEventListener('click', async () => {
            await initAudioContext();
            
            if (!isPlaying) {
                try {
                    originalAudio.currentTime = 0;
                    await originalAudio.play();
                    playBtn.innerHTML = '<span>⏸</span> Pause Original';
                    statusBar.textContent = 'Playing original... 🎵';
                    isPlaying = true;
                } catch (error) {
                    console.error('Play error:', error);
                    statusBar.textContent = 'Click to play ▶';
                }
            } else {
                originalAudio.pause();
                playBtn.innerHTML = '<span>▶</span> Play Original';
                statusBar.textContent = 'Paused ⏸';
                isPlaying = false;
            }
        });
        
        // Draw on canvas for recording
        function drawCanvasFrame() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Draw lyrics image
            const imgRatio = lyricsImage.naturalWidth / lyricsImage.naturalHeight;
            const canvasRatio = canvas.width / canvas.height;
            
            let drawWidth, drawHeight, offsetX, offsetY;
            
            if (imgRatio > canvasRatio) {
                // Image is wider than canvas
                drawWidth = canvas.width;
                drawHeight = canvas.width / imgRatio;
                offsetX = 0;
                offsetY = (canvas.height - drawHeight) / 2;
            } else {
                // Image is taller than canvas
                drawHeight = canvas.height;
                drawWidth = canvas.height * imgRatio;
                offsetX = (canvas.width - drawWidth) / 2;
                offsetY = 0;
            }
            
            ctx.drawImage(lyricsImage, offsetX, offsetY, drawWidth, drawHeight);
            
            // Draw logo
            const logoImg = document.getElementById('logoImg');
            if (logoImg.complete) {
                ctx.globalAlpha = 0.6;
                ctx.drawImage(logoImg, 20, 20, 60, 60);
                ctx.globalAlpha = 1;
            }
            
            // Draw recording indicator
            if (isRecording) {
                ctx.fillStyle = '#ff0000';
                ctx.beginPath();
                ctx.arc(50, 100, 10, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = 'white';
                ctx.font = '14px Arial';
                ctx.fillText('REC', 65, 105);
            }
        }
        
        // Start recording
        recordBtn.addEventListener('click', async () => {
            if (isRecording) return;
            
            try {
                await initAudioContext();
                
                // Stop any current playback
                originalAudio.pause();
                accompanimentAudio.pause();
                isPlaying = false;
                playBtn.innerHTML = '<span>▶</span> Play Original';
                
                // Reset recorded chunks
                recordedChunks = [];
                
                // Get microphone access
                const micStream = await navigator.mediaDevices.getUserMedia({ 
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    }
                });
                
                // Create audio sources
                micSource = audioContext.createMediaStreamSource(micStream);
                
                // Load accompaniment
                const accResponse = await fetch(accompanimentAudio.src);
                const accArrayBuffer = await accResponse.arrayBuffer();
                const accAudioBuffer = await audioContext.decodeAudioData(accArrayBuffer);
                
                accSource = audioContext.createBufferSource();
                accSource.buffer = accAudioBuffer;
                
                // Create destination for mixing
                const destination = audioContext.createMediaStreamDestination();
                micSource.connect(destination);
                accSource.connect(destination);
                
                // Start accompaniment
                accSource.start();
                
                // Setup canvas for video
                canvas.width = 1280;
                canvas.height = 720;
                
                // Create canvas stream
                canvasStream = canvas.captureStream(30);
                
                // Mix audio with video
                const mixedStream = new MediaStream([
                    ...canvasStream.getVideoTracks(),
                    ...destination.stream.getAudioTracks()
                ]);
                
                // Setup media recorder
                mediaRecorder = new MediaRecorder(mixedStream, {
                    mimeType: 'video/webm;codecs=vp9,opus'
                });
                
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        recordedChunks.push(event.data);
                    }
                };
                
                mediaRecorder.onstop = () => {
                    // Stop audio sources
                    if (accSource) accSource.stop();
                    
                    // Create blob and URL
                    const blob = new Blob(recordedChunks, { type: 'video/webm' });
                    
                    // Clean up previous URL
                    if (currentRecordingUrl) {
                        URL.revokeObjectURL(currentRecordingUrl);
                    }
                    
                    currentRecordingUrl = URL.createObjectURL(blob);
                    
                    // Setup download
                    downloadBtn.onclick = () => {
                        const a = document.createElement('a');
                        a.href = currentRecordingUrl;
                        a.download = `karaoke_${Date.now()}.webm`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                    };
                    
                    // Show modal
                    recordingModal.style.display = 'flex';
                    statusBar.textContent = 'Recording complete! 🎉';
                };
                
                // Start recording
                mediaRecorder.start(1000); // Collect data every second
                isRecording = true;
                
                // Update UI
                recordBtn.classList.add('hidden');
                stopBtn.classList.remove('hidden');
                statusBar.textContent = 'Recording... 🎙';
                statusBar.classList.add('recording-indicator');
                
                // Start canvas drawing
                function drawLoop() {
                    if (!isRecording) return;
                    drawCanvasFrame();
                    requestAnimationFrame(drawLoop);
                }
                drawLoop();
                
                // Start playback
                originalAudio.currentTime = 0;
                accompanimentAudio.currentTime = 0;
                
                try {
                    await Promise.all([
                        originalAudio.play(),
                        accompanimentAudio.play()
                    ]);
                } catch (error) {
                    console.log('Autoplay might be blocked:', error);
                }
                
            } catch (error) {
                console.error('Recording error:', error);
                statusBar.textContent = 'Recording failed 😢';
                if (error.name === 'NotAllowedError') {
                    alert('Please allow microphone access to record.');
                }
                resetRecordingState();
            }
        });
        
        // Stop recording
        stopBtn.addEventListener('click', () => {
            if (!isRecording || !mediaRecorder) return;
            
            mediaRecorder.stop();
            isRecording = false;
            
            // Stop playback
            originalAudio.pause();
            accompanimentAudio.pause();
            
            // Update UI
            stopBtn.classList.add('hidden');
            recordBtn.classList.remove('hidden');
            statusBar.classList.remove('recording-indicator');
            statusBar.textContent = 'Processing recording...';
        });
        
        // Modal buttons
        newRecordingBtn.addEventListener('click', () => {
            recordingModal.style.display = 'none';
            resetRecordingState();
            statusBar.textContent = 'Ready for new recording 🎤';
        });
        
        closeModalBtn.addEventListener('click', () => {
            recordingModal.style.display = 'none';
            statusBar.textContent = 'Ready 🎤';
        });
        
        // Reset recording state
        function resetRecordingState() {
            isRecording = false;
            recordBtn.classList.remove('hidden');
            stopBtn.classList.add('hidden');
            statusBar.classList.remove('recording-indicator');
            
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                try {
                    mediaRecorder.stop();
                } catch (e) {}
            }
            
            if (accSource) {
                try {
                    accSource.stop();
                } catch (e) {}
            }
        }
        
        // Initialize
        window.addEventListener('load', () => {
            statusBar.textContent = 'Ready 🎤';
            
            // Preload audio
            originalAudio.load();
            accompanimentAudio.load();
            
            // Handle page visibility changes
            document.addEventListener('visibilitychange', () => {
                if (document.hidden && isRecording) {
                    stopBtn.click();
                }
            });
        });
        
        // Clean up on page unload
        window.addEventListener('beforeunload', () => {
            if (currentRecordingUrl) {
                URL.revokeObjectURL(currentRecordingUrl);
            }
        });
    </script>
</body>
</html>
    """
    
    # Replace placeholders in template
    karaoke_html = karaoke_template.replace("%%SONG_NAME%%", selected_song)
    karaoke_html = karaoke_html.replace("%%LYRICS_B64%%", lyrics_b64 or "")
    karaoke_html = karaoke_html.replace("%%LOGO_B64%%", logo_b64 or "")
    karaoke_html = karaoke_html.replace("%%ORIGINAL_B64%%", original_b64 or "")
    karaoke_html = karaoke_html.replace("%%ACCOMP_B64%%", accompaniment_b64 or "")
    
    # Display the player
    html(karaoke_html, height=750, scrolling=False)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    save_session_to_db()
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
            st.write(f"Session ID: {st.session_state.get('session_id', 'N/A')}")
            
            if st.button("Clear All Caches", key="clear_caches"):
                # Clear all caches
                get_audio_files_b64.clear()
                get_lyrics_image_b64.clear()
                get_uploaded_songs_cached.clear()
                load_metadata_cached.clear()
                load_shared_links_cached.clear()
                st.success("Caches cleared!")
            
            if st.button("Force Reset Session", key="debug_reset"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.page = "Login"
                save_session_to_db()
                st.rerun()
