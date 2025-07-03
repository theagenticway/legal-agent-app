# backend/app/main.py

from dotenv import load_dotenv
load_dotenv()
import os
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage # Added SystemMessage
from .core.agent import create_agent_executor
from .core.tools import case_intake_extractor
import shutil
import uuid
from .core.transcription import transcribe_audio_file
from .core.post_call_processor import process_call_transcript

# Import ALL database objects needed from your updated database.py
from .core.database import (
    database,
    cases,
    indexed_rag_documents,
    clients,        # NEW
    contracts,      # NEW
    activities,     # NEW
    tasks,          # NEW
    notifications,  # NEW
    create_db_and_tables
)
from sqlalchemy import select, func # Added func for counts, and updated select
from .core.rag_pipeline import get_vector_store
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Import ALL schemas needed from your updated schemas.py
from .core.schemas import (
    VapiMessageOpenAI,
    VapiArtifact,
    VapiPayload,
    VapiWebhookRequest,
    CaseIntake,
    OverviewCounts,     # NEW
    RecentActivity,     # NEW
    UpcomingDeadline,   # NEW
    Notification,       # NEW
    DashboardData       # NEW (though not used directly as a response model for one endpoint yet)
)

from datetime import datetime, timezone, timedelta # Added timedelta
from .core.tools import database_case_reader_async # Import the async tool


# --- Call this function once at the top level ---
# This will create all defined tables if they don't exist
create_db_and_tables()

app = FastAPI(
    title="Legal Agent AI API",
    description="API for a legal agentic AI app using Ollama and RAG.",
    version="1.0.0",
)

# --- Define API routes FIRST ---
agent_executor = create_agent_executor()

# --- Pydantic models for specific endpoints (Query, IntakeRequest) ---
class Query(BaseModel):
    text: str
    history: List[Dict[str, Any]]

class IntakeRequest(BaseModel):
    text: str

# --- Add database connection event handlers ---
@app.on_event("startup")
async def startup():
    try:
        await database.connect()
        print("✅ Database connected successfully")
        # --- Add initial sample data if DB is empty for dashboard testing ---
        await insert_sample_dashboard_data()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# --- NEW: Function to insert sample data for dashboard ---
async def insert_sample_dashboard_data():
    # Check if data exists before inserting to avoid duplicates on reload
    # Using 'clients' table as a proxy for checking if sample data has been inserted
    if await database.fetch_val(select(func.count()).select_from(clients)) == 0:
        print("--- Inserting sample client data ---")
        # --- FIX: Generate client_id explicitly ---
        acme_client_id = uuid.uuid4().hex[:8].upper()
        tech_innovators_client_id = uuid.uuid4().hex[:8].upper()
        property_group_client_id = uuid.uuid4().hex[:8].upper()
        global_services_client_id = uuid.uuid4().hex[:8].upper()
        strategic_ventures_client_id = uuid.uuid4().hex[:8].upper()

        await database.execute(clients.insert().values(
            client_id=acme_client_id, # <--- ADDED
            name="Acme Corp", contact_email="contact@acmecorp.com", phone_number="+15551234567", status="Active", last_activity_at=datetime.utcnow()
        ))
        await database.execute(clients.insert().values(
            client_id=tech_innovators_client_id, # <--- ADDED
            name="Tech Innovators Inc.", contact_email="info@techinnovators.com", phone_number="+15559876543", status="Active", last_activity_at=datetime.utcnow() - timedelta(days=7)
        ))
        await database.execute(clients.insert().values(
            client_id=property_group_client_id, # <--- ADDED
            name="Property Group LLC", contact_email="contact@propertygroup.com", phone_number="+15551112222", status="Active", last_activity_at=datetime.utcnow() - timedelta(days=14)
        ))
        await database.execute(clients.insert().values(
            client_id=global_services_client_id, # <--- ADDED
            name="Global Services Ltd.", contact_email="info@globalservices.com", phone_number="+15553334444", status="Inactive", last_activity_at=datetime.utcnow() - timedelta(days=21)
        ))
        await database.execute(clients.insert().values(
            client_id=strategic_ventures_client_id, # <--- ADDED
            name="Strategic Ventures Co.", contact_email="contact@strategicventures.com", phone_number="+15555556666", status="Active", last_activity_at=datetime.utcnow() - timedelta(days=28)
        ))

        # Fetch client IDs for foreign keys (after inserting clients)
        # Use the generated IDs for lookup to be safe
        acme_client = await database.fetch_one(select(clients.c.id).where(clients.c.client_id == acme_client_id))
        tech_client = await database.fetch_one(select(clients.c.id).where(clients.c.client_id == tech_innovators_client_id))

        print("--- Inserting sample contract data ---")
        
        await database.execute(contracts.insert().values(
            contract_id=uuid.uuid4().hex[:8].upper(), # <--- ADDED for contracts as well
            name="Acme Corp Agreement", status="Active", signed_date=datetime.utcnow() - timedelta(days=30), client_id=acme_client.id if acme_client else None
        ))
        await database.execute(contracts.insert().values(
            contract_id=uuid.uuid4().hex[:8].upper(), # <--- ADDED for contracts as well
            name="Tech Innovators Partnership", status="Active", signed_date=datetime.utcnow() - timedelta(days=60), client_id=tech_client.id if tech_client else None
        ))
        await database.execute(contracts.insert().values(
            contract_id=uuid.uuid4().hex[:8].upper(), # <--- ADDED for contracts as well
            name="Expired Contract A", status="Expired", signed_date=datetime.utcnow() - timedelta(days=365), expiration_date=datetime.utcnow() - timedelta(days=5)
        ))
        await database.execute(contracts.insert().values(
            contract_id=uuid.uuid4().hex[:8].upper(), # <--- ADDED for contracts as well
            name="Pending Review B", status="Review", signed_date=datetime.utcnow() - timedelta(days=10)
        ))

        print("--- Inserting sample activity data ---")
        await database.execute_many(activities.insert(), [
            {"description": "Reviewed contract for Acme Corp", "activity_type": "Contract Review", "performed_at": datetime.utcnow() - timedelta(hours=2)},
            {"description": "Researched case law for Smith v. Jones", "activity_type": "Legal Research", "performed_at": datetime.utcnow() - timedelta(hours=5)},
            {"description": "Updated case status for Johnson v. Williams", "activity_type": "Case Management", "performed_at": datetime.utcnow() - timedelta(hours=10)},
            {"description": "Initiated client onboarding for new client A", "activity_type": "Client Onboarding", "performed_at": datetime.utcnow() - timedelta(days=1)},
        ])

        print("--- Inserting sample task/deadline data ---")
        # Get a sample case_id to link tasks
        sample_case_record = await database.fetch_one(select(cases.c.id).limit(1)) # Fetch one existing case
        sample_case_id = sample_case_record.id if sample_case_record else None
        
        await database.execute_many(tasks.insert(), [
            {"task_id": uuid.uuid4().hex[:8].upper(),"title": "Review contract for Acme Corp", "task_type": "Review", "due_date": datetime.utcnow() + timedelta(days=2), "status": "Pending", "assigned_to": "Alex"},
            {"task_id": uuid.uuid4().hex[:8].upper(),"title": "Prepare for deposition in Smith v. Jones", "task_type": "Litigation", "due_date": datetime.utcnow() + timedelta(days=5), "status": "In Progress", "assigned_to": "Sarah Johnson", "related_case_id": sample_case_id},
            {"task_id": uuid.uuid4().hex[:8].upper(),"title": "Review compliance report for Johnson v. Williams", "task_type": "Compliance", "due_date": datetime.utcnow() + timedelta(days=7), "status": "Pending"},
            {"task_id": uuid.uuid4().hex[:8].upper(),"title": "Draft initial client intake form", "task_type": "Intake", "due_date": datetime.utcnow() + timedelta(days=1), "status": "Pending", "assigned_to": "Alex"},
            {"task_id": uuid.uuid4().hex[:8].upper(),"title": "Follow up on client XYZ", "task_type": "Communication", "due_date": datetime.utcnow() + timedelta(days=10), "status": "Pending"},
        ])

        print("--- Inserting sample notification data ---")
        await database.execute_many(notifications.insert(), [
            {"message": "Contract for Acme Corp requires your review", "notification_type": "Contract Review", "is_read": False, "created_at": datetime.utcnow() - timedelta(minutes=30), "related_url": "/documents"},
            {"message": "New case law found for Smith v. Jones", "notification_type": "Legal Research", "is_read": False, "created_at": datetime.utcnow() - timedelta(hours=1), "related_url": "/research"},
            {"message": "Case status updated for Johnson v. Williams", "notification_type": "Case Status", "is_read": False, "created_at": datetime.utcnow() - timedelta(hours=2), "related_url": "/cases"},
            {"message": "Welcome to LegalAI!", "notification_type": "Welcome", "is_read": True, "created_at": datetime.utcnow() - timedelta(days=1)},
        ])
        print("--- Sample dashboard data inserted successfully ---")
    else:
        print("--- Sample data already exists, skipping insertion ---")

# --- Debug Endpoints ---
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
    
    # Test Legal Document Retriever (requires actual RAG setup)
    try:
        from backend.app.core.tools import LegalDocumentRetrieverTool # Use the tool directly
        # Note: This might still behave synchronously or require a more complex mock
        # For a true test of the async tool, you might need an async wrapper here
        # For now, just calling the synchronous func for testability in a sync endpoint
        test_query = "What is the policy on employee leave?"
        # The tool expects a string input and returns a string
        result = LegalDocumentRetrieverTool.func(test_query) 
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

    # Test Database Case Reader (Async version)
    try:
        from backend.app.core.tools import AsyncDatabaseCaseReaderTool
        test_phone_number = "+17205690621" # Use a phone number that might exist in sample data
        result = await AsyncDatabaseCaseReaderTool.coroutine(test_phone_number)
        results["database_case_reader"] = {"status": "success", "result": result}
    except Exception as e:
        results["database_case_reader"] = {"status": "error", "error": str(e)}
    
    return results

# --- Vapi Webhook Endpoint (Existing) ---
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
                print("DEBUG: Returning from conversation-update (no convo data)") #PointA
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
                    print("DEBUG: Returning from conversation-update (empty user input)")#pointB
                    return {"message": "I didn't receive any message content"}
                
                # Get caller info
                caller_phone_number = "Unknown" # Ensure initialized
                if message_payload.call and message_payload.call.get("customer"):
                    caller_phone_number = message_payload.call.get("customer").get("number", "Unknown")
                
                print(f"📱 Caller: {caller_phone_number}")
                print(f"👤 User input: '{user_input}'")

                # Build chat history (exclude the last message as it's the current input)
                langchain_history = []
                
                # --- Retrieve and Inject Caller-Specific Context ---
                caller_context_message = "" # Initialize here for safety
                if caller_phone_number != "Unknown":
                    try:
                        client_data = await database_case_reader_async(caller_phone_number)
                        if client_data:
                            caller_context_message = f"Here is relevant information about the current caller ({caller_phone_number}) from your internal database:\n{client_data}"
                            print(f"🔍 Injected caller context:\n{caller_context_message[:200]}...")
                        else:
                            caller_context_message = f"No existing case information found for caller {caller_phone_number}."
                            print(f"🔍 No context found for caller {caller_phone_number}.")
                    except Exception as e:
                        print(f"⚠️ Error retrieving caller context for {caller_phone_number}: {e}") # Added phone number to error log
                        caller_context_message = "An error occurred while retrieving caller information from the database."
                else:
                    caller_context_message = "" # Default to empty if phone number is unknown
                    print("🔍 Caller phone number unknown, skipping specific context retrieval.")

                # Add the caller context as a SystemMessage at the very beginning
                if caller_context_message: # Only add if there's actual content
                    langchain_history.append(SystemMessage(content=caller_context_message))
                # --- END NEW ---

                for msg in conversation_history[:-1]:  # Exclude last message
                    if msg.role == "user":
                        langchain_history.append(HumanMessage(content=msg.content or ""))
                    elif msg.role in ["assistant", "bot"]:
                        langchain_history.append(AIMessage(content=msg.content or ""))
                
                print(f"📚 Built chat history with {len(langchain_history)} messages")
                
                # Prepare agent input
                agent_input = user_input # Simpler, as phone number is in system message now.
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
                    print("DEBUG: Returning from conversation-update (agent response)")#PointC
                    return {"message": agent_text_output}
                    
                except Exception as agent_error:
                    print(f"❌ AGENT EXECUTION ERROR: {type(agent_error).__name__}")
                    print(f"❌ Error message: {str(agent_error)}")
                    import traceback
                    print("❌ Full traceback:")
                    traceback.print_exc()
                    print("DEBUG: Returning from conversation-update (agent error)") #PointD
                    return {"message": "I apologize, but I encountered an issue processing your request. Please try again."}
            else:
                print(f"⏭️ Skipping non-user message (role: {last_message.role})")
                print("DEBUG: Returning from conversation-update (non-user message)") #PointE
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
                print("DEBUG: Returning from status-update") #PointF
            else:
                print("❌ No final transcript artifact found in end-of-call payload")

        # --- Default Route: Log and ignore other event types ---
        else:
            event_type = message_payload.type if message_payload else "Unknown"
            status = getattr(message_payload, 'status', 'N/A')
            print(f"🔇 Ignoring event - Type: {event_type}, Status: {status}")

        print("✅ Webhook processing complete")
        print("DEBUG: Returning from default ignored event") #PointG
        return {}
        
    except Exception as e:
        print(f"💥 WEBHOOK PROCESSING ERROR: {type(e).__name__}")
        print(f"💥 Error message: {str(e)}")
        import traceback
        print("💥 Full traceback:")
        traceback.print_exc()
        print("DEBUG: Returning from global webhook processing error") #PointH
        return {"error": "Internal server error"}

# --- Agent Query (Frontend Web UI) ---
@app.post("/agent-query")
async def perform_agent_query(query: Query):
    """
    Accepts a query and passes it to the agent executor for processing.
    """
    print(f"Received query for agent: {query.text}")
    chat_history = []
    # No SystemMessage injection for web UI, as the context is generally less critical
    # (or could be pulled by the agent via tools if asked directly)
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

# --- Case Intake Endpoint ---
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

# --- Audio Transcription Endpoint ---
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

# --- Existing Cases Endpoint ---
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
        raise HTTPException(status_code=500, detail="Could not fetch cases") # Changed to HTTPException for consistent error handling

# --- RAG Document Endpoints (Existing) ---
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
        raise HTTPException(status_code=500, detail=f"An error occurred during document processing: {str(e)}")

# --- NEW DASHBOARD API ENDPOINTS ---

@app.get("/api/dashboard/overview", response_model=OverviewCounts)
async def get_dashboard_overview():
    """
    Fetches overview counts for the dashboard.
    """
    # Assuming 'Active Contracts' means contracts with status 'Active'
    active_contracts_count_query = select(func.count()).select_from(contracts).where(contracts.c.status == "Active")
    
    # Assuming 'Upcoming Deadlines' are tasks due in the future and not completed
    upcoming_deadlines_count_query = select(func.count()).select_from(tasks).where(
        (tasks.c.due_date >= datetime.utcnow()) & (tasks.c.status.in_(["Pending", "In Progress"]))
    )
    
    # Assuming 'New Notifications' are unread notifications
    new_notifications_count_query = select(func.count()).select_from(notifications).where(notifications.c.is_read == False)

    active_contracts = await database.fetch_val(active_contracts_count_query) or 0
    upcoming_deadlines = await database.fetch_val(upcoming_deadlines_count_query) or 0
    new_notifications = await database.fetch_val(new_notifications_count_query) or 0

    return OverviewCounts(
        active_contracts=active_contracts,
        upcoming_deadlines=upcoming_deadlines,
        new_notifications=new_notifications
    )

@app.get("/api/dashboard/recent-activity", response_model=List[RecentActivity])
async def get_recent_activity():
    """
    Fetches a list of recent activities for the dashboard.
    """
    query = select(activities).order_by(activities.c.performed_at.desc()).limit(5) # Top 5 recent activities
    activity_records = await database.fetch_all(query)
    return [RecentActivity(**dict(record)) for record in activity_records]

@app.get("/api/dashboard/upcoming-deadlines", response_model=List[UpcomingDeadline])
async def get_upcoming_deadlines():
    """
    Fetches a list of upcoming deadlines for the dashboard.
    """
    query = select(tasks).where(
        (tasks.c.due_date >= datetime.utcnow()) & (tasks.c.status.in_(["Pending", "In Progress"]))
    ).order_by(tasks.c.due_date.asc()).limit(5) # Top 5 upcoming
    deadline_records = await database.fetch_all(query)
    return [UpcomingDeadline(**dict(record)) for record in deadline_records]

@app.get("/api/dashboard/notifications", response_model=List[Notification])
async def get_notifications():
    """
    Fetches a list of unread notifications for the dashboard.
    """
    query = select(notifications).where(notifications.c.is_read == False).order_by(notifications.c.created_at.desc()).limit(5) # Top 5 unread
    notification_records = await database.fetch_all(query)
    return [Notification(**dict(record)) for record in notification_records]


# --- Static Files Mounting ---
# This is a "catch-all" route, so it should be at the end.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")