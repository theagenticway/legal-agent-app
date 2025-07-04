# --- Start of new code for sqlite3 fix ---
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
# --- End of new code for sqlite3 fix ---


# THIS IS THE CORRECTED IMPORT SECTION
from langchain_ollama.chat_models import ChatOllama
from langchain_ollama.embeddings import OllamaEmbeddings

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


# 1. Load the document
print("--- Loading document ---")
loader = TextLoader("./data/sample_contract.txt")
docs = loader.load()

# 2. Split the document into chunks
print("--- Splitting document into chunks ---")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
splits = text_splitter.split_documents(docs)

# 3. Create Ollama embeddings and store in ChromaDB
print("--- Creating embeddings and storing in ChromaDB ---")
embeddings = OllamaEmbeddings(model="nomic-embed-text")
vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)

# 4. Define the RAG chain
print("--- Defining RAG chain ---")

# THIS IS THE CORRECTED CLASS NAME
# Define our LLM using the ChatOllama class
llm = ChatOllama(model="phi4-mini:3.8b")

# Retrieve and generate using the relevant snippets of the document
retriever = vectorstore.as_retriever()
prompt = ChatPromptTemplate.from_template("""
You are an expert legal assistant. Answer the following question based only on the provided context.
If you don't know the answer, just say that you don't know.

Context:
{context}

Question:
{question}
""")

chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# 5. Ask a question
print("--- Asking a question to the RAG chain ---")
question = "What is the monthly retainer fee and which state's law governs this agreement?"
response = chain.invoke(question)

print("\n--- RESPONSE ---")
print(response)
print("\n--- RAG setup test complete! ---")