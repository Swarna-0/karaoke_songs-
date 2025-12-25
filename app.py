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
import uuid

st.set_page_config(page_title="𝄞 sing-along", layout="wide", initial_sidebar_state="collapsed")

# --------- CONFIG: set your deployed app URL here ----------
APP_URL = "https://karaoke-project-production.up.railway.app/"  # Change to your Railway URL

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
        print(f"Database init error: {e}")

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
        print(f"Save session error: {e}")

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
        print(f"Load session error: {e}")

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
        print(f"Save shared link error: {e}")

def delete_shared_link_from_db(song_name):
    """Delete shared link from database"""
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('DELETE FROM shared_links WHERE song_name = ?', (song_name,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Delete shared link error: {e}")

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
        print(f"Load shared links error: {e}")
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
        print(f"Save metadata error: {e}")

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
        print(f"Load metadata error: {e}")
    return metadata

# Initialize database
init_session_db()

# =============== HELPER FUNCTIONS ===============
def file_to_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def get_file_url(file_path):
    """Get a direct URL for the file (for Railway deployment)"""
    if not os.path.exists(file_path):
        return ""
    
    # For Railway, we need to serve files differently
    # We'll create a unique route for each file
    file_name = os.path.basename(file_path)
    # We'll use a unique identifier to avoid caching issues
    unique_id = str(hash(file_path + str(os.path.getmtime(file_path))))[:8]
    return f"/file/{unique_id}/{file_name}"

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
if "login_attempts" not in st.session_state:
    st.session_state.login_attempts = 0

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
        st.rerun()

# =============== RESPONSIVE LOGIN PAGE ===============
if st.session_state.page == "Login":
    # Save session state
    save_session_to_db()
    
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    header {visibility:hidden;}
    
    /* Remove Streamlit default styles */
    .stApp { background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%); }
    
    /* Main container */
    .main { min-height: 100vh; display: flex; align-items: center; justify-content: center; }
    
    /* Login box */
    .login-box {
        background: rgba(5,15,35,0.85);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 40px;
        width: 100%;
        max-width: 420px;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    }
    
    /* Logo */
    .login-logo {
        text-align: center;
        margin-bottom: 30px;
    }
    
    .login-logo img {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        border: 3px solid rgba(255,255,255,0.3);
        margin-bottom: 15px;
    }
    
    .login-title {
        font-size: 28px;
        font-weight: 800;
        background: linear-gradient(135deg, #ff0066, #00ccff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
    
    .login-subtitle {
        color: #a0b3d6;
        font-size: 14px;
        margin-bottom: 30px;
    }
    
    /* Input fields */
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
        color: white !important;
        padding: 14px 18px !important;
        font-size: 16px !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #ff0066 !important;
        box-shadow: 0 0 0 2px rgba(255,0,102,0.2) !important;
    }
    
    /* Login button */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #ff0066, #ff3399);
        color: white;
        border: none;
        padding: 16px;
        border-radius: 12px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        margin-top: 10px;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(255,0,102,0.3);
    }
    
    /* Footer */
    .login-footer {
        text-align: center;
        margin-top: 20px;
        color: #8899cc;
        font-size: 13px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        
        # Logo and title
        st.markdown(f"""
        <div class="login-logo">
            <img src="data:image/png;base64,{logo_b64}">
            <div class="login-title">𝄞 Karaoke Reels</div>
            <div class="login-subtitle">Sign in to continue</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Input fields
        username = st.text_input("Username", placeholder="admin / user1 / user2", key="login_user")
        password = st.text_input("Password", type="password", placeholder="Enter password", key="login_pass")
        
        # Login button
        if st.button("🚀 Login", key="login_btn"):
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                hashed_pass = hash_password(password)
                if username == "admin" and ADMIN_HASH and hashed_pass == ADMIN_HASH:
                    st.session_state.user = username
                    st.session_state.role = "admin"
                    st.session_state.page = "Admin Dashboard"
                    st.session_state.login_attempts = 0
                    save_session_to_db()
                    st.rerun()
                elif username == "user1" and USER1_HASH and hashed_pass == USER1_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    st.session_state.login_attempts = 0
                    save_session_to_db()
                    st.rerun()
                elif username == "user2" and USER2_HASH and hashed_pass == USER2_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    st.session_state.login_attempts = 0
                    save_session_to_db()
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    st.error(f"Invalid credentials. Attempt {st.session_state.login_attempts}")
        
        # Footer
        st.markdown("""
        <div class="login-footer">
            Need access? Contact administrator
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# =============== ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    save_session_to_db()
    
    # Custom CSS for admin dashboard
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: 600;
    }
    
    .song-item {
        background: rgba(30, 41, 59, 0.5);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #3b82f6;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title(f"👑 Admin Dashboard - Welcome {st.session_state.user}")
    
    # Navigation
    page_option = st.sidebar.selectbox(
        "Navigation",
        ["📤 Upload Songs", "🎵 Songs List", "🔗 Share Links", "📊 Statistics"]
    )
    
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🚪 Logout", key="admin_logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "Login"
        save_session_to_db()
        st.rerun()
    
    if page_option == "📤 Upload Songs":
        st.subheader("Upload New Song")
        
        col1, col2 = st.columns(2)
        
        with col1:
            song_name = st.text_input("Song Name", placeholder="Enter song name (e.g., ShapeOfYou)")
        
        with col2:
            uploaded_by = st.text_input("Uploaded By", value=st.session_state.user, disabled=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            original_file = st.file_uploader("Original MP3", type=["mp3"], key="orig_up")
        
        with col2:
            acc_file = st.file_uploader("Accompaniment MP3", type=["mp3"], key="acc_up")
        
        with col3:
            lyrics_img = st.file_uploader("Lyrics Image", type=["jpg", "jpeg", "png"], key="lyrics_up")
        
        if st.button("📥 Upload Song", type="primary"):
            if not song_name:
                st.error("Please enter a song name")
            elif not original_file or not acc_file or not lyrics_img:
                st.error("Please upload all three files")
            else:
                # Save files
                original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
                acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
                
                # Determine image extension
                img_ext = os.path.splitext(lyrics_img.name)[1]
                lyrics_path = os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{img_ext}")
                
                with open(original_path, "wb") as f:
                    f.write(original_file.getbuffer())
                
                with open(acc_path, "wb") as f:
                    f.write(acc_file.getbuffer())
                
                with open(lyrics_path, "wb") as f:
                    f.write(lyrics_img.getbuffer())
                
                # Update metadata
                metadata[song_name] = {
                    "uploaded_by": uploaded_by,
                    "timestamp": time.time(),
                    "files": {
                        "original": f"{song_name}_original.mp3",
                        "accompaniment": f"{song_name}_accompaniment.mp3",
                        "lyrics": f"{song_name}_lyrics_bg{img_ext}"
                    }
                }
                save_metadata(metadata)
                
                st.success(f"✅ Successfully uploaded '{song_name}'!")
                st.balloons()
                time.sleep(1)
                st.rerun()
    
    elif page_option == "🎵 Songs List":
        st.subheader("All Songs")
        
        songs = get_uploaded_songs(show_unshared=True)
        
        if not songs:
            st.info("No songs uploaded yet. Use the 'Upload Songs' tab to add songs.")
        else:
            search_term = st.text_input("🔍 Search songs", placeholder="Type to search...")
            
            filtered_songs = [s for s in songs if search_term.lower() in s.lower()] if search_term else songs
            
            for song in filtered_songs:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        st.markdown(f"""
                        <div class="song-item">
                            <h4>{song}</h4>
                            <p>Uploaded by: {metadata.get(song, {}).get('uploaded_by', 'Unknown')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        if st.button("▶ Play", key=f"play_{song}"):
                            st.session_state.selected_song = song
                            st.session_state.page = "Song Player"
                            save_session_to_db()
                            st.rerun()
                    
                    with col3:
                        if st.button("🔗 Share", key=f"share_{song}"):
                            save_shared_link(song, {"shared_by": st.session_state.user, "active": True})
                            st.success(f"'{song}' is now shared with users!")
                    
                    with col4:
                        if st.button("🗑 Delete", key=f"del_{song}"):
                            # Delete files
                            original_path = os.path.join(songs_dir, f"{song}_original.mp3")
                            acc_path = os.path.join(songs_dir, f"{song}_accompaniment.mp3")
                            
                            for path in [original_path, acc_path]:
                                if os.path.exists(path):
                                    os.remove(path)
                            
                            # Delete lyrics image
                            for ext in ['.jpg', '.jpeg', '.png']:
                                lyrics_path = os.path.join(lyrics_dir, f"{song}_lyrics_bg{ext}")
                                if os.path.exists(lyrics_path):
                                    os.remove(lyrics_path)
                            
                            # Delete from metadata
                            if song in metadata:
                                del metadata[song]
                                save_metadata(metadata)
                            
                            # Delete shared link if exists
                            delete_shared_link(song)
                            
                            st.success(f"✅ '{song}' deleted successfully!")
                            time.sleep(1)
                            st.rerun()
    
    elif page_option == "🔗 Share Links":
        st.subheader("Manage Shared Links")
        
        songs = get_uploaded_songs(show_unshared=True)
        shared_songs = load_shared_links()
        
        if not songs:
            st.info("No songs available to share.")
        else:
            for song in songs:
                is_shared = song in shared_songs
                
                col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
                
                with col1:
                    status = "✅ Shared" if is_shared else "❌ Not Shared"
                    st.write(f"**{song}** - {status}")
                
                with col2:
                    if is_shared:
                        if st.button("🚫 Unshare", key=f"unshare_{song}"):
                            delete_shared_link(song)
                            st.success(f"'{song}' is no longer shared")
                            time.sleep(1)
                            st.rerun()
                    else:
                        if st.button("✅ Share", key=f"makeshare_{song}"):
                            save_shared_link(song, {"shared_by": st.session_state.user, "active": True})
                            st.success(f"'{song}' is now shared!")
                            time.sleep(1)
                            st.rerun()
                
                with col3:
                    if st.button("▶ Play", key=f"playshare_{song}"):
                        st.session_state.selected_song = song
                        st.session_state.page = "Song Player"
                        save_session_to_db()
                        st.rerun()
                
                with col4:
                    if is_shared:
                        share_url = f"{APP_URL}?song={quote(song)}"
                        st.markdown(f"`{share_url}`")
    
    elif page_option == "📊 Statistics":
        st.subheader("Statistics")
        
        total_songs = len(get_uploaded_songs(show_unshared=True))
        shared_songs = len(load_shared_links())
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Songs", total_songs)
        
        with col2:
            st.metric("Shared Songs", shared_songs)
        
        with col3:
            st.metric("Private Songs", total_songs - shared_songs)
        
        # Recent activity
        st.subheader("Recent Activity")
        
        # Get recent uploads from metadata
        recent_uploads = []
        for song, info in metadata.items():
            if 'timestamp' in info:
                recent_uploads.append({
                    'song': song,
                    'uploaded_by': info.get('uploaded_by', 'Unknown'),
                    'timestamp': float(info.get('timestamp', 0))
                })
        
        # Sort by timestamp (newest first)
        recent_uploads.sort(key=lambda x: x['timestamp'], reverse=True)
        
        for upload in recent_uploads[:5]:
            time_str = datetime.fromtimestamp(upload['timestamp']).strftime("%Y-%m-%d %H:%M")
            st.write(f"• **{upload['song']}** uploaded by {upload['uploaded_by']} at {time_str}")

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    save_session_to_db()
    
    # Custom CSS for user dashboard
    st.markdown("""
    <style>
    .user-song-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        border: 1px solid rgba(255,255,255,0.1);
        transition: transform 0.3s ease;
    }
    
    .user-song-card:hover {
        transform: translateY(-5px);
        border-color: #3b82f6;
    }
    
    .play-btn {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        border: none;
        padding: 10px 25px;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title(f"🎤 Welcome, {st.session_state.user}!")
    
    st.markdown("---")
    
    st.subheader("🎵 Available Songs")
    
    songs = get_uploaded_songs(show_unshared=False)
    
    if not songs:
        st.info("""
        No songs available yet. 
        
        📞 Please contact the administrator to share songs with you.
        
        Once songs are shared, they will appear here automatically.
        """)
    else:
        # Search bar
        search = st.text_input("🔍 Search for songs", placeholder="Type song name...")
        
        # Filter songs based on search
        if search:
            songs = [s for s in songs if search.lower() in s.lower()]
        
        # Display songs in a grid
        cols = st.columns(2)
        
        for idx, song in enumerate(songs):
            col_idx = idx % 2
            with cols[col_idx]:
                st.markdown(f"""
                <div class="user-song-card">
                    <h3>{song}</h3>
                    <p>Shared by: {metadata.get(song, {}).get('uploaded_by', 'Admin')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("▶ Play Now", key=f"user_play_{song}"):
                    st.session_state.selected_song = song
                    st.session_state.page = "Song Player"
                    save_session_to_db()
                    st.rerun()
    
    st.markdown("---")
    
    # Logout button at bottom
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()

# =============== SONG PLAYER ===============
elif st.session_state.page == "Song Player" and st.session_state.get("selected_song"):
    save_session_to_db()
    
    selected_song = st.session_state.get("selected_song")
    
    # Check access
    shared_links = load_shared_links()
    is_shared = selected_song in shared_links
    is_admin = st.session_state.role == "admin"
    is_guest = st.session_state.role == "guest"
    
    if not (is_shared or is_admin or is_guest):
        st.error("❌ Access Denied! This song is not shared.")
        if st.button("← Go Back"):
            if st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            else:
                st.session_state.page = "User Dashboard"
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
    
    # Check if files exist
    if not os.path.exists(original_path) or not os.path.exists(accompaniment_path):
        st.error("❌ Song files not found!")
        if st.button("← Go Back"):
            if st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            else:
                st.session_state.page = "User Dashboard"
            save_session_to_db()
            st.rerun()
        st.stop()
    
    # Get base64 data
    original_b64 = file_to_base64(original_path)
    accompaniment_b64 = file_to_base64(accompaniment_path)
    lyrics_b64 = file_to_base64(lyrics_path) if lyrics_path else ""
    
    # Custom CSS for player
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    header { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    
    .player-header {
        background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
        padding: 15px 25px;
        border-radius: 15px;
        margin-bottom: 20px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .back-btn {
        background: rgba(255,255,255,0.1);
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        cursor: pointer;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .back-btn:hover {
        background: rgba(255,255,255,0.2);
    }
    
    .song-title {
        font-size: 28px;
        font-weight: 700;
        background: linear-gradient(135deg, #ff0066, #00ccff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Player header
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        if st.button("← Back", key="player_back"):
            if st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            elif st.session_state.role == "user":
                st.session_state.page = "User Dashboard"
            else:
                st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
    
    with col2:
        st.markdown(f'<div class="song-title">🎤 {selected_song}</div>', unsafe_allow_html=True)
    
    with col3:
        st.write(f"👤 {st.session_state.user}")
    
    st.markdown("---")
    
    # Optimized HTML player for Railway
    player_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>🎤 Karaoke Player - {selected_song}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                background: #000; 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: white;
                overflow: hidden;
                width: 100%;
                height: 100vh;
            }}
            
            .container {{
                width: 100%;
                height: 100vh;
                position: relative;
            }}
            
            .lyrics-image {{
                width: 100%;
                height: 85vh;
                object-fit: contain;
                background: #111;
            }}
            
            .logo {{
                position: absolute;
                top: 20px;
                left: 20px;
                width: 60px;
                height: 60px;
                border-radius: 50%;
                border: 2px solid rgba(255,255,255,0.3);
                z-index: 10;
            }}
            
            .controls {{
                position: absolute;
                bottom: 0;
                left: 0;
                width: 100%;
                background: rgba(0,0,0,0.8);
                padding: 20px;
                display: flex;
                justify-content: center;
                gap: 15px;
                z-index: 100;
            }}
            
            .control-btn {{
                background: linear-gradient(135deg, #ff0066, #ff3399);
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 25px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                min-width: 150px;
            }}
            
            .control-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(255,0,102,0.4);
            }}
            
            .control-btn:active {{
                transform: translateY(0);
            }}
            
            .control-btn.stop {{
                background: linear-gradient(135deg, #ff3300, #ff6600);
            }}
            
            .status {{
                position: absolute;
                top: 20px;
                right: 20px;
                background: rgba(0,0,0,0.7);
                padding: 10px 20px;
                border-radius: 20px;
                font-size: 14px;
                z-index: 10;
            }}
            
            .recording-indicator {{
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(255,0,0,0.8);
                padding: 10px 30px;
                border-radius: 30px;
                font-size: 24px;
                font-weight: bold;
                display: none;
                z-index: 50;
                animation: pulse 1.5s infinite;
            }}
            
            @keyframes pulse {{
                0% {{ opacity: 0.7; }}
                50% {{ opacity: 1; }}
                100% {{ opacity: 0.7; }}
            }}
            
            canvas {{
                display: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <img class="logo" src="data:image/png;base64,{logo_b64}">
            
            <div class="status" id="status">Ready 🎤</div>
            
            <div class="recording-indicator" id="recIndicator">● RECORDING</div>
            
            <img class="lyrics-image" id="lyricsImg" src="data:image/jpeg;base64,{lyrics_b64}" 
                 onerror="this.src='https://images.unsplash.com/photo-1511379938547-c1f69419868d?auto=format&fit=crop&w=1920'">
            
            <div class="controls">
                <button class="control-btn" id="playBtn">▶ Play Original</button>
                <button class="control-btn" id="recordBtn">🎙 Start Recording</button>
                <button class="control-btn stop" id="stopBtn" style="display:none;">⏹ Stop Recording</button>
                <button class="control-btn" id="playRecordBtn" style="display:none;">▶ Play Recording</button>
            </div>
        </div>
        
        <!-- Audio elements -->
        <audio id="originalAudio" src="data:audio/mp3;base64,{original_b64}" preload="auto"></audio>
        <audio id="accompanimentAudio" src="data:audio/mp3;base64,{accompaniment_b64}" preload="auto"></audio>
        
        <!-- Canvas for recording -->
        <canvas id="recordingCanvas" width="1920" height="1080"></canvas>
        
        <script>
            // Global variables
            let mediaRecorder;
            let recordedChunks = [];
            let audioContext;
            let isRecording = false;
            let originalAudio = document.getElementById('originalAudio');
            let accompanimentAudio = document.getElementById('accompanimentAudio');
            let status = document.getElementById('status');
            let recIndicator = document.getElementById('recIndicator');
            let canvas = document.getElementById('recordingCanvas');
            let ctx = canvas.getContext('2d');
            let lyricsImg = document.getElementById('lyricsImg');
            
            // Play button
            document.getElementById('playBtn').onclick = function() {{
                if (originalAudio.paused) {{
                    originalAudio.play();
                    this.textContent = '⏸ Pause Original';
                    status.textContent = 'Playing original...';
                }} else {{
                    originalAudio.pause();
                    this.textContent = '▶ Play Original';
                    status.textContent = 'Paused';
                }}
            }};
            
            // Record button
            document.getElementById('recordBtn').onclick = async function() {{
                if (isRecording) return;
                
                try {{
                    isRecording = true;
                    status.textContent = 'Starting recording...';
                    recIndicator.style.display = 'block';
                    
                    // Initialize audio context
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    
                    // Get microphone access
                    const micStream = await navigator.mediaDevices.getUserMedia({{ 
                        audio: {{ 
                            echoCancellation: true,
                            noiseSuppression: true,
                            sampleRate: 44100
                        }} 
                    }});
                    
                    // Create audio nodes
                    const micSource = audioContext.createMediaStreamSource(micStream);
                    const destination = audioContext.createMediaStreamDestination();
                    
                    // Connect microphone
                    micSource.connect(destination);
                    
                    // Start original audio for timing
                    originalAudio.currentTime = 0;
                    accompanimentAudio.currentTime = 0;
                    originalAudio.play();
                    accompanimentAudio.play();
                    
                    // Start drawing on canvas
                    startCanvasDrawing();
                    
                    // Combine video and audio
                    const canvasStream = canvas.captureStream(30);
                    const combinedStream = new MediaStream([
                        ...canvasStream.getVideoTracks(),
                        ...destination.stream.getAudioTracks()
                    ]);
                    
                    // Setup media recorder
                    mediaRecorder = new MediaRecorder(combinedStream, {{
                        mimeType: 'video/webm;codecs=vp9,opus',
                        videoBitsPerSecond: 2500000
                    }});
                    
                    recordedChunks = [];
                    
                    mediaRecorder.ondataavailable = function(event) {{
                        if (event.data.size > 0) {{
                            recordedChunks.push(event.data);
                        }}
                    }};
                    
                    mediaRecorder.onstop = function() {{
                        const blob = new Blob(recordedChunks, {{ type: 'video/webm' }});
                        const url = URL.createObjectURL(blob);
                        
                        // Show play recording button
                        document.getElementById('playRecordBtn').style.display = 'inline-block';
                        document.getElementById('playRecordBtn').onclick = function() {{
                            const recordingAudio = new Audio(url);
                            recordingAudio.play();
                            status.textContent = 'Playing recording...';
                        }};
                        
                        // Download link
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'karaoke_recording_{selected_song}_{{Date.now()}}.webm';
                        a.click();
                    }};
                    
                    mediaRecorder.start(1000); // Collect data every second
                    
                    // Update UI
                    document.getElementById('recordBtn').style.display = 'none';
                    document.getElementById('stopBtn').style.display = 'inline-block';
                    status.textContent = '● Recording...';
                    
                }} catch (error) {{
                    console.error('Recording error:', error);
                    status.textContent = 'Recording failed: ' + error.message;
                    isRecording = false;
                    recIndicator.style.display = 'none';
                }}
            }};
            
            // Stop button
            document.getElementById('stopBtn').onclick = function() {{
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
                this.style.display = 'none';
                document.getElementById('recordBtn').style.display = 'inline-block';
                document.getElementById('playBtn').textContent = '▶ Play Original';
                recIndicator.style.display = 'none';
                status.textContent = 'Recording saved! Click "Play Recording" to listen.';
                
                // Close audio context
                if (audioContext) {{
                    audioContext.close();
                }}
            }};
            
            // Canvas drawing function
            function startCanvasDrawing() {{
                function draw() {{
                    if (!isRecording) return;
                    
                    // Clear canvas
                    ctx.fillStyle = '#000';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    
                    // Draw lyrics image centered
                    const imgRatio = lyricsImg.naturalWidth / lyricsImg.naturalHeight;
                    const canvasRatio = canvas.width / (canvas.height * 0.85);
                    
                    let drawWidth, drawHeight;
                    
                    if (imgRatio > canvasRatio) {{
                        drawWidth = canvas.width;
                        drawHeight = canvas.width / imgRatio;
                    }} else {{
                        drawHeight = canvas.height * 0.85;
                        drawWidth = drawHeight * imgRatio;
                    }}
                    
                    const x = (canvas.width - drawWidth) / 2;
                    const y = (canvas.height * 0.85 - drawHeight) / 2;
                    
                    ctx.drawImage(lyricsImg, x, y, drawWidth, drawHeight);
                    
                    // Draw logo
                    const logo = document.querySelector('.logo');
                    ctx.drawImage(logo, 20, 20, 60, 60);
                    
                    // Draw recording indicator
                    if (isRecording) {{
                        ctx.fillStyle = 'rgba(255,0,0,0.7)';
                        ctx.beginPath();
                        ctx.arc(canvas.width - 50, 50, 15, 0, Math.PI * 2);
                        ctx.fill();
                        
                        ctx.fillStyle = 'white';
                        ctx.font = 'bold 20px Arial';
                        ctx.fillText('REC', canvas.width - 100, 55);
                    }}
                    
                    requestAnimationFrame(draw);
                }}
                
                // Start drawing
                draw();
            }}
            
            // Preload images
            window.onload = function() {{
                // Ensure images are loaded
                if (lyricsImg.complete) {{
                    status.textContent = 'Ready 🎤';
                }} else {{
                    lyricsImg.onload = function() {{
                        status.textContent = 'Ready 🎤';
                    }};
                }}
                
                // Preload audio
                originalAudio.load();
                accompanimentAudio.load();
            }};
            
            // Handle page visibility change
            document.addEventListener('visibilitychange', function() {{
                if (document.hidden && isRecording) {{
                    document.getElementById('stopBtn').click();
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    # Display the player
    html(player_html, height=800, scrolling=False)

# =============== FALLBACK ===============
else:
    st.session_state.page = "Login"
    save_session_to_db()
    st.rerun()

# =============== DEBUG INFO ===============
if st.session_state.get("role") == "admin" and False:  # Set to True for debugging
    with st.sidebar:
        if st.checkbox("Show Debug Info"):
            st.write("### Debug Info")
            st.write(f"Page: {st.session_state.get('page')}")
            st.write(f"User: {st.session_state.get('user')}")
            st.write(f"Role: {st.session_state.get('role')}")
            st.write(f"Selected Song: {st.session_state.get('selected_song')}")
            st.write(f"Session ID: {st.session_state.get('session_id')}")
            
            if st.button("Reset App"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.page = "Login"
                save_session_to_db()
                st.rerun()
