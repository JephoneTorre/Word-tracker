import streamlit as st
import threading
import queue
import time
import os
import tempfile
from audio_capture import AudioChunker
from transcriber import SpeechTranscriber
from nlp_analyzer import RepetitionDetector

# --- Streamlit Page Config ---
st.set_page_config(page_title="Speech Coach AI", page_icon="🎙️", layout="wide")

st.title("🎙️ Real-time Speech Coach")
st.markdown("Detects redundant words, filler words, and repetitions.")

# --- Session State Initialization ---
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'audio_queue' not in st.session_state:
    st.session_state.audio_queue = queue.Queue()
    
@st.cache_resource
def load_models():
    # Cache prevents reloading Whisper on every single Streamlit re-run
    transcriber = SpeechTranscriber(model_size="base")
    detector = RepetitionDetector(window_size=15)
    chunker = AudioChunker(samplerate=16000, energy_threshold=0.015, silence_duration=1.0)
    return transcriber, detector, chunker

transcriber, detector, chunker = load_models()
# Override thread queue into Streamlit Session queue so the data persists across re-runs
chunker.q = st.session_state.audio_queue

# --- Dashboard Layout: Tabs ---
tab1, tab2 = st.tabs(["🔴 Live Microphone", "📁 Upload Audio"])

with tab1:
    st.subheader("Live Audio Streaming")
    st.markdown("**(Requires a connected microphone)**")
    col1, col2, col3 = st.columns([1,1,2])
    with col1:
        if st.button("Start Listening", type="primary", use_container_width=True, disabled=st.session_state.is_running):
            st.session_state.is_running = True
            chunker.start()
            st.rerun()
    with col2:
        if st.button("Stop Listening", use_container_width=True, disabled=not st.session_state.is_running):
            st.session_state.is_running = False
            chunker.stop()
            st.rerun()
    with col3:
        if st.button("Clear History", key="clear_live", use_container_width=True):
            st.session_state.logs = []
            chunker.q.queue.clear()
            st.rerun()

    # --- Placeholder for Real-time Status ---
    status_text = st.empty()
    if st.session_state.is_running:
        status_text.info("🎙️ Listening... Speak into your microphone.")
    else:
        status_text.warning("🛑 Stopped.")

with tab2:
    st.subheader("Audio File Upload")
    st.markdown("Upload a **.wav** file to transcribe and analyze its contents. *(We restrict to .wav to bypass needing ffmpeg installed on Windows)*")
    
    uploaded_file = st.file_uploader("Upload an audio file (.wav)", type=["wav"])
    
    if st.button("Analyze Uploaded File", type="primary", key="btn_upload") and uploaded_file is not None:
        with st.spinner("Transcribing and Analyzing Audio... Please wait."):
            # Save uploaded file to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            # Use the whisper model to transcribe the entire file at once
            # transcriber.py was natively upgraded to handle .wav using Scipy natively!
            text = transcriber.transcribe(tmp_path)
            
            # Clean up temp file safely
            try:
                os.remove(tmp_path)
            except:
                pass
            
            if text.strip():
                # We analyze it. 
                warnings = detector.analyze(text)
                st.session_state.logs.insert(0, {"text": f"[UPLOADED AUDIO] {text}", "warnings": warnings})
                st.success("Analysis Complete!")
            else:
                st.error("No speech detected in the uploaded file.")

st.divider()

col_stats, col_logs = st.columns([1, 2])

# Background fetcher to maintain UI responsiveness for live mode
if st.session_state.is_running:
    try:
        # Check audio chunk queue briefly
        audio_chunk = st.session_state.audio_queue.get(timeout=0.1)
        
        with status_text.container():
            st.info("⏳ Processing audio chunk...")
            text = transcriber.transcribe(audio_chunk)
            
        if text.strip():
            warnings = detector.analyze(text)
            # Insert at the beginning so newest is on top
            st.session_state.logs.insert(0, {"text": text, "warnings": warnings})
            
    except queue.Empty:
        pass
        
    # Introduce small delay and immediately re-run to simulate listening loop
    time.sleep(0.5)
    st.rerun()

# Compile statistics
total_fillers = 0
total_repetitions = 0
for log in st.session_state.logs:
    for w in log['warnings']:
        if "Filler" in w:
            total_fillers += 1
        elif "repetition" in w:
            total_repetitions += 1

with col_stats:
    st.subheader("Statistics")
    st.metric(label="Total Utterances", value=len(st.session_state.logs))
    st.metric(label="Filler Words Detected", value=total_fillers)
    st.metric(label="Repetitions Detected", value=total_repetitions)

with col_logs:
    st.subheader("Transcription & Feedback Log")
    for log in st.session_state.logs:
        st.markdown(f"**Transcript:** {log['text']}")
        if log['warnings']:
            for w in log['warnings']:
                st.error(f"⚠️ {w}")
        st.markdown("---")
