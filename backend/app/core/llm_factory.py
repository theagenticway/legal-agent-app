# backend/app/core/llm_factory.py

from langchain_ollama.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings

from . import config

def get_llm(temperature: float = 0.5) -> BaseChatModel:
    """
    Factory function to get the appropriate Chat LLM based on the config.
    """
    if config.LLM_PROVIDER == "google":
        print("--- Using Google Gemini LLM ---")
        return ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            temperature=temperature,
            # convert_system_message_to_human=True
        )
    elif config.LLM_PROVIDER == "ollama":
        print("--- Using Ollama LLM ---")
        return ChatOllama(model=config.OLLAMA_LLM_MODEL, temperature=temperature)
    else:
        raise ValueError(f"Unsupported LLM provider: {config.LLM_PROVIDER}")

def get_embedding_model() -> Embeddings:
    """
    Factory function to get the appropriate embedding model based on the config.
    """
    if config.EMBEDDING_PROVIDER == "google":
        print("--- Using Google Embeddings ---")
        return GoogleGenerativeAIEmbeddings(model=config.EMBEDDING_MODEL)
    elif config.EMBEDDING_PROVIDER == "ollama":
        print("--- Using local Ollama Embeddings ---")
        return OllamaEmbeddings(model=config.EMBEDDING_MODEL)
    else:
        raise ValueError(f"Unsupported Embedding provider: {config.EMBEDDING_PROVIDER}")