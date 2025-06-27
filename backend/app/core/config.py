# backend/app/core/config.py
import os

# --- LLM PROVIDER CONFIGURATION ---
LLM_PROVIDER = "google"

# --- MODEL CONFIGURATION ---
# Models for Google
GEMINI_MODEL = "gemini-1.5-flash-latest"
# Note: For now, we will use local embeddings even with Gemini to save on costs.
# In the future, you could add 
GOOGLE_EMBEDDING_MODEL = "models/embedding-001"

# Models for Ollama
OLLAMA_LLM_MODEL = "llama3:8b"
OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"

# --- ACTIVE MODEL CONFIGURATION ---
# This section sets the active models based on the provider chosen above.
# The rest of our application will only use these generic variables.

# For now, we will always use the local Ollama embeddings.
# EMBEDDING_MODEL = OLLAMA_EMBEDDING_MODEL # <-- THIS IS THE KEY CHANGE
EMBEDDING_MODEL = GOOGLE_EMBEDDING_MODEL # <-- THIS IS THE KEY CHANGE


# --- VECTOR STORE & DATA CONFIGURATION ---
CHROMA_PERSIST_DIR = "chroma_db"
SOURCE_DATA_DIR = "data"