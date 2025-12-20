import streamlit as st
import os, base64, json, hashlib
from streamlit.components.v1 import html
from urllib.parse import unquote, quote

st.set_page_config(
    page_title="🎙 sing-along",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================== PWA INJECT ==================
st.markdown("""
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#ff0066">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">

<script>
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/service-worker.js');
}
</script>
""", unsafe_allow_html=True)
# ================================================

APP_URL = "https://karaoke-song.onrender.com/"

ADMIN_HASH = os.getenv("ADMIN_HASH", "")
USER1_HASH = os.getenv("USER1_HASH", "")
USER2_HASH = os.getenv("USER2_HASH", "")

base_dir = os.getcwd()
media_dir = os.path.join(base_dir, "media")
songs_dir = os.path.join(media_dir, "songs")
lyrics_dir = os.path.join(media_dir, "lyrics_images")
logo_dir = os.path.join(media_dir, "logo")
shared_links_dir = os.path.join(media_dir, "shared_links")
metadata_path = os.path.join(media_dir, "song_metadata.json")

for d in [songs_dir, lyrics_dir, logo_dir, shared_links_dir]:
    os.makedirs(d, exist_ok=True)

# ================= HELPERS =================
def file_to_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

def load_metadata():
    return json.load(open(metadata_path)) if os.path.exists(metadata_path) else {}

def save_metadata(d):
    json.dump(d, open(metadata_path, "w"), indent=2)

def get_uploaded_songs():
    return sorted([f.replace("_original.mp3","") for f in os.listdir(songs_dir) if f.endswith("_original.mp3")])

# =============== SESSION INIT ===============
for k,v in {
    "user":None,"role":None,"page":"Login","selected_song":None
}.items():
    st.session_state.setdefault(k,v)

# =============== LOGO ===============
logo_path = os.path.join(logo_dir,"branks3_logo.png")
if not os.path.exists(logo_path):
    up = st.file_uploader("Upload Logo (PNG)", type="png")
    if up:
        open(logo_path,"wb").write(up.getbuffer())
        st.rerun()
logo_b64 = file_to_base64(logo_path)

metadata = load_metadata()

# =============== DEEP LINK =================
qp = st.query_params
song_q = qp.get("song",[None])[0]
if song_q:
    s = unquote(song_q)
    if os.path.exists(os.path.join(songs_dir,f"{s}_original.mp3")):
        st.session_state.selected_song = s
        st.session_state.page = "Song Player"
        st.rerun()

# =============== LOGIN =====================
if st.session_state.page=="Login":
    st.title("🎤 Karaoke Reels")

    c1,c2 = st.columns(2)

    with c1:
        u = st.text_input("User")
        p = st.text_input("Password",type="password")
        if st.button("Login"):
            h = hash_password(p)
            if u=="user1" and h==USER1_HASH or u=="user2" and h==USER2_HASH:
                st.session_state.user=u
                st.session_state.role="user"
                st.session_state.page="User"
                st.rerun()
            else: st.error("Invalid")

    with c2:
        a = st.text_input("Admin")
        ap = st.text_input("Admin Password",type="password")
        if st.button("Admin Login"):
            if a=="admin" and hash_password(ap)==ADMIN_HASH:
                st.session_state.user=a
                st.session_state.role="admin"
                st.session_state.page="Admin"
                st.rerun()
            else: st.error("Invalid")

# =============== ADMIN =====================
elif st.session_state.page=="Admin":
    st.title("👑 Admin")
    for s in get_uploaded_songs():
        col1,col2 = st.columns([3,1])
        with col1: st.write(s)
        with col2:
            st.link_button("Open",f"{APP_URL}?song={quote(s)}")

# =============== USER ======================
elif st.session_state.page=="User":
    st.title("🎧 Songs")
    for s in get_uploaded_songs():
        if st.button(f"▶ {s}"):
            st.session_state.selected_song=s
            st.session_state.page="Song Player"
            st.rerun()

# =============== PLAYER ====================
elif st.session_state.page=="Song Player":
    s = st.session_state.selected_song

    ob = file_to_base64(os.path.join(songs_dir,f"{s}_original.mp3"))
    ab = file_to_base64(os.path.join(songs_dir,f"{s}_accompaniment.mp3"))

    lp=""
    for e in [".jpg",".png",".jpeg"]:
        p=os.path.join(lyrics_dir,f"{s}_lyrics_bg{e}")
        if os.path.exists(p): lp=file_to_base64(p)

    html(open("karaoke_template.html").read()
         .replace("%%ORIGINAL_B64%%",ob)
         .replace("%%ACCOMP_B64%%",ab)
         .replace("%%LYRICS_B64%%",lp)
         .replace("%%LOGO_B64%%",logo_b64),
         height=900)

else:
    st.session_state.page="Login"
    st.rerun()
