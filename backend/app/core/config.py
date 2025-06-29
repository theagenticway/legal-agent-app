# backend/app/core/config.py
import os

# --- PROVIDER CONFIGURATION ---
# Choose your providers: "ollama" or "google"
LLM_PROVIDER = "google"
EMBEDDING_PROVIDER = "google" # <-- NEW: Set this to "google"

# --- MODEL CONFIGURATION (Provider-specific) ---
# Models for Google
GEMINI_MODEL = "gemini-2.5-flash"
GOOGLE_EMBEDDING_MODEL = "models/embedding-001" # The standard Google embedding model

# Models for Ollama
OLLAMA_LLM_MODEL = "llama3:8b"
OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"

# --- ACTIVE EMBEDDING MODEL ---
# This section sets the active embedding model based on the provider chosen above.
# The rest of our application will only use this generic variable.
if EMBEDDING_PROVIDER == "google":
    EMBEDDING_MODEL = GOOGLE_EMBEDDING_MODEL
else:
    EMBEDDING_MODEL = OLLAMA_EMBEDDING_MODEL

# --- VECTOR STORE & DATA CONFIGURATION ---
CHROMA_PERSIST_DIR = "chroma_db"
SOURCE_DATA_DIR = "data"