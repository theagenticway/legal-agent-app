# backend/app/main.py
from dotenv import load_dotenv
load_dotenv() # This line reads the .env file and loads the variables
from fastapi import FastAPI
from pydantic import BaseModel
# Import our new agent creator function
from .core.agent import create_agent_executor
from langchain_core.messages import HumanMessage, AIMessage

app = FastAPI(
    title="Legal Agent AI API",
    description="API for a legal agentic AI app using Ollama and RAG.",
    version="1.0.0",
)

# On startup, create the agent executor instead of the RAG chain
agent_executor = create_agent_executor()

class Query(BaseModel):
    text: str


@app.post("/agent-query")
async def perform_agent_query(query: Query):
    """
    Accepts a query and passes it to the agent executor for processing.
    """
    print(f"Received query for agent: {query.text}")

    # For now, we'll use an empty chat history for each request.
    # In a real app, you would fetch this from a database.
    chat_history = [] 

    # The agent executor expects a dictionary with "input" and "chat_history".
    response = agent_executor.invoke({
        "input": query.text,
        "chat_history": chat_history
    })
    
    # The agent's final answer is in the "output" key of the response dictionary.
    return {"answer": response["output"]}
@app.get("/")
def read_root():
    return {"status": "Legal Agent AI API is running"}