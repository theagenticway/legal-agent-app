# backend/app/main.py

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
# Import List and Dict for type hinting
from typing import List, Optional, Dict, Any 
from langchain_core.messages import HumanMessage, AIMessage
from .core.agent import create_agent_executor
from .core.tools import case_intake_extractor
import shutil
from fastapi import UploadFile, File
from .core.transcription import transcribe_audio_file
from fastapi import Request
from .core.post_call_processor import process_call_transcript
# Import the database object and the table creation function
from .core.database import database, create_db_and_tables

# --- Call this function once at the top level ---
# This will create the 'cases' table if it doesn't exist
create_db_and_tables()

app = FastAPI(
    title="Legal Agent AI API",
    description="API for a legal agentic AI app using Ollama and RAG.",
    version="1.0.0",
)

# --- Define API routes FIRST ---
agent_executor = create_agent_executor()

# --- NEW, UNIFIED VAPI DATA MODELS ---

# Represents a single message in the conversation history, using the OpenAI format.
class VapiMessageOpenAI(BaseModel):
    role: str
    content: Optional[str] = None

# Represents the 'artifact' object, which contains the full transcript.
class VapiArtifact(BaseModel):
    messagesOpenAIFormatted: List[VapiMessageOpenAI]

# This is the main, flexible payload model that can handle different event types.
class VapiPayload(BaseModel):
    type: str
    status: Optional[str] = None
    endedReason: Optional[str] = None
    # The 'artifact' is only present in 'status-update' messages.
    artifact: Optional[VapiArtifact] = None 
    # The 'conversation' key is only present in 'conversation-update' messages.
    conversation: Optional[List[VapiMessageOpenAI]] = None
    # We can add other fields we see, but keep them optional.
    call: Optional[Dict[str, Any]] = None

# This is the top-level request object, which remains the same.
class VapiWebhookRequest(BaseModel):
    message: VapiPayload

# This is the Pydantic model for the /agent-query endpoint (from our web UI)
# Let's keep it here for clarity.
class Query(BaseModel):
    text: str
    history: List[Dict[str, Any]]

# In backend/app/main.py
# backend/app/main.py

# Add Request to your FastAPI imports
from fastapi import Request
import datetime

# ... other imports ...

# --- KEEP YOUR CORRECTED Pydantic models here, just comment them out for now ---
# In backend/app/main.py
# --- Add database connection event handlers ---
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# ... rest of your endpoints ...
@app.post("/api/vapi/agent-interaction")
async def handle_vapi_interaction(request: VapiWebhookRequest):
    """
    Handles all types of webhook events from Vapi.ai.
    It checks the message type and only acts on conversation updates.
    """
    message_payload = request.message

    # --- ROUTE 1: Handle a live conversation turn ---
    if message_payload.type == "conversation-update" and message_payload.conversation:
        
        conversation_history = message_payload.conversation
        last_message = conversation_history[-1] if conversation_history else None

        if last_message and last_message.role == "user":
            user_input = last_message.content
            print(f"--- Live Turn Received: {user_input} ---")

            # Convert Vapi's history to LangChain's format
            langchain_history = []
            for msg in conversation_history[:-1]:
                if msg.role == "user":
                    langchain_history.append(HumanMessage(content=msg.content))
                # Vapi uses 'assistant' or 'bot', LangChain expects 'ai'
                elif msg.role in ["assistant", "bot"]:
                    langchain_history.append(AIMessage(content=msg.content))
            
            # Invoke the agent
            agent_response = agent_executor.invoke({
                "input": user_input,
                "chat_history": langchain_history
            })
            
            agent_text_output = agent_response.get("output", "I had a problem processing that.")
            print(f"--- Agent Response: {agent_text_output} ---")
            
            # Return the response for Vapi to speak
            return {"message": agent_text_output}

    # --- ROUTE 2: Handle the end-of-call summary ---
    elif message_payload.type == "status-update" and message_payload.status == "ended":
        print(f"--- Call Ended. Reason: {message_payload.endedReason} ---")
         # Check if the artifact with the transcript exists
        if message_payload.artifact and message_payload.artifact.messagesOpenAIFormatted:
            
            # Correctly assign the transcript to a variable
            final_transcript = message_payload.artifact.messagesOpenAIFormatted
            
            # Call our processing service with the correct variable
            await process_call_transcript(final_transcript)
            print("--- Final Transcript Received ---")
            # print(full_transcript)
        # It's important to return an empty JSON here, not an error.
        return {}

    # --- Default Route: Ignore other event types ---
    else:
        print(f"--- Ignoring Vapi event of type: {message_payload.type} ---")
        return {}
# ... rest of your file ...



@app.post("/agent-query")
async def perform_agent_query(query: Query):
    """
    Accepts a query and passes it to the agent executor for processing.
    """
    print(f"Received query for agent: {query.text}")
    chat_history = []
    for message in query.history:
        if message.get("role") == "human":
            chat_history.append(HumanMessage(content=message.get("content")))
        elif message.get("role") == "ai":
            chat_history.append(AIMessage(content=message.get("content")))

    # --- Pass the history to the agent ---
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
# --- Add this new endpoint ---
@app.post("/transcribe-audio")
async def handle_audio_transcription(audio_file: UploadFile = File(...)):
    """
    Accepts an audio file, saves it temporarily, transcribes it,
    and returns the text.
    """
    # Create a temporary path to save the uploaded file
    temp_file_path = f"temp_{audio_file.filename}"
    
    try:
        # Save the uploaded file to the temporary path
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        
        # Call our transcription service
        transcribed_text = transcribe_audio_file(temp_file_path)
        
        return {"text": transcribed_text}
        
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}
        
    finally:
        # Clean up the temporary file
        import os
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
# --- Mount the static files LAST ---
# This is a "catch-all" route, so it should be at the end.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")