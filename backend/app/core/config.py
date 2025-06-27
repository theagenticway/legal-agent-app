# backend/app/core/config.py

# The directory where the persistent ChromaDB vector store will be saved.
CHROMA_PERSIST_DIR = "chroma_db"

# The directory containing the source documents to be ingested.
SOURCE_DATA_DIR = "data"

# The embedding model to use.
EMBEDDING_MODEL = "nomic-embed-text"

# The LLM to use for the RAG chain.
LLM_MODEL = "llama3:8b"