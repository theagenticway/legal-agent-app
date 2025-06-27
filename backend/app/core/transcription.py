# backend/app/core/transcription.py

import whisper

# Initialize the Whisper model. This will download the model weights
# the first time it's run. We'll use the 'small.en' model.
# The 'load_model' function handles everything.
print("--- Initializing Whisper STT model (openai-whisper) ---")
try:
    # The model is downloaded to ~/.cache/whisper
    whisper_model = whisper.load_model("small.en")
    print("--- Whisper STT model initialized ---")
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    whisper_model = None


def transcribe_audio_file(file_path: str) -> str:
    """
    Transcribes the audio file at the given path using the Whisper model.
    
    Args:
        file_path: The path to the audio file.
    
    Returns:
        The transcribed text.
    """
    if not whisper_model:
        return "Whisper model not loaded. Cannot transcribe."
        
    print(f"--- Transcribing audio file: {file_path} ---")
    
    # The .transcribe() method from this library is even simpler.
    result = whisper_model.transcribe(file_path, fp16=False) # fp16=False for CPU
    
    # The result dictionary contains the 'text' key.
    text = result.get("text", "")
    
    print("--- Transcription complete ---")
    return text.strip()