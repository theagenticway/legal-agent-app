# backend/app/core/llm_factory.py

from langchain_ollama.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel

from . import config

def get_llm(temperature: float = 0) -> BaseChatModel:
    """
    Factory function to get the appropriate LLM based on the config.
    """
    if config.LLM_PROVIDER == "google":
        print("--- Using Google Gemini LLM ---")
        return ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            temperature=temperature,
            convert_system_message_to_human=True # Helps with some agent prompts
        )
    elif config.LLM_PROVIDER == "ollama":
        print("--- Using Ollama LLM ---")
        return ChatOllama(model=config.OLLAMA_LLM_MODEL, temperature=temperature)
    else:
        raise ValueError(f"Unsupported LLM provider: {config.LLM_PROVIDER}")

# Note: Embedding models can also be put behind a factory if you
# want to use Google's embeddings, but for now we will keep using
# the local Ollama embeddings to save on API costs.