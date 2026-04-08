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

# --- Custom Rich UI Aesthetics ---
st.markdown("""
<style>
/* Base Dark Theme Overrides */
.stApp {
    background-color: #0b0f19;
}
h1, h2, h3 {
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif;
}
/* Live Transcript Styling */
.transcript-box {
    font-size: 1.4rem;
    padding: 24px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 16px;
    border-left: 6px solid #3b82f6;
    color: #f8fafc;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    transition: all 0.3s ease;
    line-height: 1.6;
}
/* Stacking Alerts System */
.alert-filler {
    background: linear-gradient(90deg, rgba(234, 179, 8, 0.1) 0%, transparent 100%);
    border-left: 4px solid #eab308;
    padding: 14px 20px;
    border-radius: 8px;
    margin-bottom: 12px;
    color: #fef08a;
    font-size: 1.1rem;
    letter-spacing: 0.5px;
    animation: slideFadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.alert-warning {
    background: linear-gradient(90deg, rgba(249, 115, 22, 0.15) 0%, transparent 100%);
    border-left: 4px solid #f97316;
    padding: 14px 20px;
    border-radius: 8px;
    margin-bottom: 12px;
    color: #fdba74;
    font-size: 1.1rem;
    letter-spacing: 0.5px;
    animation: slideFadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.alert-concern {
    background: linear-gradient(90deg, rgba(239, 68, 68, 0.2) 0%, transparent 100%);
    border-left: 4px solid #ef4444;
    padding: 14px 20px;
    border-radius: 8px;
    margin-bottom: 12px;
    color: #fca5a5;
    font-size: 1.1rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    animation: slideFadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.alert-critical {
    background: linear-gradient(90deg, rgba(220, 38, 38, 0.3) 0%, transparent 100%);
    border-left: 6px solid #dc2626;
    padding: 16px 20px;
    border-radius: 8px;
    margin-bottom: 12px;
    color: #fecaca;
    font-size: 1.2rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    box-shadow: 0 4px 12px rgba(220, 38, 38, 0.15);
    animation: shakePulse 0.5s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
}

/* Animations */
@keyframes slideFadeIn {
    0% { transform: translateX(30px); opacity: 0; }
    100% { transform: translateX(0); opacity: 1; }
}
@keyframes shakePulse {
    0%, 100% { transform: scale(1) translateX(0); opacity: 1; }
    25% { transform: scale(1.02) translateX(-5px); }
    50% { transform: scale(1.02) translateX(5px); }
    75% { transform: scale(1.02) translateX(-5px); }
}
</style>
""", unsafe_allow_html=True)

st.title("🎙️ Dynamic Voice Analysis")
st.markdown("<p style='color: #94a3b8; font-size: 1.1rem; margin-bottom: 2rem;'>A smart coaching assistant with stacking visual notifications for recurring words.</p>", unsafe_allow_html=True)

# --- Session States ---
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'latest_transcript' not in st.session_state:
    st.session_state.latest_transcript = "Waiting for speech..."
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'audio_queue' not in st.session_state:
    st.session_state.audio_queue = queue.Queue()
if 'alert_stack' not in st.session_state:
    st.session_state.alert_stack = []
    
@st.cache_resource
def load_models():
    transcriber = SpeechTranscriber(model_size="base")
    detector = RepetitionDetector(window_size=20) # 20 second rolling window
    chunker = AudioChunker(samplerate=16000, energy_threshold=0.015, silence_duration=1.0)
    return transcriber, detector, chunker

transcriber, detector, chunker = load_models()
chunker.q = st.session_state.audio_queue

# --- User Interface Structure ---
left_col, right_col = st.columns([1.2, 0.8], gap="large")

with left_col:
    # --- Live Engine Controls ---
    control_container = st.container()
    col1, col2, col3 = control_container.columns([1,1,1])
    with col1:
        if st.button("🔴 Start Listening", type="primary", use_container_width=True, disabled=st.session_state.is_running):
            st.session_state.is_running = True
            chunker.start()
            st.rerun()
    with col2:
        if st.button("⏹ Stop Listening", use_container_width=True, disabled=not st.session_state.is_running):
            st.session_state.is_running = False
            chunker.stop()
            st.rerun()
    with col3:
        if st.button("🗑 Clear Session", use_container_width=True):
            st.session_state.logs = []
            st.session_state.alert_stack = []
            st.session_state.latest_transcript = "Waiting for speech..."
            chunker.q.queue.clear()
            st.rerun()

    status_text = st.empty()
    if st.session_state.is_running:
        status_text.markdown("&nbsp;&nbsp;🟢 **Active:** Processing real-time audio chunking...")
        
    st.markdown("### 📝 Live Transcript")
    # Live Floating Output Box
    transcript_placeholder = st.empty()
    transcript_placeholder.markdown(f"<div class='transcript-box'>{st.session_state.latest_transcript}</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📁 Or Upload an Audio (.wav)")
    uploaded_file = st.file_uploader("Analyzes full offline files", type=["wav"], label_visibility="collapsed")
    
    if st.button("Upload & Analyze", type="primary") and uploaded_file is not None:
        with st.spinner("Processing file through Whisper..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            text = transcriber.transcribe(tmp_path)
            try:
                os.remove(tmp_path)
            except:
                pass
            
            if text.strip():
                st.session_state.latest_transcript = text
                warnings = detector.analyze(text)
                
                # Push to global logs
                st.session_state.logs.insert(0, {"text": text, "warnings": warnings})
                
                # Push newest warnings to alert stack
                for w in warnings:
                    st.session_state.alert_stack.insert(0, w)
                    # Use Streamlit Toasts natively for floating popups
                    icon = "🟡" if w['level'] in ['filler','warning'] else "🟠" if w['level'] == 'concern' else "🚨"
                    st.toast(w['message'], icon=icon)
                st.rerun()

with right_col:
    st.markdown("### 🔔 Event Stack")
    st.markdown("<p style='color: #64748b; font-size: 0.9rem'>Alerts auto-aggregate dynamically as repetitions escalate.</p>", unsafe_allow_html=True)
    
    # Render Dashboard Stats
    stat1, stat2 = st.columns(2)
    stat1.metric("Lines Spoken", len(st.session_state.logs))
    stat2.metric("Total Flags", sum([len(l['warnings']) for l in st.session_state.logs]))
    
    st.markdown("<br/>", unsafe_allow_html=True)
    
    # Render escalating notification blocks
    alert_placeholder = st.empty()
    alert_html = ""
    # We only show the latest 8 alerts on screen to keep the dashboard clean
    for w in st.session_state.alert_stack[:8]:
        css_class = f"alert-{w['level']}"
        alert_html += f"<div class='{css_class}'>{w['message']}</div>"
    
    if not alert_html:
        alert_html = "<div style='color: #475569; padding: 20px; border: 1px dashed #334155; border-radius: 8px; text-align: center'>No repetitions logged yet.</div>"
        
    alert_placeholder.markdown(alert_html, unsafe_allow_html=True)

# --- Background Worker Processor ---
if st.session_state.is_running:
    try:
        # Check audio queue briefly
        audio_chunk = st.session_state.audio_queue.get(timeout=0.1)
        
        with status_text.container():
            st.markdown("&nbsp;&nbsp;⏳ **Computing:** Whisper is transcribing chunk...")
        text = transcriber.transcribe(audio_chunk)
            
        if text.strip():
            # Update Live Session Text
            st.session_state.latest_transcript = text
            
            # Send through NLP Engine
            warnings = detector.analyze(text)
            
            st.session_state.logs.insert(0, {"text": text, "warnings": warnings})
            
            # Stacking Alerts Generation
            if warnings:
                for w in warnings:
                    st.session_state.alert_stack.insert(0, w)
                    # Trigger floating OS-level toast
                    icon = "🟡" if w['level'] in ['filler','warning'] else "🟠" if w['level'] == 'concern' else "🚨"
                    st.toast(w['message'], icon=icon)
                    
    except queue.Empty:
        pass
        
    time.sleep(0.3)
    st.rerun()
