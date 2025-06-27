# backend/app/main.py

from fastapi import FastAPI
from pydantic import BaseModel
from .core.rag_pipeline import create_rag_chain

# Initialize the FastAPI app
app = FastAPI(
    title="Legal Agent AI API",
    description="API for a legal agentic AI app using Ollama and RAG.",
    version="1.0.0",
)

# Create the RAG chain on startup.
# This makes it so we don't have to rebuild it for every request.
# NOTE: This is still a temporary solution. We will improve this in Module 2.
rag_chain = create_rag_chain()

# Define the request model for our endpoint using Pydantic
class Query(BaseModel):
    text: str

# Define our first API endpoint
@app.post("/legal-research")
async def perform_legal_research(query: Query):
    """
    Accepts a legal query and returns the answer from the RAG chain.
    """
    print(f"Received query: {query.text}")
    
    # Use the pre-loaded RAG chain to get an answer
    response = rag_chain.invoke(query.text)
    
    return {"answer": response}

# A simple root endpoint to confirm the server is running
@app.get("/")
def read_root():
    return {"status": "Legal Agent AI API is running"}