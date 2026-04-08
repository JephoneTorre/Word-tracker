import sounddevice as sd
import numpy as np
import queue
import sys

class AudioChunker:
    """
    Captures raw audio from microphone using sounddevice
    and groups it into chunks based on Voice Activity Detection (VAD) via energy threshold.
    """
    def __init__(self, samplerate=16000, channels=1, energy_threshold=0.015, silence_duration=1.0):
        self.samplerate = samplerate
        self.channels = channels
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        
        self.q = queue.Queue()
        self.audio_buffer = []
        self.is_speaking = False
        self.silence_frames = 0
        self.silence_threshold_frames = int(samplerate * silence_duration)
        self.stream = None
        
    def callback(self, indata, frames, time, status):
        """
        Callback invoked by sounddevice for every audio block.
        """
        if status:
            print(f"Status: {status}", file=sys.stderr)
            
        # Flatten to 1D array of float32
        data = indata.flatten()
        
        # Calculate RMS energy for VAD
        energy = np.mean(np.abs(data))
        
        if energy > self.energy_threshold:
            if not self.is_speaking:
                self.is_speaking = True
                print("🎙️ Speech detected...", end='\r')
                
            self.audio_buffer.extend(data)
            self.silence_frames = 0
        else:
            if self.is_speaking:
                self.audio_buffer.extend(data)
                self.silence_frames += frames
                if self.silence_frames > self.silence_threshold_frames:
                    self.is_speaking = False
                    print("🛑 Silence detected. Processing chunk...  ")
                    
                    # Emit chunk into the queue
                    chunk = np.array(self.audio_buffer, dtype=np.float32)
                    self.q.put(chunk)
                    
                    # Reset buffer and frames
                    self.audio_buffer = []
                    self.silence_frames = 0
                    
    def start(self):
        """Starts the audio input stream."""
        # Ensure only single stream runs
        if self.stream is not None:
            self.stop()
            
        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            callback=self.callback,
            dtype='float32'
        )
        self.stream.start()
        
    def stop(self):
        """Stops the audio input stream."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
