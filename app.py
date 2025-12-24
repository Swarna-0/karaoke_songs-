import streamlit as st
import os
import base64
import json
from streamlit.components.v1 import html
import hashlib
from urllib.parse import unquote, quote

PORT = int(os.environ.get('PORT', 8501))
st.setpageconfig(page_title="sing-along", layout="wide")

# CONFIG
APPURL = "https://karaoke-project-production.up.railway.app"

# SECURITY - Environment Variables for Password Hashes
ADMINHASH = os.getenv('ADMINHASH')
USER1HASH = os.getenv('USER1HASH')
USER2HASH = os.getenv('USER2HASH')

# PERSISTENT STORAGE
BASESTORAGE = "data" if os.path.exists("data") else os.getcwd()
mediadir = os.path.join(BASESTORAGE, "media")
songsdir = os.path.join(mediadir, "songs")
lyricsdir = os.path.join(mediadir, "lyricsimages")
logodir = os.path.join(mediadir, "logo")
sharedlinksdir = os.path.join(mediadir, "sharedlinks")
metadatapath = os.path.join(mediadir, "songmetadata.json")

os.makedirs(songsdir, exist_ok=True)
os.makedirs(lyricsdir, exist_ok=True)
os.makedirs(logodir, exist_ok=True)
os.makedirs(sharedlinksdir, exist_ok=True)

# Helper functions
def filetobase64(path):
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    return ""

def hashpassword(password):
    return hashlib.sha256(password.encode()).hexdigest()

def loadmetadata():
    if os.path.exists(metadatapath):
        with open(metadatapath, 'r') as f:
            return json.load(f)
    return {}

def savemetadata(data):
    with open(metadatapath, 'w') as f:
        json.dump(data, f, indent=2)

def loadsharedlinks():
    links = {}
    if not os.path.exists(sharedlinksdir):
        return links
    for filename in os.listdir(sharedlinksdir):
        if filename.endswith('.json'):
            songname = filename[:-5]
            filepath = os.path.join(sharedlinksdir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    if data.get('active', True):
                        links[songname] = data
            except:
                links[songname] = {}
    return links

def savesharedlink(songname, linkdata):
    filepath = os.path.join(sharedlinksdir, f"{songname}.json")
    with open(filepath, 'w') as f:
        json.dump(linkdata, f)

def deletesharedlink(songname):
    filepath = os.path.join(sharedlinksdir, f"{songname}.json")
    if os.path.exists(filepath):
        os.remove(filepath)

def getuploadedsongs(showunshared=False):
    songs = []
    if not os.path.exists(songsdir):
        return songs
    sharedlinks = loadsharedlinks()
    for f in os.listdir(songsdir):
        if f.endswith('original.mp3'):
            songname = f.replace('original.mp3', '')
            if showunshared or songname in sharedlinks:
                songs.append(songname)
    return sorted(songs)

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'role' not in st.session_state:
    st.session_state.role = None
if 'page' not in st.session_state:
    st.session_state.page = "Login"
metadata = loadmetadata()

# Logo
defaultlogopath = os.path.join(logodir, "branks3logo.png")
if not os.path.exists(defaultlogopath):
    logoupload = st.file_uploader("Upload Logo PNG (optional)", type=['png'], key='logoupload')
    if logoupload:
        with open(defaultlogopath, 'wb') as f:
            f.write(logoupload.getbuffer())
        st.rerun()
logob64 = filetobase64(defaultlogopath)

# Pages
if st.session_state.page == "Login":
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none !important;}
        header {visibility: hidden;}
        body {background: radial-gradient(circle at top, #335d8c 0%, #0b1b30 55%, #020712 100%);}
        .login-content {padding: 1.8rem 2.2rem 2.2rem 2.2rem;}
        .login-header {display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.8rem; margin-bottom: 1.6rem; text-align: center;}
        .login-header img {width: 60px; height: 60px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.4);}
        .login-title {font-size: 1.6rem; font-weight: 700; width: 100%;}
        .login-sub {font-size: 0.9rem; color: #c3cfdd; margin-bottom: 0.5rem; width: 100%;}
        .stTextInput > input {background: rgba(5,10,25,0.7) !important; border-radius: 10px !important; color: white !important; border: 1px solid rgba(255,255,255,0.2) !important; padding: 12px 14px !important;}
        .stTextInput > input:focus {border-color: rgba(255,255,255,0.6) !important; box-shadow: 0 0 0 1px rgba(255,255,255,0.3);}
        .stButton > button {width: 100%; height: 44px; background: linear-gradient(to right, #1f2937, #020712); border-radius: 10px; font-weight: 600; margin-top: 0.6rem; color: white; border: none;}
    </style>
    """, unsafe_allow_html=True)
    
    left, center, right = st.columns([1, 1.5, 1])
    with center:
        st.markdown('<div class="login-content">', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="login-header">
            <img src="data:image/png;base64,{logob64}">
            <div class="login-title">Karaoke Reels</div>
            <div class="login-sub">Login to continue</div>
        </div>
        """, unsafe_allow_html=True)
        
        username = st.text_input("Email/Username", placeholder="admin, user1, user2", value="")
        password = st.text_input("Password", type="password", placeholder="Enter password", value="")
        
        if st.button("Login"):
            if not username or not password:
                st.error("Enter both username and password")
            else:
                hashedpass = hashpassword(password)
                if username == "admin" and ADMINHASH and hashedpass == ADMINHASH:
                    st.session_state.user = username
                    st.session_state.role = "admin"
                    st.session_state.page = "Admin Dashboard"
                    st.rerun()
                elif username == "user1" and USER1HASH and hashedpass == USER1HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    st.rerun()
                elif username == "user2" and USER2HASH and hashedpass == USER2HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        st.markdown('<div style="margin-top:16px;font-size:0.8rem;color:#b5c2d2;text-align:center;padding-bottom:8px;">Don\'t have access? Contact admin.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    st.title(f"Admin Dashboard - {st.session_state.user}")
    pagesidebar = st.sidebar.radio("Navigate", ["Upload Songs", "Songs List", "Share Links"])
    
    if pagesidebar == "Upload Songs":
        st.subheader("Upload New Song")
        col1, col2, col3 = st.columns(3)
        with col1:
            uploadedoriginal = st.file_uploader("Original Song (original.mp3)", type=['mp3'], key='originalupload')
        with col2:
            uploadedaccompaniment = st.file_uploader("Accompaniment (accompaniment.mp3)", type=['mp3'], key='accupload')
        with col3:
            uploadedlyricsimage = st.file_uploader("Lyrics Image (lyricsbg.jpg/png)", type=['jpg', 'jpeg', 'png'], key='lyricsupload')
        
        if uploadedoriginal and uploadedaccompaniment and uploadedlyricsimage:
            songname = uploadedoriginal.name.replace('original.mp3', '').strip()
            if not songname:
                songname = os.path.splitext(uploadedoriginal.name)[0]
            originalpath = os.path.join(songsdir, f"{songname}original.mp3")
            accpath = os.path.join(songsdir, f"{songname}accompaniment.mp3")
            lyricsext = os.path.splitext(uploadedlyricsimage.name)[1]
            lyricspath = os.path.join(lyricsdir, f"{songname}lyricsbg{lyricsext}")
            
            with open(originalpath, 'wb') as f:
                f.write(uploadedoriginal.getbuffer())
            with open(accpath, 'wb') as f:
                f.write(uploadedaccompaniment.getbuffer())
            with open(lyricspath, 'wb') as f:
                f.write(uploadedlyricsimage.getbuffer())
            
            metadata[songname] = {"uploadedby": st.session_state.user, "timestamp": str({"timestamp": st.session_state.get('timestamp')})}
            savemetadata(metadata)
            st.success(f"Uploaded {songname}")
            st.rerun()
    
    elif pagesidebar == "Songs List":
        st.subheader("All Songs List (Admin View)")
        uploadedsongs = getuploadedsongs(showunshared=True)
        if not uploadedsongs:
            st.warning("No songs uploaded yet.")
        else:
            for s in uploadedsongs:
                col1, col2, col3 = st.columns([3, 1, 2])
                safes = quote(s)
                with col1:
                    st.write(f"{s} - by {metadata.get(s, {}).get('uploadedby', 'Unknown')}")
                with col2:
                    if st.button("Play", key=f"plays_{safes}"):
                        st.session_state.selectedsong = s
                        st.session_state.page = "Song Player"
                        st.rerun()
                with col3:
                    shareurl = f"{APPURL}?song={safes}"
                    st.markdown(f"[Share Link]({shareurl})")
    
    elif pagesidebar == "Share Links":
        st.header("Manage Shared Links")
        allsongs = getuploadedsongs(showunshared=True)
        sharedlinksdata = loadsharedlinks()
        for song in allsongs:
            col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1.5])
            safesong = quote(song)
            isshared = song in sharedlinksdata
            with col1:
                status = "SHARED" if isshared else "NOT SHARED"
                st.write(f"{song} - {status}")
            with col2:
                if st.button("Toggle Share", key=f"toggleshare_{safesong}"):
                    if isshared:
                        deletesharedlink(song)
                        st.success(f"{song} unshared! Users can no longer see this song.")
                    else:
                        savesharedlink(song, {"sharedby": st.session_state.user, "active": True})
                        shareurl = f"{APPURL}?song={safesong}"
                        st.success(f"{song} shared! Link: {shareurl}")
                    st.rerun()
            with col3:
                if isshared:
                    if st.button("Unshare", key=f"unshare_{safesong}"):
                        deletesharedlink(song)
                        st.success(f"{song} unshared! Users cannot see this song anymore.")
                        st.rerun()
            with col4:
                if isshared:
                    shareurl = f"{APPURL}?song={safesong}"
                    st.markdown(f"[Open Link]({shareurl})")
    
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    st.title(f"User Dashboard - {st.session_state.user}")
    st.subheader("Available Songs (Only Shared Songs)")
    uploadedsongs = getuploadedsongs(showunshared=False)
    if not uploadedsongs:
        st.warning("No shared songs available. Contact admin to share songs.")
        st.info("Only admin-shared songs appear here for users.")
    else:
        for song in uploadedsongs:
            col1, col2 = st.columns([3,1])
            with col1:
                st.write(f"{song} (Shared)")
            with col2:
                if st.button("Play", key=f"userplay_{song}"):
                    st.session_state.selectedsong = song
                    st.session_state.page = "Song Player"
                    st.rerun()
    
    if st.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

elif st.session_state.page == "Song Player" and st.session_state.get('selectedsong'):
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none !important;}
        header {visibility: hidden !important;}
        .st-emotion-cache-1pahdxg {display:none !important;}
        .st-emotion-cache-18ni7ap {padding: 0 !important;}
        footer {visibility: hidden !important;}
        div.block-container {padding: 0 !important; margin: 0 !important; width: 100vw !important;}
        html, body {overflow: hidden !important;}
    </style>
    """, unsafe_allow_html=True)
    
    selectedsong = st.session_state.get('selectedsong')
    if not selectedsong:
        st.error("No song selected!")
        st.stop()
    
    # Double-check access permission
    sharedlinks = loadsharedlinks()
    isshared = selectedsong in sharedlinks
    isadmin = st.session_state.role == "admin"
    if not (isshared or isadmin):
        st.error("Access denied! This song is not shared with users.")
        if st.session_state.role == "user":
            st.session_state.page = "User Dashboard"
        else:
            st.session_state.page = "Admin Dashboard"
        st.rerun()
    
    originalpath = os.path.join(songsdir, f"{selectedsong}original.mp3")
    accompanimentpath = os.path.join(songsdir, f"{selectedsong}accompaniment.mp3")
    lyricspath = None
    for ext in ['.jpg', '.jpeg', '.png']:
        p = os.path.join(lyricsdir, f"{selectedsong}lyricsbg{ext}")
        if os.path.exists(p):
            lyricspath = p
            break
    
    originalb64 = filetobase64(originalpath)
    accompanimentb64 = filetobase64(accompanimentpath)
    lyricsb64 = filetobase64(lyricspath)
    
    karaoketemplate = """<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>Karaoke Reels</title>
    <style>
        * { box-sizing: border-box; }
        html, body { margin:0; padding:0; width:100vw; height:100vh; overflow:hidden; background:black; font-family: Poppins, Arial, sans-serif; color:#ddd; }
        .reel-container { width:100vw;height:100vh;position:relative;background:#111;display:flex;align-items:center;justify-content:center;flex-direction:column; }
        .reel-bg { max-width:100%;max-height:75vh;object-fit:contain;border-radius:8px;box-shadow: 0 8px 30px rgba(0,0,0,0.8); }
        .controls { position:relative;margin-top:18px;text-align:center;z-index:30; }
        button { background:linear-gradient(135deg, #ff0066, #ff66cc);border:none;color:white;padding:10px 18px;border-radius:25px;font-size:15px;cursor:pointer;margin:6px;box-shadow: 0 4px 18px rgba(255,0,128,0.25); }
        button:active { transform:scale(.98); }
        #status { position:absolute;top:18px;width:100%;text-align:center;font-size:15px;color:#ccc;text-shadow: 1px 1px 6px rgba(0,0,0,0.9); }
        #logoImg { position:absolute;top:16px;left:16px;width:60px;opacity:0.7;z-index:40; }
        .final-screen { display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.95);justify-content:center;align-items:center;flex-direction:column;z-index:999;gap:12px; }
        canvas#Preview { display:none; }
        .note { font-size:13px; color:#bbb; margin-top:8px; }
    </style>
</head>
<body>
    <div class="reel-container" id="mainScreen">
        <img id="lyricsImg" class="reel-bg" src="data:image/jpeg;base64,LYRICSB64" onerror="this.onerror=null; this.src='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='">
        <img id="logoImg" src="data:image/png;base64,LOGOB64">
        <div id="status">Ready...</div>
        <audio id="originalAudio" src="data:audio/mp3;base64,ORIGINALB64"></audio>
        <audio id="accompaniment" src="data:audio/mp3;base64,ACCOMPB64"></audio>
        <div class="controls">
            <button id="playBtn">Play</button>
            <button id="recordBtn">Record</button>
            <button id="stopBtn" style="display:none">Stop</button>
        </div>
        <div class="note">Recording happens in your browser. Play Recording in same page.</div>
    </div>
    <div class="final-screen" id="finalScreen">
        <div style="text-align:center">
            <img id="finalPreviewImg" class="reel-bg" style="max-height:60vh">
        </div>
        <div id="statusFinal" style="color:white;font-size:18px">Done!</div>
        <div style="display:flex; gap:10px; align-items:center; margin-top:8px;">
            <button id="playRecordingBtn">Play Recording</button>
            <a id="downloadRecordingBtn" download="karaokeoutput.webm"><button>Download</button></a>
            <button id="newBtn">Create New</button>
        </div>
        <div class="note">Recording playback stays on the same page.</div>
    </div>
    <canvas id="Preview"></canvas>
    <script>
        let mediaRecorder, recordedChunks = [], mixedBlob = null, playRecordingAudio = null, isPlaying = false;
        const original = document.getElementById('originalAudio');
        const acc = document.getElementById('accompaniment');
        const status = document.getElementById('status');
        const statusFinal = document.getElementById('statusFinal');
        const playBtn = document.getElementById('playBtn');
        const recordBtn = document.getElementById('recordBtn');
        const stopBtn = document.getElementById('stopBtn');
        const mainScreen = document.getElementById('mainScreen');
        const finalScreen = document.getElementById('finalScreen');
        const playRecordingBtn = document.getElementById('playRecordingBtn');
        const downloadRecordingBtn = document.getElementById('downloadRecordingBtn');
        const newBtn = document.getElementById('newBtn');
        const lyricsImg = document.getElementById('lyricsImg');
        const finalPreviewImg = document.getElementById('finalPreviewImg');
        const canvas = document.getElementById('Preview');
        const ctx = canvas.getContext('2d');
        const logoImg = new Image();
        logoImg.src = 'data:image/png;base64,LOGOB64';

        async function safePlay(a) {
            try {
                await a.play();
            } catch(e) {
                console.log('play blocked', e);
            }
        }

        playBtn.onclick = async () => {
            if (original.paused) {
                await safePlay(original);
                playBtn.innerText = 'Pause';
                status.innerText = 'Playing Song...';
            } else {
                original.pause();
                playBtn.innerText = 'Play';
                status.innerText = 'Paused';
            }
        };

        recordBtn.onclick = async () => {
            recordedChunks = [];
            status.innerText = 'Preparing mic...';
            
            let micStream;
            try {
                micStream = await navigator.mediaDevices.getUserMedia({
                    audio: { echoCancellation: true, noiseSuppression: true },
                    video: false
                });
            } catch(err) {
                alert('Allow microphone access');
                return;
            }

            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const micSource = audioCtx.createMediaStreamSource(micStream);
            
            const accResp = await fetch(acc.src);
            const accBuf = await accResp.arrayBuffer();
            const accDecoded = await audioCtx.decodeAudioData(accBuf);
            const accSource = audioCtx.createBufferSource();
            accSource.buffer = accDecoded;
            
            const dest = audioCtx.createMediaStreamDestination();
            const micGain = audioCtx.createGain();
            micGain.gain.value = 1.0;
            const accGain = audioCtx.createGain();
            accGain.gain.value = 0.7;
            
            micSource.connect(micGain).connect(dest);
            accSource.connect(accGain).connect(dest);
            
            const accOutSource = audioCtx.createBufferSource();
            accOutSource.buffer = accDecoded;
            accOutSource.connect(audioCtx.destination);
            
            accSource.start();
            accOutSource.start();
            await new Promise(res => setTimeout(res, 150));
            
            const img = lyricsImg;
            const w = img.naturalWidth || 1280;
            const h = img.naturalHeight || 720;
            canvas.width = w;
            canvas.height = h;
            
            let rafId;
            function drawFrame() {
                ctx.fillStyle = '#000';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                if (img && img.src) {
                    const iw = img.naturalWidth / canvas.width;
                    const ih = img.naturalHeight / canvas.height;
                    const scale = Math.max(canvas.width / iw, canvas.height / ih);
                    const dw = iw * scale;
                    const dh = ih * scale;
                    const dx = (canvas.width - dw) / 2;
                    const dy = (canvas.height - dh) / 2;
                    ctx.drawImage(img, dx, dy, dw, dh);
                }
                if (logoImg.complete) {
                    const logoWidth = 100;
                    const logoHeight = logoImg.naturalHeight * logoWidth / logoImg.naturalWidth;
                    ctx.globalAlpha = 0.7;
                    ctx.drawImage(logoImg, 20, 20, logoWidth, logoHeight);
                    ctx.globalAlpha = 1.0;
                }
                rafId = requestAnimationFrame(drawFrame);
            }
            drawFrame();

            const canvasStream = canvas.captureStream(25);
            const mixedAudioStream = dest.stream;
            const combinedStream = new MediaStream([
                ...canvasStream.getVideoTracks(),
                ...mixedAudioStream.getAudioTracks()
            ]);
            
            try {
                mediaRecorder = new MediaRecorder(combinedStream, { mimeType: 'video/webm;codecs=vp8,opus' });
            } catch {
                mediaRecorder = new MediaRecorder(combinedStream);
            }
            
            mediaRecorder.ondataavailable = e => {
                if (e.data && e.data.size > 0) recordedChunks.push(e.data);
            };
            
            mediaRecorder.start();
            original.currentTime = 0;
            acc.currentTime = 0;
            try { await original.play(); } catch {}
            try { await acc.play(); } catch {}
            
            playBtn.style.display = 'none';
            recordBtn.style.display = 'none';
            stopBtn.style.display = 'inline-block';
            status.innerText = 'Recording...';
            
            original.onended = async () => stopRecording();
            stopBtn.onclick = async () => stopRecording();
            
            async function stopRecording() {
                try { mediaRecorder.stop(); } catch {}
                try { accSource.stop(); accOutSource.stop(); audioCtx.close(); } catch {}
                cancelAnimationFrame(rafId);
                try { original.pause(); acc.pause(); } catch {}
                try { micStream.getTracks().forEach(t => t.stop()); } catch {}
                status.innerText = 'Processing mix... Please wait';
                stopBtn.style.display = 'none';
            }
            
            mediaRecorder.onstop = async () => {
                mixedBlob = new Blob(recordedChunks, { type: 'video/webm' });
                const url = URL.createObjectURL(mixedBlob);
                finalPreviewImg.src = lyricsImg.src;
                downloadRecordingBtn.href = url;
                downloadRecordingBtn.setAttribute('download', `karaoke-${Date.now()}.webm`);
                mainScreen.style.display = 'none';
                finalScreen.style.display = 'flex';
                statusFinal.innerText = '🎤 Recording Complete!';
            };
        };
        
        playRecordingBtn.onclick = () => {
            if (!mixedBlob) return;
            if (!isPlaying) {
                playRecordingAudio = new Audio(URL.createObjectURL(mixedBlob));
                playRecordingAudio.play();
                isPlaying = true;
                playRecordingBtn.innerText = 'Stop';
                playRecordingAudio.onended = () => {
                    isPlaying = false;
                    playRecordingBtn.innerText = 'Play Recording';
                };
            } else {
                playRecordingAudio.pause();
                playRecordingAudio.currentTime = 0;
                isPlaying = false;
                playRecordingBtn.innerText = 'Play Recording';
            }
        };
        
        newBtn.onclick = () => {
            finalScreen.style.display = 'none';
            mainScreen.style.display = 'flex';
            status.innerText = 'Ready';
            playBtn.style.display = 'inline-block';
            playBtn.innerText = 'Play';
            recordBtn.style.display = 'inline-block';
            stopBtn.style.display = 'none';
            if (playRecordingAudio) {
                playRecordingAudio.pause();
                playRecordingAudio = null;
            }
            isPlaying = false;
            mixedBlob = null;
            recordedChunks = [];
        };
    </script>
</body>
</html>"""
    
    karaokehtml = karaoketemplate.replace('LYRICSB64', lyricsb64 or '')
    karaokehtml = karaokehtml.replace('LOGOB64', logob64 or '')
    karaokehtml = karaokehtml.replace('ORIGINALB64', originalb64 or '')
    karaokehtml = karaokehtml.replace('ACCOMPB64', accompanimentb64 or '')
    html(karaokehtml, height=700, width=1920)

else:
    st.session_state.page = "Login"
    st.rerun()
