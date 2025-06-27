# backend/app/core/config.py

import os

# --- LLM PROVIDER CONFIGURATION ---
# Choose your provider: "ollama" or "google"
LLM_PROVIDER = "google" # <--- CHANGE THIS TO SWITCH

# --- MODEL CONFIGURATION ---
# Models for Google
GEMINI_MODEL = "gemini-1.5-flash-latest"

# Models for Ollama
OLLAMA_LLM_MODEL = "llama3:8b"
OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"

# --- VECTOR STORE & DATA CONFIGURATION ---
# The directory where the persistent ChromaDB vector store will be saved.
CHROMA_PERSIST_DIR = "chroma_db"

# The directory containing the source documents to be ingested.
SOURCE_DATA_DIR = "data"