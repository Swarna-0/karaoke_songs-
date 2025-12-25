import streamlit as st
import os
import base64
import json
from streamlit.components.v1 import html
import hashlib
from urllib.parse import unquote, quote
import time
import pickle
import sqlite3
from datetime import datetime

st.set_page_config(
    page_title="𝄞 sing-along", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

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

# =============== PERSISTENT SESSION DATABASE ===============
def init_session_db():
    """Initialize SQLite database for persistent sessions"""
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
    except:
        pass

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
            if user:
                st.session_state.user = user
            if role:
                st.session_state.role = role
            if page:
                st.session_state.page = page
            if selected_song:
                st.session_state.selected_song = selected_song
    except:
        pass

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
    except:
        pass

def delete_shared_link_from_db(song_name):
    """Delete shared link from database"""
    try:
        conn = sqlite3.connect(session_db_path)
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
        conn = sqlite3.connect(session_db_path)
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
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO metadata 
                     (song_name, uploaded_by, timestamp)
                     VALUES (?, ?, ?)''',
                  (song_name, uploaded_by, time.time()))
        conn.commit()
        conn.close()
    except:
        pass

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
    except:
        pass
    return metadata

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

# =============== INITIALIZE SESSION ===============
check_and_create_session_id()

# Initialize session state with default values
default_state = {
    'user': None,
    'role': None,
    'page': 'Login',
    'selected_song': None,
    'init': True
}

for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Load persistent session data
load_session_from_db()

# Load metadata
metadata = load_metadata()

# =============== LOGO HANDLING ===============
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

    .login-content {
        padding: 2rem;
        background: rgba(2, 7, 18, 0.95);
        border-radius: 15px;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }

    .login-header {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        margin-bottom: 2rem;
        text-align: center;
    }

    .login-header img {
        width: 70px;
        height: 70px;
        border-radius: 50%;
        border: 2px solid rgba(255,255,255,0.4);
    }

    .login-title {
        font-size: 1.8rem;
        font-weight: 700;
        width: 100%;
        color: white;
    }

    .login-sub {
        font-size: 1rem;
        color: #c3cfdd;
        margin-bottom: 0.5rem;
        width: 100%;
    }

    .stTextInput input {
        background: rgba(5,10,25,0.8) !important;
        border-radius: 12px !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        padding: 14px 16px !important;
        font-size: 16px;
    }

    .stTextInput input:focus {
        border-color: rgba(255,255,255,0.6) !important;
        box-shadow: 0 0 0 2px rgba(255,255,255,0.2);
    }

    .stButton button {
        width: 100%;
        height: 50px;
        background: linear-gradient(to right, #1f2937, #020712);
        border-radius: 12px;
        font-weight: 600;
        margin-top: 1rem;
        color: white;
        border: none;
        font-size: 16px;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        background: linear-gradient(to right, #2d3748, #111827);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)

    left, center, right = st.columns([1, 1.5, 1])

    with center:
        st.markdown('<div class="login-content">', unsafe_allow_html=True)

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

        username = st.text_input("Username", placeholder="admin / user1 / user2", key="login_username")
        password = st.text_input("Password", type="password", placeholder="Enter password", key="login_password")

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
        <div style="margin-top:20px;font-size:0.9rem;color:#b5c2d2;text-align:center;padding-bottom:10px;">
            Don't have access? Contact admin.
        </div>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

# =============== ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    # Auto-save session
    save_session_to_db()
    
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #020617 100%);
    }
    
    .stButton button {
        transition: all 0.2s ease;
    }
    
    .stButton button:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    
    .song-item {
        padding: 12px;
        border-radius: 10px;
        margin: 8px 0;
        background: rgba(255,255,255,0.05);
        border-left: 4px solid #3b82f6;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title(f"👑 Admin Dashboard")
    st.subheader(f"Welcome, {st.session_state.user}")
    
    # Sidebar
    with st.sidebar:
        st.image(f"data:image/png;base64,{logo_b64}", width=80) if logo_b64 else None
        st.markdown("### Navigation")
        page_sidebar = st.radio(
            "Menu", 
            ["Upload Songs", "Songs List", "Share Links"],
            key="admin_nav"
        )
        
        st.markdown("---")
        st.markdown("### Quick Actions")
        
        if st.button("🔄 Refresh Data", key="refresh_data", use_container_width=True):
            st.rerun()
            
        if st.button("🚪 Logout", key="admin_logout", use_container_width=True):
            st.session_state.clear()
            st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
    
    # Main content based on selection
    if page_sidebar == "Upload Songs":
        st.header("📤 Upload New Song")
        st.info("Upload all three files for a complete karaoke experience")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            uploaded_original = st.file_uploader(
                "Original Song", 
                type=["mp3"], 
                key="original_upload",
                help="File should end with '_original.mp3'"
            )
        with col2:
            uploaded_accompaniment = st.file_uploader(
                "Accompaniment", 
                type=["mp3"], 
                key="acc_upload",
                help="File should end with '_accompaniment.mp3'"
            )
        with col3:
            uploaded_lyrics_image = st.file_uploader(
                "Lyrics Image", 
                type=["jpg", "jpeg", "png"], 
                key="lyrics_upload",
                help="File should end with '_lyrics_bg.jpg/png'"
            )
        
        if uploaded_original and uploaded_accompaniment and uploaded_lyrics_image:
            song_name = st.text_input(
                "Song Name", 
                value=uploaded_original.name.replace("_original.mp3", "").strip(),
                help="Enter a name for this song"
            )
            
            if st.button("Upload Song", key="upload_song_btn", type="primary"):
                if not song_name:
                    song_name = os.path.splitext(uploaded_original.name)[0]
                
                # Save files
                original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
                acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
                lyrics_ext = os.path.splitext(uploaded_lyrics_image.name)[1]
                lyrics_path = os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{lyrics_ext}")
                
                try:
                    with open(original_path, "wb") as f:
                        f.write(uploaded_original.getbuffer())
                    with open(acc_path, "wb") as f:
                        f.write(uploaded_accompaniment.getbuffer())
                    with open(lyrics_path, "wb") as f:
                        f.write(uploaded_lyrics_image.getbuffer())
                    
                    # Update metadata
                    metadata[song_name] = {
                        "uploaded_by": st.session_state.user, 
                        "timestamp": str(time.time()),
                        "files": {
                            "original": original_path,
                            "accompaniment": acc_path,
                            "lyrics": lyrics_path
                        }
                    }
                    save_metadata(metadata)
                    
                    st.success(f"✅ **{song_name}** uploaded successfully!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error uploading files: {str(e)}")
    
    elif page_sidebar == "Songs List":
        st.header("🎵 All Songs")
        
        uploaded_songs = get_uploaded_songs(show_unshared=True)
        
        if not uploaded_songs:
            st.warning("No songs uploaded yet. Go to 'Upload Songs' to add songs.")
        else:
            st.success(f"Found {len(uploaded_songs)} song(s)")
            
            for idx, song in enumerate(uploaded_songs):
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 2])
                    
                    with col1:
                        st.markdown(f"""
                        <div class="song-item">
                            <h4>{song}</h4>
                            <p style="color: #888; font-size: 0.9em;">
                                Uploaded by: {metadata.get(song, {}).get('uploaded_by', 'Unknown')}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        if st.button("▶ Play", key=f"admin_play_{song}_{idx}"):
                            st.session_state.selected_song = song
                            st.session_state.page = "Song Player"
                            save_session_to_db()
                            st.rerun()
                    
                    with col3:
                        safe_song = quote(song)
                        share_url = f"{APP_URL}?song={safe_song}"
                        st.markdown(f"**Share Link:**")
                        st.code(share_url, language=None)
    
    elif page_sidebar == "Share Links":
        st.header("🔗 Manage Shared Links")
        
        all_songs = get_uploaded_songs(show_unshared=True)
        shared_links = load_shared_links()
        
        if not all_songs:
            st.warning("No songs available to share.")
        else:
            st.info(f"Total songs: {len(all_songs)} | Shared: {len(shared_links)}")
            
            for song in all_songs:
                is_shared = song in shared_links
                safe_song = quote(song)
                share_url = f"{APP_URL}?song={safe_song}"
                
                with st.expander(f"{'✅' if is_shared else '❌'} {song}", expanded=False):
                    col1, col2 = st.columns([3, 2])
                    
                    with col1:
                        if is_shared:
                            st.success(f"**Status:** Shared ✅")
                            st.markdown(f"**Link:** `{share_url}`")
                            st.markdown(f"**Shared by:** {shared_links[song].get('shared_by', 'Unknown')}")
                        else:
                            st.warning("**Status:** Not Shared ❌")
                    
                    with col2:
                        if is_shared:
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.button("Copy Link", key=f"copy_{song}"):
                                    st.code(share_url, language=None)
                                    st.success("Link copied!")
                            with col_btn2:
                                if st.button("Unshare", key=f"unshare_{song}"):
                                    delete_shared_link(song)
                                    st.success(f"✅ {song} unshared!")
                                    time.sleep(0.5)
                                    st.rerun()
                        else:
                            if st.button("Share Now", key=f"share_{song}", type="primary"):
                                save_shared_link(song, {
                                    "shared_by": st.session_state.user, 
                                    "active": True,
                                    "shared_at": str(time.time())
                                })
                                st.success(f"✅ {song} shared successfully!")
                                time.sleep(0.5)
                                st.rerun()

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    # Auto-save session
    save_session_to_db()
    
    st.title(f"👤 User Dashboard")
    st.subheader(f"Welcome, {st.session_state.user}")
    
    with st.sidebar:
        st.image(f"data:image/png;base64,{logo_b64}", width=60) if logo_b64 else None
        st.markdown("### User Menu")
        
        if st.button("🔄 Refresh Songs", key="user_refresh"):
            st.rerun()
            
        if st.button("🚪 Logout", key="user_logout"):
            st.session_state.clear()
            st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
    
    st.header("🎵 Available Songs")
    
    uploaded_songs = get_uploaded_songs(show_unshared=False)
    shared_links = load_shared_links()
    
    if not uploaded_songs:
        st.warning("No shared songs available yet.")
        st.info("The admin needs to share songs before they appear here.")
    else:
        st.success(f"You have access to {len(uploaded_songs)} song(s)")
        
        cols = st.columns(2)
        for idx, song in enumerate(uploaded_songs):
            with cols[idx % 2]:
                with st.container():
                    st.markdown(f"""
                    <div style="
                        background: rgba(30, 41, 59, 0.5);
                        border-radius: 10px;
                        padding: 15px;
                        margin: 10px 0;
                        border-left: 4px solid #10b981;
                    ">
                        <h4>🎵 {song}</h4>
                        <p style="color: #94a3b8; font-size: 0.9em;">
                            Shared by: {shared_links.get(song, {}).get('shared_by', 'Admin')}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("▶ Play Now", key=f"user_play_{song}_{idx}", use_container_width=True):
                        st.session_state.selected_song = song
                        st.session_state.page = "Song Player"
                        save_session_to_db()
                        st.rerun()

# =============== SONG PLAYER ===============
elif st.session_state.page == "Song Player":
    # Auto-save session
    save_session_to_db()
    
    selected_song = st.session_state.get("selected_song")
    
    if not selected_song:
        st.error("No song selected!")
        if st.button("← Go Back"):
            if st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            elif st.session_state.role == "user":
                st.session_state.page = "User Dashboard"
            else:
                st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
        st.stop()
    
    # Check access
    shared_links = load_shared_links()
    is_shared = selected_song in shared_links
    is_admin = st.session_state.role == "admin"
    is_guest = st.session_state.role == "guest"
    
    if not (is_shared or is_admin or is_guest):
        st.error("❌ Access denied! This song is not shared.")
        if st.button("← Go Back"):
            st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
        st.stop()
    
    # Find files
    original_path = os.path.join(songs_dir, f"{selected_song}_original.mp3")
    accompaniment_path = os.path.join(songs_dir, f"{selected_song}_accompaniment.mp3")
    
    # Find lyrics image
    lyrics_path = ""
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        test_path = os.path.join(lyrics_dir, f"{selected_song}_lyrics_bg{ext}")
        if os.path.exists(test_path):
            lyrics_path = test_path
            break
    
    if not os.path.exists(original_path):
        st.error(f"Original audio file not found for: {selected_song}")
        st.stop()
    
    if not os.path.exists(accompaniment_path):
        st.error(f"Accompaniment file not found for: {selected_song}")
        st.stop()
    
    # Convert to base64
    original_b64 = file_to_base64(original_path)
    accompaniment_b64 = file_to_base64(accompaniment_path)
    lyrics_b64 = file_to_base64(lyrics_path) if lyrics_path else ""
    
    # Player HTML
    player_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🎤 {selected_song} - Karaoke</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background: #000;
                overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            
            .container {{
                width: 100vw;
                height: 100vh;
                position: relative;
            }}
            
            .background-image {{
                width: 100%;
                height: 100%;
                object-fit: contain;
                object-position: center;
            }}
            
            .overlay {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.3);
            }}
            
            .logo {{
                position: absolute;
                top: 20px;
                left: 20px;
                width: 50px;
                height: 50px;
                border-radius: 50%;
                border: 2px solid rgba(255, 255, 255, 0.3);
                z-index: 10;
            }}
            
            .song-title {{
                position: absolute;
                top: 20px;
                right: 20px;
                background: rgba(0, 0, 0, 0.7);
                color: white;
                padding: 10px 20px;
                border-radius: 25px;
                font-size: 16px;
                font-weight: 600;
                z-index: 10;
            }}
            
            .controls {{
                position: absolute;
                bottom: 40px;
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                gap: 15px;
                z-index: 10;
            }}
            
            .control-btn {{
                background: linear-gradient(135deg, #6366f1, #8b5cf6);
                border: none;
                color: white;
                padding: 14px 28px;
                border-radius: 30px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
                min-width: 160px;
                text-align: center;
            }}
            
            .control-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
            }}
            
            .control-btn:active {{
                transform: translateY(0);
            }}
            
            .control-btn.stop {{
                background: linear-gradient(135deg, #ef4444, #dc2626);
            }}
            
            .status {{
                position: absolute;
                bottom: 100px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 10px 20px;
                border-radius: 20px;
                font-size: 14px;
                z-index: 10;
                white-space: nowrap;
            }}
            
            .lyrics {{
                position: absolute;
                bottom: 150px;
                width: 100%;
                text-align: center;
                color: white;
                font-size: 2.5vw;
                font-weight: bold;
                text-shadow: 2px 2px 10px rgba(0,0,0,0.8);
                padding: 0 20px;
                z-index: 5;
            }}
            
            .hidden {{
                display: none;
            }}
            
            @media (max-width: 768px) {{
                .controls {{
                    flex-direction: column;
                    gap: 10px;
                }}
                
                .control-btn {{
                    min-width: 200px;
                }}
                
                .lyrics {{
                    font-size: 4vw;
                    bottom: 200px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <img id="bgImage" class="background-image" src="data:image/jpeg;base64,{lyrics_b64}" 
                 onerror="this.style.display='none'" alt="Lyrics Background">
            <div class="overlay"></div>
            
            {f'<img class="logo" src="data:image/png;base64,{logo_b64}" alt="Logo">' if logo_b64 else ''}
            
            <div class="song-title">🎵 {selected_song}</div>
            
            <div class="status" id="status">Ready to sing! 🎤</div>
            
            <div class="controls">
                <button id="playBtn" class="control-btn">▶ Play Original</button>
                <button id="recordBtn" class="control-btn">🎙 Start Recording</button>
                <button id="stopBtn" class="control-btn stop hidden">⏹ Stop Recording</button>
            </div>
        </div>
        
        <!-- Hidden audio elements -->
        <audio id="originalAudio" src="data:audio/mp3;base64,{original_b64}"></audio>
        <audio id="accompanimentAudio" src="data:audio/mp3;base64,{accompaniment_b64}"></audio>
        
        <script>
            // Elements
            const playBtn = document.getElementById('playBtn');
            const recordBtn = document.getElementById('recordBtn');
            const stopBtn = document.getElementById('stopBtn');
            const status = document.getElementById('status');
            const originalAudio = document.getElementById('originalAudio');
            const accompanimentAudio = document.getElementById('accompanimentAudio');
            
            let isRecording = false;
            let mediaRecorder;
            let recordedChunks = [];
            
            // Play original audio
            playBtn.addEventListener('click', async () => {{
                try {{
                    if (originalAudio.paused) {{
                        originalAudio.currentTime = 0;
                        await originalAudio.play();
                        playBtn.textContent = '⏸ Pause Original';
                        status.textContent = 'Playing original...';
                    }} else {{
                        originalAudio.pause();
                        playBtn.textContent = '▶ Play Original';
                        status.textContent = 'Paused';
                    }}
                }} catch (error) {{
                    status.textContent = 'Click Play again to start';
                    originalAudio.play();
                }}
            }});
            
            // Start recording
            recordBtn.addEventListener('click', async () => {{
                if (isRecording) return;
                
                try {{
                    isRecording = true;
                    status.textContent = 'Starting recording...';
                    
                    // Get microphone access
                    const micStream = await navigator.mediaDevices.getUserMedia({{
                        audio: {{
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true
                        }}
                    }});
                    
                    // Start both audios
                    originalAudio.currentTime = 0;
                    accompanimentAudio.currentTime = 0;
                    
                    await Promise.all([
                        originalAudio.play(),
                        accompanimentAudio.play()
                    ]);
                    
                    // Combine microphone with accompaniment
                    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    const destination = audioContext.createMediaStreamDestination();
                    
                    const micSource = audioContext.createMediaStreamSource(micStream);
                    const accSource = audioContext.createMediaStreamSource(accompanimentAudio.captureStream());
                    
                    micSource.connect(destination);
                    accSource.connect(destination);
                    
                    // Create media recorder
                    recordedChunks = [];
                    mediaRecorder = new MediaRecorder(destination.stream);
                    
                    mediaRecorder.ondataavailable = (event) => {{
                        if (event.data.size > 0) {{
                            recordedChunks.push(event.data);
                        }}
                    }};
                    
                    mediaRecorder.onstop = () => {{
                        const blob = new Blob(recordedChunks, {{ type: 'audio/webm' }});
                        const url = URL.createObjectURL(blob);
                        
                        // Create download link
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `karaoke_{selected_song}_${{Date.now()}}.webm`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        
                        status.textContent = 'Recording saved! ✅';
                    }};
                    
                    mediaRecorder.start();
                    
                    // Update UI
                    recordBtn.classList.add('hidden');
                    stopBtn.classList.remove('hidden');
                    status.textContent = 'Recording... 🎤';
                    playBtn.disabled = true;
                    
                }} catch (error) {{
                    console.error('Recording error:', error);
                    status.textContent = 'Error: ' + error.message;
                    isRecording = false;
                }}
            }});
            
            // Stop recording
            stopBtn.addEventListener('click', () => {{
                if (!isRecording) return;
                
                isRecording = false;
                
                // Stop recording
                if (mediaRecorder && mediaRecorder.state !== 'inactive') {{
                    mediaRecorder.stop();
                }}
                
                // Stop audio
                originalAudio.pause();
                accompanimentAudio.pause();
                
                // Update UI
                stopBtn.classList.add('hidden');
                recordBtn.classList.remove('hidden');
                playBtn.disabled = false;
                playBtn.textContent = '▶ Play Original';
                status.textContent = 'Processing...';
            }});
            
            // Handle page visibility
            document.addEventListener('visibilitychange', () => {{
                if (document.hidden && isRecording) {{
                    stopBtn.click();
                }}
            }});
            
            // Initialize
            window.addEventListener('load', () => {{
                status.textContent = 'Ready to sing! 🎤';
            }});
        </script>
    </body>
    </html>
    """
    
    # Back button
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("← Back", key="back_player"):
            if st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            elif st.session_state.role == "user":
                st.session_state.page = "User Dashboard"
            else:
                st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
    
    # Display player
    html(player_html, height=800, scrolling=False)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    save_session_to_db()
    st.rerun()
