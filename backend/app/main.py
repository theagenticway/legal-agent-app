# backend/app/main.py

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from .core.agent import create_agent_executor
from .core.tools import case_intake_extractor

app = FastAPI(
    title="Legal Agent AI API",
    description="API for a legal agentic AI app using Ollama and RAG.",
    version="1.0.0",
)

# --- Define API routes FIRST ---
agent_executor = create_agent_executor()

class Query(BaseModel):
    text: str

@app.post("/agent-query")
async def perform_agent_query(query: Query):
    """
    Accepts a query and passes it to the agent executor for processing.
    """
    print(f"Received query for agent: {query.text}")
    chat_history = []
    response = agent_executor.invoke({
        "input": query.text,
        "chat_history": chat_history
    })
    return {"answer": response["output"]}
# --- Add this new endpoint ---
class IntakeRequest(BaseModel):
    text: str

@app.post("/case-intake")
async def process_case_intake(request: IntakeRequest):
    """
    Accepts unstructured text and returns a structured case file.
    This endpoint uses the Case Intake Extractor tool directly.
    """
    print(f"Received case intake request with text: {request.text[:100]}...")
    
    # We call the function directly, bypassing the agent for this specific task
    extracted_data = case_intake_extractor(request.text)
    
    # In a real app, you would now save this 'extracted_data' to your database.
    # For now, we'll just return it.
    print(f"--- Extracted Data --- \n{extracted_data}")
    
    return extracted_data

# --- Mount the static files LAST ---
# This is a "catch-all" route, so it should be at the end.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")