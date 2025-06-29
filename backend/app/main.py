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
from .core.database import database, cases, create_db_and_tables
from sqlalchemy import select

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
from datetime import datetime, timezone

# ... other imports ...

# --- KEEP YOUR CORRECTED Pydantic models here, just comment them out for now ---
# In backend/app/main.py
# --- Add database connection event handlers ---
@app.on_event("startup")
async def startup():
    try:
        await database.connect()
        print("✅ Database connected successfully")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Add these endpoints to your main.py for basic health checks

@app.get("/debug/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/debug/llm-test")
async def test_llm():
    """Test LLM connectivity"""
    try:
        from backend.app.core.llm_factory import get_llm
        llm = get_llm()
        response = llm.invoke("Say 'Hello World'")
        return {
            "status": "success",
            "response": response.content,
            "llm_type": type(llm).__name__
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

@app.get("/debug/database-test")
async def test_database():
    """Test database connectivity"""
    try:
        from backend.app.core.database import database
        # Simple query to test connection
        query = "SELECT 1 as test"
        result = await database.fetch_one(query)
        return {
            "status": "success",
            "result": dict(result) if result else None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

@app.get("/debug/tools-test")
async def test_tools():
    """Test individual tools"""
    results = {}
    
    # Test Legal Document Retriever
    try:
        from backend.app.core.tools import legal_document_retriever
        result = legal_document_retriever("test query")
        results["legal_doc_retriever"] = {"status": "success", "result_length": len(str(result))}
    except Exception as e:
        results["legal_doc_retriever"] = {"status": "error", "error": str(e)}
    
    # Test Case Intake Extractor
    try:
        from backend.app.core.tools import case_intake_extractor
        result = case_intake_extractor("Client John Doe has a contract dispute with ABC Corp.")
        results["case_intake_extractor"] = {"status": "success", "result": result}
    except Exception as e:
        results["case_intake_extractor"] = {"status": "error", "error": str(e)}
    
    return results
# ... rest of your endpoints ...
# @app.post("/api/vapi/agent-interaction")


# @app.post("/api/vapi/agent-interaction")

@app.post("/api/vapi/agent-interaction")
async def handle_vapi_interaction(request: VapiWebhookRequest):
    """
    Enhanced debug version of webhook handler
    """
    print(f"\n🔔 === WEBHOOK RECEIVED ===")
    print(f"📋 Message Type: {request.message.type}")
    print(f"📋 Message Status: {getattr(request.message, 'status', 'N/A')}")
    
    try:
        message_payload = request.message
        
        # Log the full payload structure for debugging
        print(f"📦 Payload keys: {list(message_payload.__dict__.keys())}")

        # --- ROUTE 1: Handle a live conversation turn ---
        if message_payload.type == "conversation-update":
            print("📞 Processing conversation-update...")
            
            if not message_payload.conversation:
                print("❌ No conversation data in payload")
                return {"message": "No conversation data received"}
            
            conversation_history = message_payload.conversation
            print(f"📚 Conversation length: {len(conversation_history)}")
            
            # Log all messages in conversation
            for i, msg in enumerate(conversation_history):
                print(f"  Message {i+1}: {msg.role} -> {msg.content[:50] if msg.content else 'None'}...")
            
            last_message = conversation_history[-1] if conversation_history else None
            
            if not last_message:
                print("❌ No last message found")
                return {"message": "No message to process"}
                
            print(f"📝 Last message role: {last_message.role}")
            print(f"📝 Last message content: {last_message.content}")

            if last_message.role == "user":
                user_input = last_message.content
                
                if not user_input or user_input.strip() == "":
                    print("❌ Empty user input")
                    return {"message": "I didn't receive any message content"}
                
                # Get caller info
                caller_phone_number = "Unknown"
                if message_payload.call and message_payload.call.get("customer"):
                    caller_phone_number = message_payload.call.get("customer").get("number", "Unknown")
                
                print(f"📱 Caller: {caller_phone_number}")
                print(f"👤 User input: '{user_input}'")

                # Build chat history (exclude the last message as it's the current input)
                langchain_history = []
                for msg in conversation_history[:-1]:  # Exclude last message
                    if msg.role == "user":
                        langchain_history.append(HumanMessage(content=msg.content or ""))
                    elif msg.role in ["assistant", "bot"]:
                        langchain_history.append(AIMessage(content=msg.content or ""))
                
                print(f"📚 Built chat history with {len(langchain_history)} messages")
                
                # Prepare agent input
                agent_input = f"A user from phone number {caller_phone_number} says: {user_input}"
                print(f"🤖 Prepared agent input: '{agent_input}'")
                
                try:
                    print("🚀 About to invoke agent executor...")
                    print(f"🚀 Agent executor type: {type(agent_executor)}")
                    print(f"🚀 Agent executor verbose: {agent_executor.verbose}")
                    
                    # Use async version consistently
                    agent_response = await agent_executor.ainvoke({
                        "input": agent_input,
                        "chat_history": langchain_history
                    })
                    
                    print(f"✅ Agent response received!")
                    print(f"📤 Response type: {type(agent_response)}")
                    print(f"📤 Response keys: {list(agent_response.keys()) if isinstance(agent_response, dict) else 'Not a dict'}")
                    
                    if isinstance(agent_response, dict):
                        agent_text_output = agent_response.get("output", "I'm sorry, something went wrong.")
                        print(f"💬 Extracted output: '{agent_text_output}'")
                    else:
                        agent_text_output = str(agent_response)
                        print(f"💬 Converted to string: '{agent_text_output}'")
                    
                    print(f"📤 Returning to Vapi: '{agent_text_output}'")
                    return {"message": agent_text_output}
                    
                except Exception as agent_error:
                    print(f"❌ AGENT EXECUTION ERROR: {type(agent_error).__name__}")
                    print(f"❌ Error message: {str(agent_error)}")
                    import traceback
                    print("❌ Full traceback:")
                    traceback.print_exc()
                    
                    return {"message": "I apologize, but I encountered an issue processing your request. Please try again."}
            else:
                print(f"⏭️ Skipping non-user message (role: {last_message.role})")
                return {}

        # --- ROUTE 2: Handle the end-of-call summary ---
        elif message_payload.type == "status-update" and message_payload.status == "ended":
            print(f"📞 Call ended. Reason: {message_payload.endedReason}")
            
            if message_payload.artifact and message_payload.artifact.messagesOpenAIFormatted:
                final_transcript = message_payload.artifact.messagesOpenAIFormatted
                
                caller_phone_number = "Unknown"
                vapi_call_id = None
                
                if message_payload.call:
                    vapi_call_id = message_payload.call.get("id")
                    if message_payload.call.get("customer"):
                        caller_phone_number = message_payload.call.get("customer").get("number", "Unknown")

                print(f"📋 Processing end-of-call for {caller_phone_number}, call ID: {vapi_call_id}")
                await process_call_transcript(final_transcript, caller_phone_number, vapi_call_id)
            else:
                print("❌ No final transcript artifact found in end-of-call payload")

        # --- Default Route: Log and ignore other event types ---
        else:
            event_type = message_payload.type if message_payload else "Unknown"
            status = getattr(message_payload, 'status', 'N/A')
            print(f"🔇 Ignoring event - Type: {event_type}, Status: {status}")

        print("✅ Webhook processing complete")
        return {}
        
    except Exception as e:
        print(f"💥 WEBHOOK PROCESSING ERROR: {type(e).__name__}")
        print(f"💥 Error message: {str(e)}")
        import traceback
        print("💥 Full traceback:")
        traceback.print_exc()
        return {"error": "Internal server error"}
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
    response = await agent_executor.ainvoke({
        "input": query.text,
        "chat_history": chat_history
    })
     # --- ADD THIS DEBUG PRINT ---
    print(f"DEBUG: AgentExecutor ainvoke raw response: {response}")
    print(f"DEBUG: AgentExecutor output sent to frontend: {response.get('output', 'N/A')}")
    # --- END DEBUG PRINT ---

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
        print(f"DEBUG (main.py): Calling transcribe_audio_file for {temp_file_path}")
        # Call our transcription service
        transcribed_text = transcribe_audio_file(temp_file_path)
        print(f"DEBUG (main.py): Transcribed text received: '{transcribed_text[:100]}...' (Type: {type(transcribed_text)})")
        return {"text": transcribed_text}
        
    # Ensure that transcribed_text is indeed a string. If it's empty, send an appropriate message.
        if not isinstance(transcribed_text, str):
            print(f"ERROR (main.py): transcribe_audio_file returned non-string: {transcribed_text}")
            return {"error": "Transcription failed: Invalid output format from transcriber."}
        if not transcribed_text.strip(): # Check if it's empty or just whitespace
            print(f"WARNING (main.py): Transcribed text is empty for {audio_file.filename}")
            # You might want to return an error, or a default message
            return {"text": "No speech detected or transcription failed for the provided audio."}

        return {"text": transcribed_text}
        
    except Exception as e:
        print(f"ERROR (main.py): Exception during transcription: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"An error occurred during transcription: {str(e)}"}
        
    finally:
        # Clean up the temporary file
        import os
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

# --- ADD THIS NEW ENDPOINT ---
@app.get("/api/cases")
async def get_all_cases():
    """
    Fetches all case records from the database.
    """
    print("--- Fetching all cases from the database ---")
    try:
        query = select(cases)
        all_cases = await database.fetch_all(query)
        # Convert the list of RowProxy objects to a list of dictionaries
        return [dict(case) for case in all_cases]
    except Exception as e:
        print(f"Error fetching cases: {e}")
        # Use FastAPI's error handling in a real app
        return {"error": "Could not fetch cases"}

# --- Mount the static files LAST ---
# This is a "catch-all" route, so it should be at the end.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")