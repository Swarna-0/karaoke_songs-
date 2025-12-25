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
import tempfile
import gzip
import asyncio

st.set_page_config(page_title="𝄞 sing-along", layout="wide", initial_sidebar_state="collapsed")

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
cache_dir = os.path.join(base_dir, ".cache")

# Create directories
os.makedirs(songs_dir, exist_ok=True)
os.makedirs(lyrics_dir, exist_ok=True)
os.makedirs(logo_dir, exist_ok=True)
os.makedirs(shared_links_dir, exist_ok=True)
os.makedirs(cache_dir, exist_ok=True)

# =============== OPTIMIZED CACHING ===============
@st.cache_resource(ttl=3600)
def get_cached_base64(path):
    """Cache base64 conversions to avoid repeated encoding"""
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

@st.cache_data(ttl=300)
def load_metadata_cached():
    """Cached metadata loading"""
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
    """Cached shared links loading"""
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
    except:
        pass

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
            if user and user != 'None':
                st.session_state.user = user
            if role and role != 'None':
                st.session_state.role = role
            if page and page != 'None':
                st.session_state.page = page
            if selected_song and selected_song != 'None':
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

# =============== OPTIMIZED HELPER FUNCTIONS ===============
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_metadata():
    """Load metadata from both file and database"""
    file_metadata = load_metadata_cached()
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
    
    # Clear cache
    load_metadata_cached.clear()

def load_shared_links():
    """Load shared links from both file and database"""
    file_links = load_shared_links_cached()
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

def get_uploaded_songs(show_unshared=False):
    """Get list of uploaded songs with caching"""
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
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "page" not in st.session_state:
    st.session_state.page = "Login"
if "selected_song" not in st.session_state:
    st.session_state.selected_song = None
if "player_ready" not in st.session_state:
    st.session_state.player_ready = False

# Load persistent session data
load_session_from_db()

metadata = load_metadata()

# Logo - cached
logo_path = os.path.join(logo_dir, "branks3_logo.png")
logo_b64 = get_cached_base64(logo_path) if os.path.exists(logo_path) else ""

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

# =============== OPTIMIZED LOGIN PAGE ===============
if st.session_state.page == "Login":
    save_session_to_db()
    
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    header {visibility:hidden;}
    .stApp {background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%);}
    .main .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    .login-container {background: rgba(5,10,25,0.9); border-radius: 20px; padding: 2.5rem; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 20px 40px rgba(0,0,0,0.3);}
    .login-header {text-align: center; margin-bottom: 2rem;}
    .login-header img {width: 70px; height: 70px; border-radius: 50%; border: 3px solid rgba(255,255,255,0.2); margin-bottom: 1rem;}
    .login-title {font-size: 2rem; font-weight: 800; background: linear-gradient(45deg, #4facfe, #00f2fe); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem;}
    .login-subtitle {color: #a0b3d1; font-size: 0.9rem; margin-bottom: 2rem;}
    .stTextInput input {background: rgba(5,10,25,0.7) !important; border-radius: 12px !important; color: white !important; border: 1px solid rgba(255,255,255,0.2) !important; padding: 14px 16px !important;}
    .stButton button {width: 100%; background: linear-gradient(45deg, #1a2980, #26d0ce); border-radius: 12px; height: 50px; font-weight: 600; font-size: 1rem; border: none; transition: all 0.3s;}
    .stButton button:hover {transform: translateY(-2px); box-shadow: 0 10px 20px rgba(38,208,206,0.3);}
    .credentials-box {background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px; margin-top: 20px; border-left: 4px solid #4facfe;}
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="login-header">
            <img src="data:image/png;base64,{logo_b64}">
            <div class="login-title">𝄞 Karaoke Reels</div>
            <div class="login-subtitle">Professional Karaoke Recording Studio</div>
        </div>
        """, unsafe_allow_html=True)
        
        username = st.text_input("👤 Username", placeholder="Enter admin/user1/user2", key="login_username")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter password", key="login_password")
        
        if st.button("🚀 Login", type="primary", key="login_button"):
            if not username or not password:
                st.error("Please enter both username and password")
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
                    st.error("Invalid username or password")
        
        st.markdown("""
        <div class="credentials-box">
        <h4>📋 Demo Credentials:</h4>
        <p>• Admin: admin / admin123</p>
        <p>• User1: user1 / user123</p>
        <p>• User2: user2 / user123</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# =============== ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    save_session_to_db()
    
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);}
    .sidebar-content {padding: 20px;}
    .main-header {background: linear-gradient(90deg, #1e3a8a 0%, #1e40af 100%); padding: 20px; border-radius: 15px; color: white; margin-bottom: 30px;}
    .card {background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; border: 1px solid rgba(255,255,255,0.1); transition: transform 0.3s;}
    .card:hover {transform: translateY(-5px); border-color: #3b82f6;}
    .stButton button {border-radius: 10px; font-weight: 500;}
    </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown(f"### 👑 {st.session_state.user}")
        st.markdown("---")
        page_option = st.radio(
            "📊 Dashboard",
            ["📤 Upload Songs", "🎵 Songs List", "🔗 Share Links", "📊 Statistics"],
            key="admin_nav"
        )
        st.markdown("---")
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
    
    st.markdown('<div class="main-header"><h1>👑 Admin Dashboard</h1><p>Manage all karaoke songs and user access</p></div>', unsafe_allow_html=True)
    
    if page_option == "📤 Upload Songs":
        st.subheader("📤 Upload New Song")
        
        col1, col2 = st.columns([3, 2])
        with col1:
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                
                col1a, col2a, col3a = st.columns(3)
                with col1a:
                    uploaded_original = st.file_uploader("Original Track", type=["mp3"], 
                                                        help="Main song with vocals (_original.mp3)", key="original_upload")
                with col2a:
                    uploaded_accompaniment = st.file_uploader("Accompaniment", type=["mp3"], 
                                                            help="Karaoke version (_accompaniment.mp3)", key="acc_upload")
                with col3a:
                    uploaded_lyrics_image = st.file_uploader("Lyrics Image", type=["jpg", "jpeg", "png"], 
                                                           help="Lyrics background (_lyrics_bg.jpg)", key="lyrics_upload")
                
                if uploaded_original and uploaded_accompaniment and uploaded_lyrics_image:
                    song_name = uploaded_original.name.replace("_original.mp3", "").strip()
                    if not song_name:
                        song_name = os.path.splitext(uploaded_original.name)[0]
                    
                    # Show preview
                    st.info(f"🎵 Song Name: **{song_name}**")
                    
                    if st.button("✅ Upload Song", type="primary", use_container_width=True):
                        original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
                        acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
                        lyrics_ext = os.path.splitext(uploaded_lyrics_image.name)[1]
                        lyrics_path = os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{lyrics_ext}")
                        
                        with st.spinner("Uploading files..."):
                            with open(original_path, "wb") as f:
                                f.write(uploaded_original.getbuffer())
                            with open(acc_path, "wb") as f:
                                f.write(uploaded_accompaniment.getbuffer())
                            with open(lyrics_path, "wb") as f:
                                f.write(uploaded_lyrics_image.getbuffer())
                        
                        metadata[song_name] = {"uploaded_by": st.session_state.user, "timestamp": str(time.time())}
                        save_metadata(metadata)
                        st.success(f"✅ **{song_name}** uploaded successfully!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="card">
            <h4>📝 Instructions:</h4>
            <p>1. <strong>Original Track:</strong> Song with vocals</p>
            <p>2. <strong>Accompaniment:</strong> Karaoke/instrumental version</p>
            <p>3. <strong>Lyrics Image:</strong> Background image with lyrics</p>
            <p>All files should follow naming pattern:<br>
            <code>songname_original.mp3</code><br>
            <code>songname_accompaniment.mp3</code><br>
            <code>songname_lyrics_bg.jpg</code>
            </p>
            </div>
            """, unsafe_allow_html=True)
    
    elif page_option == "🎵 Songs List":
        st.subheader("📋 All Songs")
        
        uploaded_songs = get_uploaded_songs(show_unshared=True)
        if not uploaded_songs:
            st.warning("No songs uploaded yet. Upload your first song!")
        else:
            search_term = st.text_input("🔍 Search songs", placeholder="Type to filter...")
            
            filtered_songs = [s for s in uploaded_songs if search_term.lower() in s.lower()] if search_term else uploaded_songs
            
            for idx, song in enumerate(filtered_songs):
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    with col1:
                        uploader = metadata.get(song, {}).get('uploaded_by', 'Unknown')
                        st.markdown(f"**{song}**<br><small>Uploaded by: {uploader}</small>", unsafe_allow_html=True)
                    with col2:
                        if st.button("▶ Play", key=f"play_{song}_{idx}", use_container_width=True):
                            st.session_state.selected_song = song
                            st.session_state.page = "Song Player"
                            save_session_to_db()
                            st.rerun()
                    with col3:
                        safe_s = quote(song)
                        share_url = f"{APP_URL}?song={safe_s}"
                        st.link_button("🔗 Share", share_url)
                    with col4:
                        if st.button("🗑️ Delete", key=f"del_{song}_{idx}", use_container_width=True):
                            # Delete song files
                            original_path = os.path.join(songs_dir, f"{song}_original.mp3")
                            acc_path = os.path.join(songs_dir, f"{song}_accompaniment.mp3")
                            for path in [original_path, acc_path]:
                                if os.path.exists(path):
                                    os.remove(path)
                            # Delete from metadata
                            if song in metadata:
                                del metadata[song]
                                save_metadata(metadata)
                            st.success(f"Deleted {song}")
                            time.sleep(1)
                            st.rerun()
                    st.divider()
    
    elif page_option == "🔗 Share Links":
        st.subheader("🔗 Share Management")
        
        all_songs = get_uploaded_songs(show_unshared=True)
        shared_links_data = load_shared_links()
        
        col1, col2 = st.columns([3, 2])
        with col1:
            for song in all_songs:
                is_shared = song in shared_links_data
                safe_song = quote(song)
                share_url = f"{APP_URL}?song={safe_song}"
                
                with st.container():
                    st.markdown(f"**{song}**")
                    col_a, col_b, col_c = st.columns([1, 1, 2])
                    with col_a:
                        status = "✅ Shared" if is_shared else "❌ Private"
                        st.write(status)
                    with col_b:
                        if is_shared:
                            if st.button("🚫 Unshare", key=f"unshare_{song}"):
                                delete_shared_link(song)
                                st.success(f"Unshared {song}")
                                time.sleep(0.5)
                                st.rerun()
                        else:
                            if st.button("🔗 Share", key=f"share_{song}"):
                                save_shared_link(song, {"shared_by": st.session_state.user, "active": True})
                                st.success(f"Shared {song}")
                                time.sleep(0.5)
                                st.rerun()
                    with col_c:
                        if is_shared:
                            st.code(share_url, language=None)
                    st.divider()
        
        with col2:
            st.markdown("""
            <div class="card">
            <h4>🔗 Quick Share Guide:</h4>
            <p>1. <strong>Shared:</strong> Users can access via direct link</p>
            <p>2. <strong>Private:</strong> Only visible to admin</p>
            <p>3. <strong>Direct Link:</strong> Share URL with users</p>
            <p>4. <strong>Unshare:</strong> Make song private again</p>
            <hr>
            <p><strong>Total Songs:</strong> {}</p>
            <p><strong>Shared Songs:</strong> {}</p>
            </div>
            """.format(len(all_songs), len(shared_links_data)), unsafe_allow_html=True)
    
    elif page_option == "📊 Statistics":
        st.subheader("📊 Usage Statistics")
        
        uploaded_songs = get_uploaded_songs(show_unshared=True)
        shared_songs = load_shared_links()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Songs", len(uploaded_songs))
        with col2:
            st.metric("Shared Songs", len(shared_songs))
        with col3:
            st.metric("Private Songs", len(uploaded_songs) - len(shared_songs))
        
        # Recent activity
        st.subheader("Recent Activity")
        try:
            conn = sqlite3.connect(session_db_path)
            c = conn.cursor()
            c.execute('SELECT song_name, uploaded_by FROM metadata ORDER BY timestamp DESC LIMIT 10')
            recent = c.fetchall()
            conn.close()
            
            for song, uploader in recent:
                st.write(f"• **{song}** - uploaded by {uploader}")
        except:
            st.info("No recent activity")

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    save_session_to_db()
    
    st.markdown("""
    <style>
    .user-header {background: linear-gradient(90deg, #059669 0%, #10b981 100%); padding: 20px; border-radius: 15px; color: white; margin-bottom: 30px;}
    .song-card {background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; margin-bottom: 15px; border: 1px solid rgba(255,255,255,0.1);}
    .song-card:hover {border-color: #10b981; transform: translateY(-2px); transition: all 0.3s;}
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f'<div class="user-header"><h1>👤 Welcome, {st.session_state.user}</h1><p>Browse and sing your favorite karaoke songs</p></div>', unsafe_allow_html=True)
    
    uploaded_songs = get_uploaded_songs(show_unshared=False)
    
    if not uploaded_songs:
        st.info("""
        ## 🎤 No Songs Available Yet
        
        There are no shared songs in the library right now.
        
        **What to do next:**
        1. Contact the admin to share songs
        2. Wait for songs to be uploaded
        3. Check back later
        
        The admin needs to upload and share songs before you can start singing!
        """)
    else:
        st.subheader(f"🎵 Available Songs ({len(uploaded_songs)})")
        
        # Grid layout for songs
        cols = st.columns(2)
        for idx, song in enumerate(uploaded_songs):
            with cols[idx % 2]:
                with st.container():
                    st.markdown(f'<div class="song-card">', unsafe_allow_html=True)
                    st.markdown(f"### {song}")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("🎵 Play Now", key=f"user_play_{song}_{idx}", use_container_width=True):
                            st.session_state.selected_song = song
                            st.session_state.page = "Song Player"
                            save_session_to_db()
                            st.rerun()
                    with col_b:
                        safe_s = quote(song)
                        share_url = f"{APP_URL}?song={safe_s}"
                        st.link_button("🔗 Get Link", share_url)
                    st.markdown('</div>', unsafe_allow_html=True)
    
    # Logout button
    if st.button("🚪 Logout", type="secondary", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "Login"
        save_session_to_db()
        st.rerun()

# =============== OPTIMIZED SONG PLAYER ===============
elif st.session_state.page == "Song Player" and st.session_state.get("selected_song"):
    save_session_to_db()
    
    selected_song = st.session_state.get("selected_song", None)
    
    # Pre-load all media files in background
    @st.cache_data(ttl=600)
    def preload_song_media(song_name):
        """Preload and cache song media"""
        original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
        accompaniment_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
        
        lyrics_path = ""
        for ext in [".jpg", ".jpeg", ".png"]:
            p = os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{ext}")
            if os.path.exists(p):
                lyrics_path = p
                break
        
        original_b64 = get_cached_base64(original_path) if os.path.exists(original_path) else ""
        accompaniment_b64 = get_cached_base64(accompaniment_path) if os.path.exists(accompaniment_path) else ""
        lyrics_b64 = get_cached_base64(lyrics_path) if lyrics_path else ""
        
        return {
            "original_b64": original_b64,
            "accompaniment_b64": accompaniment_b64,
            "lyrics_b64": lyrics_b64,
            "song_name": song_name
        }
    
    # Load media
    media_data = preload_song_media(selected_song)
    
    # Check access
    shared_links = load_shared_links()
    is_shared = selected_song in shared_links
    is_admin = st.session_state.role == "admin"
    is_guest = st.session_state.role == "guest"
    
    if not (is_shared or is_admin or is_guest):
        st.error("❌ Access Denied")
        st.info("This song is not shared. Contact admin for access.")
        if st.button("← Go Back"):
            if st.session_state.role == "user":
                st.session_state.page = "User Dashboard"
            elif st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            else:
                st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
        st.stop()
    
    # Player UI
    st.markdown("""
    <style>
    .player-header {background: linear-gradient(90deg, #7c3aed 0%, #8b5cf6 100%); padding: 15px 20px; border-radius: 10px; color: white; margin-bottom: 20px;}
    .back-button {background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; padding: 8px 20px; border-radius: 20px; text-decoration: none; font-size: 14px; transition: all 0.3s;}
    .back-button:hover {background: rgba(255,255,255,0.2); transform: translateY(-2px);}
    #player-container {border-radius: 20px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.3);}
    </style>
    """, unsafe_allow_html=True)
    
    # Header with back button
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(f'<div class="player-header"><h2>🎤 {selected_song}</h2><p>Karaoke Player - Start recording your performance!</p></div>', unsafe_allow_html=True)
    with col2:
        if st.button("← Back", key="back_player", use_container_width=True):
            if st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            elif st.session_state.role == "user":
                st.session_state.page = "User Dashboard"
            else:
                st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
    
    # Optimized Player HTML
    player_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{selected_song} - Karaoke Player</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #0f172a; 
                color: white;
                overflow: hidden;
            }}
            
            .player-wrapper {{
                width: 100%;
                height: 85vh;
                position: relative;
                border-radius: 20px;
                overflow: hidden;
                background: #1e293b;
            }}
            
            #lyrics-image {{
                width: 100%;
                height: 100%;
                object-fit: contain;
                object-position: center;
                background: #000;
            }}
            
            .controls {{
                position: absolute;
                bottom: 40px;
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                gap: 15px;
                z-index: 100;
                background: rgba(0,0,0,0.7);
                padding: 20px 30px;
                border-radius: 50px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.1);
            }}
            
            .control-btn {{
                background: linear-gradient(135deg, #7c3aed, #8b5cf6);
                border: none;
                color: white;
                padding: 12px 25px;
                border-radius: 25px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 8px;
                transition: all 0.3s;
                min-width: 160px;
                justify-content: center;
            }}
            
            .control-btn:hover {{
                transform: translateY(-3px);
                box-shadow: 0 10px 20px rgba(124, 58, 237, 0.4);
            }}
            
            .control-btn:active {{
                transform: translateY(-1px);
            }}
            
            .control-btn.recording {{
                background: linear-gradient(135deg, #dc2626, #ef4444);
                animation: pulse 1.5s infinite;
            }}
            
            @keyframes pulse {{
                0% {{ box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7); }}
                70% {{ box-shadow: 0 0 0 15px rgba(220, 38, 38, 0); }}
                100% {{ box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }}
            }}
            
            .status-bar {{
                position: absolute;
                top: 20px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0,0,0,0.7);
                padding: 10px 25px;
                border-radius: 20px;
                font-size: 14px;
                backdrop-filter: blur(10px);
                z-index: 100;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .logo {{
                position: absolute;
                top: 20px;
                left: 20px;
                width: 50px;
                height: 50px;
                border-radius: 10px;
                z-index: 100;
                opacity: 0.8;
            }}
            
            .final-output {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: rgba(0,0,0,0.95);
                display: none;
                justify-content: center;
                align-items: center;
                z-index: 1000;
                flex-direction: column;
                gap: 30px;
            }}
            
            .final-controls {{
                display: flex;
                gap: 20px;
                margin-top: 30px;
            }}
            
            .download-btn {{
                background: linear-gradient(135deg, #059669, #10b981);
            }}
            
            .new-recording-btn {{
                background: linear-gradient(135deg, #1e40af, #3b82f6);
            }}
            
            canvas {{ display: none; }}
        </style>
    </head>
    <body>
        <div class="player-wrapper">
            <img id="lyrics-image" src="data:image/jpeg;base64,{media_data['lyrics_b64']}" alt="Lyrics Background">
            <img class="logo" src="data:image/png;base64,{logo_b64}" alt="Logo">
            
            <div class="status-bar" id="statusBar">
                <span id="statusText">Ready to sing 🎤</span>
            </div>
            
            <div class="controls">
                <button class="control-btn" id="playBtn">
                    <span>▶</span> Play Original
                </button>
                <button class="control-btn" id="recordBtn">
                    <span>🎙️</span> Start Recording
                </button>
                <button class="control-btn recording" id="stopBtn" style="display: none;">
                    <span>⏹️</span> Stop Recording
                </button>
            </div>
        </div>
        
        <div class="final-output" id="finalOutput">
            <h2 style="font-size: 2rem; margin-bottom: 10px;">Recording Complete! 🎉</h2>
            <p style="color: #cbd5e1; margin-bottom: 30px;">Your karaoke performance is ready</p>
            <div class="final-controls">
                <button class="control-btn" id="playRecordingBtn">
                    <span>▶</span> Play Recording
                </button>
                <a id="downloadLink" download="karaoke_recording.webm">
                    <button class="control-btn download-btn">
                        <span>⬇️</span> Download Video
                    </button>
                </a>
                <button class="control-btn new-recording-btn" id="newRecordingBtn">
                    <span>🔄</span> New Recording
                </button>
            </div>
        </div>
        
        <canvas id="recordingCanvas" width="1920" height="1080"></canvas>
        
        <audio id="originalAudio" preload="auto" src="data:audio/mp3;base64,{media_data['original_b64']}"></audio>
        <audio id="accompanimentAudio" preload="auto" src="data:audio/mp3;base64,{media_data['accompaniment_b64']}"></audio>
        
        <script>
            // Global variables
            let mediaRecorder;
            let recordedChunks = [];
            let recordingStream;
            let isRecording = false;
            let audioContext;
            let micSource;
            let accSource;
            let canvasContext;
            
            // Elements
            const playBtn = document.getElementById('playBtn');
            const recordBtn = document.getElementById('recordBtn');
            const stopBtn = document.getElementById('stopBtn');
            const statusText = document.getElementById('statusText');
            const originalAudio = document.getElementById('originalAudio');
            const accompanimentAudio = document.getElementById('accompanimentAudio');
            const finalOutput = document.getElementById('finalOutput');
            const downloadLink = document.getElementById('downloadLink');
            const playRecordingBtn = document.getElementById('playRecordingBtn');
            const newRecordingBtn = document.getElementById('newRecordingBtn');
            const canvas = document.getElementById('recordingCanvas');
            const lyricsImage = document.getElementById('lyrics-image');
            
            // Initialize canvas context
            canvasContext = canvas.getContext('2d');
            
            // Play original audio
            playBtn.addEventListener('click', async () => {{
                try {{
                    if (originalAudio.paused) {{
                        originalAudio.currentTime = 0;
                        await originalAudio.play();
                        playBtn.innerHTML = '<span>⏸️</span> Pause';
                        statusText.textContent = 'Playing original track...';
                    }} else {{
                        originalAudio.pause();
                        playBtn.innerHTML = '<span>▶</span> Play Original';
                        statusText.textContent = 'Paused';
                    }}
                }} catch (error) {{
                    console.error('Error playing audio:', error);
                    statusText.textContent = 'Click to play again';
                }}
            }});
            
            // Draw frame to canvas
            function drawFrame() {{
                if (!isRecording) return;
                
                canvasContext.clearRect(0, 0, canvas.width, canvas.height);
                canvasContext.drawImage(lyricsImage, 0, 0, canvas.width, canvas.height);
                
                requestAnimationFrame(drawFrame);
            }}
            
            // Start recording
            recordBtn.addEventListener('click', async () => {{
                try {{
                    isRecording = true;
                    
                    // Get microphone access
                    const micStream = await navigator.mediaDevices.getUserMedia({{
                        audio: {{
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true
                        }}
                    }});
                    
                    // Setup audio context
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    
                    // Create microphone source
                    micSource = audioContext.createMediaStreamSource(micStream);
                    
                    // Create destination for mixing
                    const destination = audioContext.createMediaStreamDestination();
                    
                    // Connect microphone
                    micSource.connect(destination);
                    
                    // Start drawing to canvas
                    drawFrame();
                    
                    // Capture canvas stream
                    const canvasStream = canvas.captureStream(30);
                    
                    // Combine audio and video streams
                    recordingStream = new MediaStream([
                        ...canvasStream.getVideoTracks(),
                        ...destination.stream.getAudioTracks()
                    ]);
                    
                    // Create media recorder
                    mediaRecorder = new MediaRecorder(recordingStream, {{
                        mimeType: 'video/webm;codecs=vp9,opus'
                    }});
                    
                    recordedChunks = [];
                    
                    mediaRecorder.ondataavailable = (event) => {{
                        if (event.data.size > 0) {{
                            recordedChunks.push(event.data);
                        }}
                    }};
                    
                    mediaRecorder.onstop = () => {{
                        const blob = new Blob(recordedChunks, {{ type: 'video/webm' }});
                        const url = URL.createObjectURL(blob);
                        
                        downloadLink.href = url;
                        downloadLink.download = `karaoke_${{selected_song}}_${{new Date().getTime()}}.webm`;
                        
                        finalOutput.style.display = 'flex';
                        
                        // Setup play recording button
                        playRecordingBtn.onclick = () => {{
                            const audio = new Audio(url);
                            audio.play();
                        }};
                    }};
                    
                    // Start recording
                    mediaRecorder.start(100);
                    
                    // Play accompaniment
                    accompanimentAudio.currentTime = 0;
                    await accompanimentAudio.play();
                    
                    // Update UI
                    recordBtn.style.display = 'none';
                    stopBtn.style.display = 'flex';
                    statusText.textContent = 'Recording... 🎤';
                    
                }} catch (error) {{
                    console.error('Recording error:', error);
                    statusText.textContent = 'Recording failed. Check microphone permissions.';
                    isRecording = false;
                }}
            }});
            
            // Stop recording
            stopBtn.addEventListener('click', () => {{
                if (mediaRecorder && isRecording) {{
                    mediaRecorder.stop();
                    isRecording = false;
                    
                    // Stop all tracks
                    if (recordingStream) {{
                        recordingStream.getTracks().forEach(track => track.stop());
                    }}
                    
                    // Stop audio
                    originalAudio.pause();
                    accompanimentAudio.pause();
                    
                    // Update UI
                    recordBtn.style.display = 'flex';
                    stopBtn.style.display = 'none';
                    statusText.textContent = 'Processing recording...';
                    
                    setTimeout(() => {{
                        statusText.textContent = 'Recording complete!';
                    }}, 1000);
                }}
            }});
            
            // New recording
            newRecordingBtn.addEventListener('click', () => {{
                finalOutput.style.display = 'none';
                recordBtn.style.display = 'flex';
                stopBtn.style.display = 'none';
                statusText.textContent = 'Ready to sing 🎤';
                originalAudio.pause();
                accompanimentAudio.pause();
                originalAudio.currentTime = 0;
                accompanimentAudio.currentTime = 0;
                playBtn.innerHTML = '<span>▶</span> Play Original';
            }});
            
            // Auto-resume audio context on user interaction
            document.addEventListener('click', async () => {{
                if (audioContext && audioContext.state === 'suspended') {{
                    await audioContext.resume();
                }}
            }});
            
            // Preload audio for faster playback
            window.addEventListener('load', () => {{
                originalAudio.load();
                accompanimentAudio.load();
            }});
        </script>
    </body>
    </html>
    """
    
    # Display player
    html(player_html, height=900, scrolling=False)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    save_session_to_db()
    st.rerun()

# =============== DEBUG PANEL (Admin only) ===============
if st.session_state.get("role") == "admin":
    with st.sidebar:
        if st.checkbox("🛠️ Debug Panel", key="debug_toggle"):
            st.write("### Debug Information")
            st.write(f"**Session ID:** {st.session_state.get('session_id', 'N/A')}")
            st.write(f"**Current Page:** {st.session_state.get('page')}")
            st.write(f"**User Role:** {st.session_state.get('role')}")
            st.write(f"**Selected Song:** {st.session_state.get('selected_song')}")
            
            if st.button("🔄 Clear Cache", key="clear_cache"):
                st.cache_data.clear()
                st.cache_resource.clear()
                st.success("Cache cleared!")
            
            if st.button("⚠️ Reset Session", key="reset_session"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.page = "Login"
                save_session_to_db()
                st.rerun()
