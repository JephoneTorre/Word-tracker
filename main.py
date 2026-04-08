import threading
import time
from audio_capture import AudioChunker
from transcriber import SpeechTranscriber
from nlp_analyzer import RepetitionDetector
import queue

def main():
    print("="*60)
    print("🎙️ Real-time Speech Repetition Coach (CLI Version)")
    print("="*60)
    print("Initializing components, this may take a moment...")
    
    # Initialize Core Components
    # You can change model_size to "small", "medium", or "large" for better accuracy.
    transcriber = SpeechTranscriber(model_size="base")
    detector = RepetitionDetector(window_size=15)
    
    # Adjust energy_threshold depending on how loud your environment/mic is.
    # Defaulting to 0.015, if it misses speech, decrease it e.g. 0.005. 
    # If it triggers on noise, increase it e.g. 0.05.
    chunker = AudioChunker(samplerate=16000, energy_threshold=0.015, silence_duration=1.0)
    
    print("\n[READY] Listening for speech... (Press Ctrl+C to stop)")
    
    chunker.start()
    
    try:
        while True:
            # Wait for audio chunk from the queue (Blocking)
            # The background thread running 'sounddevice' fills this queue
            try:
                audio_chunk = chunker.q.get(timeout=1.0)
            except queue.Empty:
                continue # Allows KeyboardInterrupt to be processed
                
            # Transcribe the incoming chunk
            text = transcriber.transcribe(audio_chunk)
            
            if text.strip():
                print(f"\n[Transcript]: {text}")
                
                # Analyze text via NLP module
                warnings = detector.analyze(text)
                
                # Output warnings beautifully
                for w in warnings:
                    # ANSI escape code \033[93m for yellow, \033[0m to reset
                    print(f"  \033[93m⚠️ {w}\033[0m")
            else:
                # Can be background noise interpreted as speech
                pass
                
    except KeyboardInterrupt:
        print("\n\nStopping application...")
    finally:
        chunker.stop()
        print("Goodbye!")

if __name__ == "__main__":
    main()
