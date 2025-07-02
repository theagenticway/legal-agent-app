# backend/app/main.py

from dotenv import load_dotenv
load_dotenv()
import os
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
# Import List and Dict for type hinting
from typing import List, Optional, Dict, Any 
from langchain_core.messages import HumanMessage, AIMessage
from .core.agent import create_agent_executor
from .core.tools import case_intake_extractor
import shutil

from .core.transcription import transcribe_audio_file

from .core.post_call_processor import process_call_transcript
# Import the database object and the table creation function
from .core.database import database, cases, create_db_and_tables
from sqlalchemy import select
from .core.rag_pipeline import get_vector_store # Import get_vector_store
from langchain_community.document_loaders import TextLoader, PyPDFLoader # For loading documents
from langchain_text_splitters import RecursiveCharacterTextSplitter # For splitting
# --- NEW IMPORT ---
from .core.database import indexed_rag_documents # Import the new table object
from .core.tools import database_case_reader_async # NEW: Import the async tool

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
                # --- NEW: Retrieve and Inject Caller-Specific Context ---
            caller_context_message = ""
            if caller_phone_number != "Unknown":
                try:
                    # Use the async database reader tool directly to get client data
                    # This is efficient because it avoids an extra agent "tool-use" step
                    # if the data is critical for every turn.
                    client_data = await database_case_reader_async(caller_phone_number)
                    if client_data:
                        caller_context_message = f"Here is relevant information about the current caller ({caller_phone_number}) from your internal database:\n{client_data}"
                        print(f"🔍 Injected caller context:\n{caller_context_message[:200]}...")
                    else:
                        caller_context_message = f"No existing case information found for caller {caller_phone_number}."
                        print(f"🔍 No context found for caller {caller_phone_number}.")
                except Exception as e:
                    print(f"⚠️ Error retrieving caller context: {e}")
                    caller_context_message = "An error occurred while retrieving caller information from the database."
            
            # Add the caller context as a SystemMessage at the very beginning
            if caller_context_message:
                langchain_history.append(SystemMessage(content=caller_context_message))
            # --- END NEW ---
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
# --- NEW ENDPOINT: Process RAG Documents ---
@app.post("/process-rag-documents")
async def process_rag_documents(documents: List[UploadFile] = File(...)):
    if not documents:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    processed_count = 0
    temp_files = []
    processed_filenames = [] # To track successfully processed files
    try:
        all_splits = []
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)

        for doc_file in documents:
            filename_original = doc_file.filename # Store original filename
            temp_file_path = f"temp_rag_doc_{doc_file.filename}"
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(doc_file.file, buffer)
            temp_files.append(temp_file_path)

            loader = None
            file_extension = os.path.splitext(doc_file.filename)[1].lower()

            if file_extension == '.txt':
                loader = TextLoader(temp_file_path)
            elif file_extension == '.pdf':
                loader = PyPDFLoader(temp_file_path)
            else:
                print(f"Skipping unsupported file type: {doc_file.filename}")
                continue

            if loader:
                try:
                    docs = loader.load()
                    splits = text_splitter.split_documents(docs)
                    # --- CRITICAL CHANGE: Add 'original_filename' metadata to each split ---
                    for split in splits:
                        split.metadata["original_filename"] = filename_original
                    # --- END CRITICAL CHANGE ---
                    all_splits.extend(splits)
                    processed_count += 1
                    print(f"Processed file: {doc_file.filename} with {len(splits)} chunks.")
                    processed_filenames.append({
                        "filename": doc_file.filename,
                        "num_chunks": len(splits)
                    }) # Store info for DB insert
                except Exception as e:
                    print(f"Error loading {doc_file.filename}: {e}")
                    continue

        if not all_splits:
            raise HTTPException(status_code=400, detail="No valid content found in uploaded files or all files were unsupported types.")

        vector_store = get_vector_store()
        vector_store.add_documents(all_splits)
        # vector_store.persist() # Removed this earlier, keep it removed

        # --- NEW: Insert metadata into PostgreSQL ---
        for file_info in processed_filenames:
            insert_query = indexed_rag_documents.insert().values(
                filename=file_info["filename"],
                num_chunks=file_info["num_chunks"],
                # indexed_at defaults to now()
            )
            await database.execute(insert_query)
        print(f"Successfully recorded metadata for {len(processed_filenames)} files in DB.")
        # --- END NEW ---

        message = f"Successfully processed {processed_count} file(s) and added {len(all_splits)} chunks to the RAG knowledge base."
        print(message)
        return {"message": message}

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Exception during RAG document processing: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred during document processing: {str(e)}")
    finally:
        for fpath in temp_files:
            if os.path.exists(fpath):
                os.remove(fpath)

# --- NEW ENDPOINT: Get Indexed RAG Documents ---
@app.get("/api/rag-documents")
async def get_rag_documents():
    """
    Fetches a list of documents currently indexed in the RAG system (from DB metadata).
    """
    print("--- Fetching indexed RAG documents from the database ---")
    try:
        query = select(indexed_rag_documents.c.id, indexed_rag_documents.c.filename,
                       indexed_rag_documents.c.num_chunks, indexed_rag_documents.c.indexed_at)
        docs = await database.fetch_all(query)
        return [dict(doc) for doc in docs]
    except Exception as e:
        print(f"Error fetching RAG documents: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch indexed RAG documents")
    # --- NEW ENDPOINT: Delete RAG Document ---
@app.delete("/api/rag-documents/{filename:path}") # Using path converter for filename with dots/slashes
async def delete_rag_document(filename: str):
    """
    Deletes a document and its associated chunks from the RAG system (ChromaDB)
    and removes its metadata from the database.
    """
    print(f"--- Attempting to delete document: {filename} ---")
    
    if not filename:
        raise HTTPException(status_code=400, detail="Filename must be provided for deletion.")

    try:
        # 1. Delete from ChromaDB using metadata filter
        vector_store = get_vector_store()
        
        # NOTE: Chroma's delete method accepts a 'where' clause for metadata.
        # The key in 'where' must match the metadata key stored in Chroma.
        # We stored it as 'original_filename'.
        delete_from_chroma_result = vector_store.delete(where={"original_filename": filename})
        print(f"DEBUG: ChromaDB deletion result for {filename}: {delete_from_chroma_result}")

        # 2. Delete from PostgreSQL metadata table
        delete_from_db_query = indexed_rag_documents.delete().where(indexed_rag_documents.c.filename == filename)
        await database.execute(delete_from_db_query)
        
        print(f"Successfully deleted {filename} from ChromaDB and PostgreSQL metadata.")
        return {"message": f"Document '{filename}' successfully removed from RAG system."}

    except Exception as e:
        print(f"ERROR: Exception during RAG document deletion for {filename}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to delete document '{filename}': {str(e)}")
# --- Static Files Mounting ---
# --- Mount the static files LAST ---
# This is a "catch-all" route, so it should be at the end.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")