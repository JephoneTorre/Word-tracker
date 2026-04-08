import whisper
import warnings
import torch

class SpeechTranscriber:
    """
    Wraps the OpenAI Whisper model for converting audio chunks into text.
    """
    def __init__(self, model_size="base"):
        print(f"Loading Whisper model '{model_size}'...")
        # Load whisper. fp16 requires CUDA but will automatically fall back to fp32 if CPU.
        # We suppress warnings to keep console output clean.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.model = whisper.load_model(model_size)
        print("Whisper model loaded!")
    
    def transcribe(self, audio_data):
        """
        Transcribes a 16kHz float32 audio numpy array OR a local .wav file path.
        """
        if isinstance(audio_data, str):
            # It's a file path. Use soundfile avoiding whisper's ffmpeg shell commands
            import soundfile as sf
            import scipy.signal as sps
            import numpy as np
            
            try:
                # soundfile natively converts any bit-depth wav to normalized float64
                data, samplerate = sf.read(audio_data)
                
                # Convert to mono if it's stereo (2D array: samples x channels)
                if len(data.shape) > 1:
                    data = data.mean(axis=1)
                    
                # Whisper requires exactly 16000hz 
                if samplerate != 16000:
                    number_of_samples = round(len(data) * float(16000) / samplerate)
                    data = sps.resample(data, number_of_samples)
                    
                # Store back into audio_data as the expected float32 array
                audio_data = data.astype(np.float32)
            except Exception as e:
                raise ValueError(f"Failed to process WAV natively without ffmpeg: {str(e)}")

        # Using whisper's top level transcribe method
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = self.model.transcribe(
                audio_data, 
                fp16=torch.cuda.is_available(), 
                language="en",
                condition_on_previous_text=False # Prevent hallucination loops for isolated chunks
            )
            
        return result['text'].strip()
