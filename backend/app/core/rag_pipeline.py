# backend/app/core/rag_pipeline.py

# --- sqlite3 fix for ChromaDB ---
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
# ---

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_ollama.chat_models import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# NOTE: This is a simplified, naive implementation.
# The vector store is created in memory every time the function is called.
# In Module 2, we will persist this to disk.
def create_rag_chain():
    """
    Creates and returns a RAG chain.
    The chain is built from documents in the './data' directory.
    """
    print("--- Creating RAG chain ---")

    # 1. Load documents
    loader = TextLoader("./data/sample_contract.txt")
    docs = loader.load()

    # 2. Split documents
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    splits = text_splitter.split_documents(docs)

    # 3. Create vector store
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)

    # 4. Create retriever
    retriever = vectorstore.as_retriever()

    # 5. Create prompt template
    prompt = ChatPromptTemplate.from_template("""
    You are an expert legal assistant. Answer the following question based only on the provided context.
    If you don't know the answer, just say that you don't know. Be concise and precise.

    Context:
    {context}

    Question:
    {question}
    """)

    # 6. Define the LLM
    llm = ChatOllama(model="llama3:8b")

    # 7. Build the chain
    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    print("--- RAG chain created successfully ---")
    return chain