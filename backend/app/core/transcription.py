# backend/app/core/transcription.py

from whisper_cpp_python import Whisper

# Initialize the Whisper model. This will download the model weights
# the first time it's run. We'll use the small, English-only model
# for a good balance of speed and accuracy.
print("--- Initializing Whisper STT model ---")
whisper_model = Whisper(model_path="small.en")
print("--- Whisper STT model initialized ---")


def transcribe_audio_file(file_path: str) -> str:
    """
    Transcribes the audio file at the given path using the Whisper model.
    
    Args:
        file_path: The path to the audio file.
    
    Returns:
        The transcribed text.
    """
    print(f"--- Transcribing audio file: {file_path} ---")
    
    # The .transcribe() method does all the work.
    result = whisper_model.transcribe(file_path)
    
    # The result is a dictionary; we want the 'text' key.
    text = result.get("text", "")
    
    print("--- Transcription complete ---")
    return text.strip()