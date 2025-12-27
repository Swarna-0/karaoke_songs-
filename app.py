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

# =============== FIXED: QUERY PARAMETER PROCESSING ===============
def process_query_params():
    query_params = st.query_params

    if "song" in query_params:
        song_from_url = unquote(query_params["song"])

        # Always set song from URL
        st.session_state.selected_song = song_from_url
        st.session_state.page = "Song Player"

        # Auto guest if not logged in
        if not st.session_state.get("user"):
            st.session_state.user = "guest"
            st.session_state.role = "guest"

        save_session_to_db()

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

# Process query parameters FIRST
process_query_params()

metadata = load_metadata()

# Logo
default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
if not os.path.exists(default_logo_path):
    pass
logo_b64 = file_to_base64(default_logo_path) if os.path.exists(default_logo_path) else ""

# =============== RESPONSIVE LOGIN PAGE (SAME AS BEFORE) ===============
if st.session_state.page == "Login":
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

    left, center, right = st.columns([1, 1.5, 1])
    with center:
        st.markdown('<div class="login-content">', unsafe_allow_html=True)
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
                    st.session_state.selected_song = None
                    save_session_to_db()
                    st.rerun()
                elif username == "user1" and USER1_HASH and hashed_pass == USER1_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    st.session_state.selected_song = None
                    save_session_to_db()
                    st.rerun()
                elif username == "user2" and USER2_HASH and hashed_pass == USER2_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    st.session_state.selected_song = None
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

# =============== ADMIN DASHBOARD WITH DJANGO UI ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    save_session_to_db()
    
    # ✅ DJANGO-STYLE ADMIN DASHBOARD CSS
    st.markdown("""
    <style>
    /* Hide Streamlit default elements */
    [data-testid="stSidebar"] {display: none !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    
    /* Django-style Admin Dashboard */
    .django-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
        font-family: Arial, sans-serif;
        background: #111;
        color: white;
    }
    
    .django-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 30px;
        padding-bottom: 15px;
        border-bottom: 1px solid #333;
    }
    
    .django-title {
        font-size: 28px;
        font-weight: bold;
        background: linear-gradient(135deg, #ff0066, #ff66cc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .django-tabs {
        display: flex;
        gap: 10px;
        margin-bottom: 30px;
        flex-wrap: wrap;
    }
    
    .django-tab-btn {
        background: #222;
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 16px;
        cursor: pointer;
        text-decoration: none;
        display: inline-block;
        transition: all 0.3s;
    }
    
    .django-tab-btn:hover {
        background: #333;
    }
    
    .django-tab-btn.active {
        background: linear-gradient(135deg, #ff0066, #ff66cc);
    }
    
    .django-card {
        background: #222;
        padding: 25px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #333;
    }
    
    .django-song-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 18px;
        border-bottom: 1px solid #333;
        transition: background 0.3s;
    }
    
    .django-song-item:hover {
        background: #2a2a2a;
    }
    
    .django-btn {
        background: linear-gradient(135deg, #ff0066, #ff66cc);
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 25px;
        cursor: pointer;
        text-decoration: none;
        display: inline-block;
        font-size: 14px;
        transition: opacity 0.3s;
    }
    
    .django-btn:hover {
        opacity: 0.9;
    }
    
    .django-btn.logout {
        background: linear-gradient(135deg, #1f2937, #020712);
    }
    
    .django-btn.shared {
        background: linear-gradient(135deg, #00ff88, #66ffcc);
    }
    
    .django-btn.private {
        background: linear-gradient(135deg, #ff9900, #ffcc00);
    }
    
    .django-url {
        word-break: break-all;
        font-size: 12px;
        color: #aaa;
        margin-top: 5px;
        padding: 5px;
        background: #2a2a2a;
        border-radius: 5px;
    }
    
    .django-upload-form {
        display: flex;
        flex-direction: column;
        gap: 20px;
    }
    
    .django-file-input {
        background: #333;
        color: white;
        border: 1px solid #555;
        padding: 15px;
        border-radius: 8px;
        font-size: 16px;
        min-height: 60px;
        display: flex;
        align-items: center;
    }
    
    .django-text-input {
        background: #333;
        color: white;
        border: 1px solid #555;
        padding: 15px;
        border-radius: 8px;
        font-size: 16px;
        width: 100%;
    }
    
    .django-text-input::placeholder {
        color: #aaa;
    }
    
    .django-stats {
        display: flex;
        gap: 20px;
        margin-bottom: 20px;
    }
    
    .django-stat-card {
        background: #222;
        padding: 20px;
        border-radius: 10px;
        flex: 1;
        text-align: center;
        border: 1px solid #333;
    }
    
    .django-stat-number {
        font-size: 32px;
        font-weight: bold;
        background: linear-gradient(135deg, #ff0066, #ff66cc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .django-stat-label {
        font-size: 14px;
        color: #aaa;
        margin-top: 5px;
    }
    
    .share-url-container {
        margin-top: 10px;
        padding: 10px;
        background: #2a2a2a;
        border-radius: 5px;
        border-left: 4px solid #ff0066;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize admin page state
    if 'admin_page' not in st.session_state:
        st.session_state.admin_page = "upload"
    
    # Get songs data
    all_songs = get_uploaded_songs(show_unshared=True)
    shared_songs = get_uploaded_songs(show_unshared=False)
    shared_links = load_shared_links()
    
    # Django-style Admin Dashboard HTML
    admin_html = f"""
    <div class="django-container">
        <div class="django-header">
            <div class="django-title">👑 Admin Dashboard - {st.session_state.user}</div>
            <button class="django-btn logout" onclick="window.location.href='?logout=true'">🚪 Logout</button>
        </div>
        
        <div class="django-stats">
            <div class="django-stat-card">
                <div class="django-stat-number">{len(all_songs)}</div>
                <div class="django-stat-label">Total Songs</div>
            </div>
            <div class="django-stat-card">
                <div class="django-stat-number">{len(shared_songs)}</div>
                <div class="django-stat-label">Shared Songs</div>
            </div>
            <div class="django-stat-card">
                <div class="django-stat-number">{len(all_songs) - len(shared_songs)}</div>
                <div class="django-stat-label">Private Songs</div>
            </div>
        </div>
        
        <div class="django-tabs">
            <button class="django-tab-btn {'active' if st.session_state.admin_page == 'upload' else ''}" 
                    onclick="window.location.href='?admin_page=upload'">📤 Upload Songs</button>
            <button class="django-tab-btn {'active' if st.session_state.admin_page == 'songs' else ''}" 
                    onclick="window.location.href='?admin_page=songs'">🎵 Songs List</button>
            <button class="django-tab-btn {'active' if st.session_state.admin_page == 'share' else ''}" 
                    onclick="window.location.href='?admin_page=share'">🔗 Share Links</button>
        </div>
    """
    
    # Handle query parameters for admin page
    if "admin_page" in st.query_params:
        st.session_state.admin_page = st.query_params["admin_page"]
    
    # Upload Songs Page
    if st.session_state.admin_page == "upload":
        admin_html += """
        <div class="django-card">
            <h3 style="margin-top:0;margin-bottom:20px;color:#ff66cc;">📤 Upload New Song</h3>
            <div class="django-upload-form">
                <input type="text" class="django-text-input" id="songTitleInput" 
                       placeholder="🎵 Enter Song Title (e.g. 'Shape of You')">
                <input type="file" class="django-file-input" id="originalFileInput" accept=".mp3">
                <input type="file" class="django-file-input" id="accompanimentFileInput" accept=".mp3">
                <input type="file" class="django-file-input" id="lyricsImageInput" accept="image/*">
                <button class="django-btn" style="width:100%;padding:15px;font-size:16px;" 
                        onclick="uploadSong()">🚀 Upload Song</button>
            </div>
        </div>
        """
    
    # Songs List Page
    elif st.session_state.admin_page == "songs":
        admin_html += f"""
        <div class="django-card">
            <h3 style="margin-top:0;margin-bottom:20px;color:#ff66cc;">🎵 All Songs List ({len(all_songs)})</h3>
        """
        
        if not all_songs:
            admin_html += """
            <div style="text-align:center;padding:40px;color:#ccc;">
                <h3>❌ No songs uploaded yet</h3>
                <p>Upload your first song to get started!</p>
            </div>
            """
        else:
            for idx, song in enumerate(all_songs):
                is_shared = song in shared_links
                uploaded_by = metadata.get(song, {}).get('uploaded_by', 'Unknown')
                safe_song = quote(song)
                share_url = f"{APP_URL}?song={safe_song}"
                
                admin_html += f"""
                <div class="django-song-item">
                    <div>
                        <strong style="font-size:16px;">{song}</strong><br>
                        <small style="color:#aaa;">Uploaded by: {uploaded_by}</small>
                    </div>
                    <div style="text-align:right;min-width:300px;">
                        <button class="django-btn" onclick="playSong('{song}')" 
                                style="margin-right:10px;">▶️ Play</button>
                        <button class="django-btn {'shared' if is_shared else 'private'}" 
                                onclick="toggleShare('{song}', this)">
                            {'✅ Shared' if is_shared else '🔒 Private'}
                        </button>
                        {f'<div class="django-url">{share_url}</div>' if is_shared else ''}
                    </div>
                </div>
                """
        
        admin_html += "</div>"
    
    # Share Links Page
    elif st.session_state.admin_page == "share":
        admin_html += f"""
        <div class="django-card">
            <h3 style="margin-top:0;margin-bottom:20px;color:#ff66cc;">🔗 Manage Shared Links</h3>
        """
        
        for song in all_songs:
            is_shared = song in shared_links
            safe_song = quote(song)
            share_url = f"{APP_URL}?song={safe_song}"
            
            admin_html += f"""
            <div class="django-song-item">
                <div style="flex:1;">
                    <strong>{song}</strong>
                    <div style="font-size:14px;color: {'#00ff88' if is_shared else '#ff9900'};">
                        {('✅ SHARED' if is_shared else '❌ NOT SHARED')}
                    </div>
                </div>
                <div style="display:flex;gap:10px;align-items:center;">
                    <button class="django-btn" onclick="toggleShare('{song}', this)">
                        🔄 Toggle Share
                    </button>
                    {'<button class="django-btn private" onclick="unshareSong(\'' + song + '\', this)">🚫 Unshare</button>' if is_shared else ''}
                    <button class="django-btn" onclick="copyShareLink('{share_url}')">📋 Copy Link</button>
                </div>
            </div>
            """
        
        admin_html += "</div>"
    
    admin_html += """
    </div>
    
    <script>
    function playSong(songName) {
        window.location.href = '?song=' + encodeURIComponent(songName);
    }
    
    function toggleShare(songName, btn) {
        btn.disabled = true;
        const originalText = btn.innerText;
        btn.innerText = '⏳...';
        
        // Simulate API call - In Streamlit we'll use query params
        window.location.href = '?toggle_share=' + encodeURIComponent(songName);
    }
    
    function unshareSong(songName, btn) {
        if (confirm('Are you sure you want to unshare "' + songName + '"?')) {
            window.location.href = '?unshare=' + encodeURIComponent(songName);
        }
    }
    
    function copyShareLink(url) {
        navigator.clipboard.writeText(url).then(() => {
            alert('✅ Link copied to clipboard!\\n' + url);
        });
    }
    
    function uploadSong() {
        alert('In Streamlit version, please use the file uploader in the sidebar.');
    }
    </script>
    """
    
    # Render the admin dashboard
    html(admin_html, height=800, scrolling=True)
    
    # Handle sidebar actions for file uploads (Streamlit native)
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📁 File Upload")
        
        # Song title input
        song_title = st.text_input("🎵 Song Title", 
                                  placeholder="Enter song name (e.g. Shape of You)",
                                  key="song_title_input")
        
        # File uploaders
        uploaded_original = st.file_uploader("Original Song (.mp3)", 
                                            type=["mp3"], 
                                            key="original_upload_admin")
        uploaded_accompaniment = st.file_uploader("Accompaniment (.mp3)", 
                                                 type=["mp3"], 
                                                 key="acc_upload_admin")
        uploaded_lyrics_image = st.file_uploader("Lyrics Image (.jpg/.png)", 
                                                type=["jpg", "jpeg", "png"], 
                                                key="lyrics_upload_admin")
        
        if st.button("🚀 Upload Song", key="upload_btn_admin"):
            if not song_title:
                st.error("Please enter a song title!")
            elif not uploaded_original or not uploaded_accompaniment:
                st.error("Please upload both original and accompaniment files!")
            else:
                # Process upload
                song_name = song_title.strip()
                original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
                acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
                
                with open(original_path, "wb") as f:
                    f.write(uploaded_original.getbuffer())
                with open(acc_path, "wb") as f:
                    f.write(uploaded_accompaniment.getbuffer())
                
                # Save lyrics image if provided
                if uploaded_lyrics_image:
                    lyrics_ext = os.path.splitext(uploaded_lyrics_image.name)[1]
                    lyrics_path = os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{lyrics_ext}")
                    with open(lyrics_path, "wb") as f:
                        f.write(uploaded_lyrics_image.getbuffer())
                
                # Update metadata
                metadata[song_name] = {"uploaded_by": st.session_state.user, "timestamp": str(time.time())}
                save_metadata(metadata)
                
                st.success(f"✅ Uploaded: {song_name}")
                st.balloons()
                time.sleep(1)
                st.rerun()
        
        st.markdown("---")
        st.markdown("### ⚙️ Quick Actions")
        
        # Handle toggle share from query params
        if "toggle_share" in st.query_params:
            song_to_toggle = unquote(st.query_params["toggle_share"])
            if song_to_toggle in shared_links:
                delete_shared_link(song_to_toggle)
                st.success(f"✅ {song_to_toggle} unshared!")
            else:
                save_shared_link(song_to_toggle, {"shared_by": st.session_state.user, "active": True})
                st.success(f"✅ {song_to_toggle} shared!")
            time.sleep(0.5)
            st.query_params.clear()
            st.rerun()
        
        # Handle unshare from query params
        if "unshare" in st.query_params:
            song_to_unshare = unquote(st.query_params["unshare"])
            delete_shared_link(song_to_unshare)
            st.success(f"✅ {song_to_unshare} unshared!")
            time.sleep(0.5)
            st.query_params.clear()
            st.rerun()
        
        # Handle logout
        if "logout" in st.query_params:
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
        
        # Refresh button
        if st.button("🔄 Refresh", key="refresh_admin"):
            st.rerun()

# =============== USER DASHBOARD WITH DJANGO UI ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    save_session_to_db()
    
    # ✅ DJANGO-STYLE USER DASHBOARD CSS
    st.markdown("""
    <style>
    /* Hide Streamlit default elements */
    [data-testid="stSidebar"] {display: none !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    
    /* Django-style User Dashboard */
    .user-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
        font-family: Arial, sans-serif;
        background: #111;
        color: white;
    }
    
    .user-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 30px;
        padding-bottom: 15px;
        border-bottom: 1px solid #333;
    }
    
    .user-title {
        font-size: 28px;
        font-weight: bold;
        background: linear-gradient(135deg, #00a8ff, #0097e6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .user-song-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px;
        background: #222;
        margin-bottom: 10px;
        border-radius: 10px;
        border-left: 5px solid #00ff88;
        transition: transform 0.3s, background 0.3s;
    }
    
    .user-song-item:hover {
        transform: translateY(-2px);
        background: #2a2a2a;
    }
    
    .user-btn {
        background: linear-gradient(135deg, #00a8ff, #0097e6);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 25px;
        cursor: pointer;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        font-weight: bold;
        transition: opacity 0.3s, transform 0.3s;
    }
    
    .user-btn:hover {
        opacity: 0.9;
        transform: scale(1.05);
    }
    
    .user-btn.logout {
        background: linear-gradient(135deg, #1f2937, #020712);
    }
    
    .user-no-songs {
        text-align: center;
        padding: 60px 20px;
        background: #222;
        border-radius: 10px;
        margin-top: 20px;
        border: 2px dashed #555;
    }
    
    .user-song-info {
        flex: 1;
    }
    
    .user-song-name {
        font-size: 18px;
        font-weight: bold;
        color: #fff;
        margin-bottom: 5px;
    }
    
    .user-song-status {
        font-size: 14px;
        color: #00ff88;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    
    .user-stats {
        display: flex;
        gap: 20px;
        margin-bottom: 30px;
    }
    
    .user-stat-card {
        background: #222;
        padding: 20px;
        border-radius: 10px;
        flex: 1;
        text-align: center;
        border: 1px solid #333;
    }
    
    .user-stat-number {
        font-size: 28px;
        font-weight: bold;
        color: #00a8ff;
    }
    
    .user-stat-label {
        font-size: 14px;
        color: #aaa;
        margin-top: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Get user songs
    user_songs = get_uploaded_songs(show_unshared=False)
    shared_links = load_shared_links()
    
    # Django-style User Dashboard HTML
    user_html = f"""
    <div class="user-container">
        <div class="user-header">
            <div class="user-title">👤 {st.session_state.user}'s Dashboard</div>
            <button class="user-btn logout" onclick="window.location.href='?logout=true'">🚪 Logout</button>
        </div>
        
        <div class="user-stats">
            <div class="user-stat-card">
                <div class="user-stat-number">{len(user_songs)}</div>
                <div class="user-stat-label">Available Songs</div>
            </div>
            <div class="user-stat-card">
                <div class="user-stat-number">{len(shared_links)}</div>
                <div class="user-stat-label">Shared by Admin</div>
            </div>
        </div>
        
        <h3 style="color:#00a8ff;margin-bottom:20px;">🎵 Available Songs (Only Shared)</h3>
    """
    
    if not user_songs:
        user_html += """
        <div class="user-no-songs">
            <h3 style="color:#ccc;margin-bottom:15px;">❌ No shared songs available</h3>
            <p style="color:#aaa;margin-bottom:20px;">Contact admin to share songs with you.</p>
            <div style="font-size:14px;color:#777;background:#1a1a1a;padding:15px;border-radius:8px;">
                <strong>👑 Admin-only features:</strong>
                <ul style="text-align:left;padding-left:20px;margin-top:10px;">
                    <li>Upload new songs</li>
                    <li>Share/unshare songs with users</li>
                    <li>Manage all song files</li>
                </ul>
            </div>
        </div>
        """
    else:
        for song in user_songs:
            safe_song = quote(song)
            user_html += f"""
            <div class="user-song-item">
                <div class="user-song-info">
                    <div class="user-song-name">✅ {song}</div>
                    <div class="user-song-status">
                        <span>🎤 Ready to sing!</span>
                    </div>
                </div>
                <button class="user-btn" onclick="playSong('{song}')">🎤 Sing Now</button>
            </div>
            """
    
    user_html += """
    </div>
    
    <script>
    function playSong(songName) {
        window.location.href = '?song=' + encodeURIComponent(songName);
    }
    </script>
    """
    
    # Render the user dashboard
    html(user_html, height=700, scrolling=True)
    
    # Handle logout
    if "logout" in st.query_params:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "Login"
        save_session_to_db()
        st.rerun()

# =============== SONG PLAYER (SAME AS BEFORE) ===============
elif st.session_state.page == "Song Player" and st.session_state.get("selected_song"):
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
        if st.session_state.role in ["admin", "user"]:
            if st.button("Go Back"):
                if st.session_state.role == "admin":
                    st.session_state.page = "Admin Dashboard"
                elif st.session_state.role == "user":
                    st.session_state.page = "User Dashboard"
                save_session_to_db()
                st.rerun()
        st.stop()

    # Check access permission
    shared_links = load_shared_links()
    is_shared = selected_song in shared_links
    is_admin = st.session_state.role == "admin"
    is_guest = st.session_state.role == "guest"
    came_from_dashboard = st.session_state.role in ["admin", "user"]

    if not (is_admin or came_from_dashboard or is_shared):
        st.error("❌ Access denied!")
        st.stop()

    original_path = os.path.join(songs_dir, f"{selected_song}_original.mp3")
    accompaniment_path = os.path.join(songs_dir, f"{selected_song}_accompaniment.mp3")

    lyrics_path = ""
    for ext in [".jpg", ".jpeg", ".png"]:
        p = os.path.join(lyrics_dir, f"{selected_song}_lyrics_bg{ext}")
        if os.path.exists(p):
            lyrics_path = p
            break

    original_b64 = file_to_base64(original_path)
    accompaniment_b64 = file_to_base64(accompaniment_path)
    lyrics_b64 = file_to_base64(lyrics_path)

    # Karaoke Template (Same as before)
    karaoke_template = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>🎤 Karaoke Reels</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #000; font-family: 'Poppins', sans-serif; height: 100vh; width: 100vw; overflow: hidden; }
.reel-container, .final-reel-container { width: 100%; height: 100%; position: absolute; background: #111; overflow: hidden; }
#status { position: absolute; top: 20px; width: 100%; text-align: center; font-size: 14px; color: #ccc; z-index: 20; text-shadow: 1px 1px 6px rgba(0,0,0,0.9); }
.reel-bg { position: absolute; top: 0; left: 0; width: 100%; height: 85vh; object-fit: contain; object-position: top; }
.lyrics { position: absolute; bottom: 25%; width: 100%; text-align: center; font-size: 2vw; font-weight: bold; color: white; text-shadow: 2px 2px 10px black; }
.controls { position: absolute; bottom: 20%; width: 100%; text-align: center; z-index: 30; }
button { background: linear-gradient(135deg, #ff0066, #ff66cc); border: none; color: white; padding: 8px 20px; border-radius: 25px; font-size: 13px; margin: 4px; box-shadow: 0px 3px 15px rgba(255,0,128,0.4); cursor: pointer; }
button:active { transform: scale(0.95); }
.final-output { position: fixed; width: 100vw; height: 100vh; top: 0; left: 0; background: rgba(0,0,0,0.9); display: none; justify-content: center; align-items: center; z-index: 999; }
#logoImg { position: absolute; top: 20px; left: 20px; width: 60px; z-index: 50; opacity: 0.6; }
canvas { display: none; }
.back-button { position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.7); color: white; padding: 8px 16px; border-radius: 20px; text-decoration: none; font-size: 14px; z-index: 100; }
</style>
</head>
<body>

<div class="reel-container" id="reelContainer">
    <img class="reel-bg" id="mainBg" src="data:image/jpeg;base64,%%LYRICS_B64%%">
    <img id="logoImg" src="data:image/png;base64,%%LOGO_B64%%">
    <div id="status">Ready 🎤</div>
    <audio id="originalAudio" src="data:audio/mp3;base64,%%ORIGINAL_B64%%"></audio>
    <audio id="accompaniment" src="data:audio/mp3;base64,%%ACCOMP_B64%%"></audio>
    <div class="controls">
      <button id="playBtn">▶ Play</button>
      <button id="recordBtn">🎙 Record</button>
      <button id="stopBtn" style="display:none;">⏹ Stop</button>
    </div>
</div>

<div class="final-output" id="finalOutputDiv">
  <div class="final-reel-container">
    <img class="reel-bg" id="finalBg">
    <div id="status"></div>
    <div class="lyrics" id="finalLyrics"></div>
    <div class="controls">
      <button id="playRecordingBtn">▶ Play Recording</button>
      <a id="downloadRecordingBtn" href="#" download>
        <button>⬇ Download</button>
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

const logoImg = new Image();
logoImg.src = document.getElementById("logoImg").src;

/* ================== AUDIO CONTEXT FIX ================== */
async function ensureAudioContext() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioContext.state === "suspended") {
        await audioContext.resume();
    }
}

async function safePlay(audio) {
    try {
        await ensureAudioContext();
        await audio.play();
    } catch (e) {
        console.log("Autoplay blocked:", e);
    }
}

document.addEventListener("visibilitychange", async () => {
    if (!document.hidden) await ensureAudioContext();
});

/* ================== PLAY ORIGINAL ================== */
playBtn.onclick = async () => {
    await ensureAudioContext();
    if (originalAudio.paused) {
        originalAudio.currentTime = 0;
        await safePlay(originalAudio);
        playBtn.innerText = "⏸ Pause";
        status.innerText = "🎵 Playing song...";
    } else {
        originalAudio.pause();
        playBtn.innerText = "▶ Play";
        status.innerText = "⏸ Paused";
    }
};

/* ================== CANVAS DRAW (DJANGO MATCH) ================== */
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
    const y = 0; // TOP aligned

    ctx.drawImage(mainBg, x, y, drawW, drawH);

    /* LOGO — exact Django feel */
    ctx.globalAlpha = 0.6;
    ctx.drawImage(logoImg, 20, 20, 60, 60);
    ctx.globalAlpha = 1;

    canvasRafId = requestAnimationFrame(drawCanvas);
}

/* ================== RECORD ================== */
recordBtn.onclick = async () => {
    if (isRecording) return;
    isRecording = true;

    await ensureAudioContext();
    recordedChunks = [];

    /* MIC */
    const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    micSource = audioContext.createMediaStreamSource(micStream);

    /* ACCOMPANIMENT */
    const accRes = await fetch(accompanimentAudio.src);
    const accBuf = await accRes.arrayBuffer();
    const accDecoded = await audioContext.decodeAudioData(accBuf);

    accSource = audioContext.createBufferSource();
    accSource.buffer = accDecoded;

    const destination = audioContext.createMediaStreamDestination();
    micSource.connect(destination);
    accSource.connect(destination);

    accSource.start();

    canvas.width = 1920;
    canvas.height = 1080;
    drawCanvas();

    const stream = new MediaStream([
        ...canvas.captureStream(30).getTracks(),
        ...destination.stream.getTracks()
    ]);

    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = e => e.data.size && recordedChunks.push(e.data);

    mediaRecorder.onstop = () => {
        cancelAnimationFrame(canvasRafId);

        const blob = new Blob(recordedChunks, { type: "video/webm" });
        const url = URL.createObjectURL(blob);

        if (lastRecordingURL) URL.revokeObjectURL(lastRecordingURL);
        lastRecordingURL = url;

        finalBg.src = mainBg.src;
        finalDiv.style.display = "flex";

        downloadRecordingBtn.href = url;
        downloadRecordingBtn.download = "karaoke_" + Date.now() + ".webm";

        playRecordingBtn.onclick = () => {
            if (!isPlayingRecording) {
                playRecordingAudio = new Audio(url);
                playRecordingAudio.play();
                playRecordingBtn.innerText = "⏹ Stop";
                isPlayingRecording = true;
                playRecordingAudio.onended = resetPlayBtn;
            } else {
                resetPlayBtn();
            }
        };
    };

    mediaRecorder.start();

    originalAudio.currentTime = 0;
    accompanimentAudio.currentTime = 0;
    await safePlay(originalAudio);
    await safePlay(accompanimentAudio);

    playBtn.style.display = "none";
    recordBtn.style.display = "none";
    stopBtn.style.display = "inline-block";
    status.innerText = "🎙 Recording...";
    
    // ✅ AUTOMATIC STOP: Set timeout to stop recording when song ends
    const songDuration = originalAudio.duration * 1000;
    setTimeout(() => {
        if (isRecording) {
            stopBtn.click();
        }
    }, songDuration + 500);
};

/* ================== STOP ================== */
stopBtn.onclick = () => {
    if (!isRecording) return;
    isRecording = false;

    try { mediaRecorder.stop(); } catch {}
    try { accSource.stop(); } catch {}

    originalAudio.pause();
    accompanimentAudio.pause();

    stopBtn.style.display = "none";
    status.innerText = "⏹ Processing...";
};

/* ================== HELPERS ================== */
function resetPlayBtn() {
    if (playRecordingAudio) {
        playRecordingAudio.pause();
        playRecordingAudio.currentTime = 0;
    }
    playRecordingBtn.innerText = "▶ Play Recording";
    isPlayingRecording = false;
}

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
    playBtn.innerText = "▶ Play";
    status.innerText = "Ready 🎤";
};

/* ================== SONG END DETECTION ================== */
originalAudio.addEventListener('ended', () => {
    if (isRecording) {
        setTimeout(() => {
            if (isRecording) {
                stopBtn.click();
            }
        }, 100);
    }
});

accompanimentAudio.addEventListener('ended', () => {
    if (isRecording) {
        setTimeout(() => {
            if (isRecording) {
                stopBtn.click();
            }
        }, 100);
    }
});
</script>
</body>
</html>
"""

    karaoke_html = karaoke_template.replace("%%LYRICS_B64%%", lyrics_b64 or "")
    karaoke_html = karaoke_html.replace("%%LOGO_B64%%", logo_b64 or "")
    karaoke_html = karaoke_html.replace("%%ORIGINAL_B64%%", original_b64 or "")
    karaoke_html = karaoke_html.replace("%%ACCOMP_B64%%", accompaniment_b64 or "")

    # Back button logic
    if st.session_state.role in ["admin", "user"]:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("← Back to Dashboard", key="back_player"):
                if st.session_state.role == "admin":
                    st.session_state.page = "Admin Dashboard"
                    st.session_state.selected_song = None
                elif st.session_state.role == "user":
                    st.session_state.page = "User Dashboard"
                    st.session_state.selected_song = None
                
                if "song" in st.query_params:
                    del st.query_params["song"]
                
                save_session_to_db()
                st.rerun()
    else:
        st.empty()

    html(karaoke_html, height=800, width=1920, scrolling=False)

# =============== FALLBACK ===============
else:
    if "song" in st.query_params:
        st.session_state.page = "Song Player"
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
