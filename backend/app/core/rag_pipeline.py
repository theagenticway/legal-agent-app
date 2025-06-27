# backend/app/core/rag_pipeline.py

import os

# --- sqlite3 fix for ChromaDB ---
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
# ---

from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Import our configuration and our new factories
from . import config
from .llm_factory import get_llm, get_embedding_model

def get_vector_store() -> Chroma:
    """
    Initializes and returns a Chroma vector store using the factory for embeddings.
    """
    # Use the factory to get the embedding model
    embeddings = get_embedding_model()

    if os.path.exists(config.CHROMA_PERSIST_DIR):
        print(f"--- Loading existing vector store from {config.CHROMA_PERSIST_DIR} ---")
        vector_store = Chroma(
            persist_directory=config.CHROMA_PERSIST_DIR,
            embedding_function=embeddings
        )
    else:
        print(f"--- Creating new vector store from documents in {config.SOURCE_DATA_DIR} ---")
        loader = DirectoryLoader(config.SOURCE_DATA_DIR, glob="**/*.txt", loader_cls=TextLoader)
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        splits = text_splitter.split_documents(docs)
        print(f"Loaded and split {len(splits)} document chunks.")
        vector_store = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=config.CHROMA_PERSIST_DIR
        )
        print(f"--- Vector store created and persisted at {config.CHROMA_PERSIST_DIR} ---")
    return vector_store

def create_rag_chain():
    """
    Creates and returns a RAG chain using factories for both LLM and embeddings.
    """
    vector_store = get_vector_store()
    retriever = vector_store.as_retriever()

    prompt = ChatPromptTemplate.from_template("""
    You are an expert legal assistant. Answer the following question based only on the provided context.
    If you don't know the answer, just say that you don't know. Be concise and precise.

    Context:
    {context}

    Question:
    {question}
    """)

    # Use the factory to get the main LLM
    llm = get_llm()

    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    print("--- RAG chain created successfully ---")
    return chain