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
        print("ERROR (transcription.py): Whisper model not loaded.")
        return "Whisper model not loaded. Cannot transcribe."
        
    print(f"--- Transcribing audio file: {file_path} ---")
    
    try:
        result = whisper_model.transcribe(file_path, fp16=False)
        text = result.get("text", "").strip() # Ensure strip() is applied right away

        print(f"DEBUG (transcription.py): Raw Whisper result keys: {result.keys()}")
        print(f"DEBUG (transcription.py): Extracted text from Whisper: '{text[:100]}...'")
        
        return text
    except Exception as e:
        print(f"ERROR (transcription.py): Exception during Whisper transcription: {e}")
        import traceback
        traceback.print_exc()
        return f"Transcription failed due to internal Whisper error: {e}"