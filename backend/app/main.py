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
import json
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
from sqlalchemy import select, func, and_, cast, Text # Import cast and Text for JSON column handling
from sqlalchemy.dialects.postgresql import JSONB # Ensure JSONB is imported if you use it for JSON columns in SELECT
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
    DashboardData,      # NEW (though not used directly as a response model for one endpoint yet)
    Client, # NEW: Import Client schema
    Case  # NEW: Import Case schema
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
        
        # Generate UUIDs for clients upfront
        acme_client_id = uuid.uuid4().hex[:8].upper()
        tech_innovators_client_id = uuid.uuid4().hex[:8].upper()
        property_group_client_id = uuid.uuid4().hex[:8].upper()
        global_services_client_id = uuid.uuid4().hex[:8].upper()
        strategic_ventures_client_id = uuid.uuid4().hex[:8].upper()

        # Insert clients
        await database.execute(clients.insert().values(
            client_id=acme_client_id, name="Acme Corp", contact_email="contact@acmecorp.com", phone_number="+15551234567", status="Active", last_activity_at=datetime.utcnow()
        ))
        await database.execute(clients.insert().values(
            client_id=tech_innovators_client_id, name="Tech Innovators Inc.", contact_email="info@techinnovators.com", phone_number="+15559876543", status="Active", last_activity_at=datetime.utcnow() - timedelta(days=7)
        ))
        await database.execute(clients.insert().values(
            client_id=property_group_client_id, name="Property Group LLC", contact_email="contact@propertygroup.com", phone_number="+15551112222", status="Active", last_activity_at=datetime.utcnow() - timedelta(days=14)
        ))
        await database.execute(clients.insert().values(
            client_id=global_services_client_id, name="Global Services Ltd.", contact_email="info@globalservices.com", phone_number="+15553334444", status="Inactive", last_activity_at=datetime.utcnow() - timedelta(days=21)
        ))
        await database.execute(clients.insert().values(
            client_id=strategic_ventures_client_id, name="Strategic Ventures Co.", contact_email="contact@strategicventures.com", phone_number="+15555556666", status="Active", last_activity_at=datetime.utcnow() - timedelta(days=28)
        ))

        # --- NEW: Fetch the actual ID and name of the inserted client records ---
        # These variables are now correctly scoped and assigned right after insertion
        acme_client_record = await database.fetch_one(select(clients.c.id, clients.c.name).where(clients.c.client_id == acme_client_id))
        tech_client_record = await database.fetch_one(select(clients.c.id, clients.c.name).where(clients.c.client_id == tech_innovators_client_id))
        property_group_client_record = await database.fetch_one(select(clients.c.id, clients.c.name).where(clients.c.client_id == property_group_client_id))
        global_services_client_record = await database.fetch_one(select(clients.c.id, clients.c.name).where(clients.c.client_id == global_services_client_id))
        strategic_ventures_client_record = await database.fetch_one(select(clients.c.id, clients.c.name).where(clients.c.client_id == strategic_ventures_client_id))

        print("--- Inserting sample case data ---")
        # Generate structured_intake JSON for cases
        structured_intake_acme = json.dumps(CaseIntake(
            client_name="Acme Corp",
            opposing_party="Innovate Corp",
            case_type="Contract Dispute",
            summary_of_facts="Client Acme Corp has a dispute regarding terms of a software licensing agreement with Innovate Corp.",
            key_dates=["01/15/2024", "02/20/2024"]
        ).dict())

        structured_intake_tech = json.dumps(CaseIntake(
            client_name="Tech Innovators Inc.",
            opposing_party="Competitor X",
            case_type="Intellectual Property",
            summary_of_facts="Tech Innovators Inc. is defending against a patent infringement claim by Competitor X related to their new AI algorithm.",
            key_dates=["03/01/2022", "06/01/2023"]
        ).dict())

        structured_intake_property = json.dumps(CaseIntake(
            client_name="Property Group LLC",
            opposing_party="City Zoning Board",
            case_type="Real Estate Law",
            summary_of_facts="Property Group LLC is seeking a variance from the city zoning board for a new commercial development.",
            key_dates=["07/10/2024"]
        ).dict())
        
        structured_intake_global = json.dumps(CaseIntake(
            client_name="Global Services Ltd.",
            opposing_party="Former Employee",
            case_type="Employment Litigation",
            summary_of_facts="Global Services Ltd. is involved in litigation with a former employee regarding wrongful termination allegations.",
            key_dates=["04/01/2023", "09/15/2023"]
        ).dict())

        structured_intake_strategic = json.dumps(CaseIntake(
            client_name="Strategic Ventures Co.",
            opposing_party="Merger Partner Corp",
            case_type="Corporate Law",
            summary_of_facts="Strategic Ventures Co. is undergoing a merger with Merger Partner Corp, requiring extensive legal due diligence.",
            key_dates=["05/01/2024", "08/30/2024"]
        ).dict())

        await database.execute_many(cases.insert(), [
            {
                "case_id": f"CASE-{uuid.uuid4().hex[:8].upper()}",
                "caller_phone_number": "+15551234567", # Matches Acme Corp
                "status": "Open",
                "structured_intake": structured_intake_acme,
                "call_summary": "Initial consultation on contract dispute.",
                "full_transcript": "User: Hi, I'm from Acme Corp. We have a contract dispute. AI: Understood. Please provide details.",
                "follow_up_notes": json.dumps([]),
                "assigned_to": "Sarah Johnson",
                "last_updated_at": datetime.utcnow()
            },
            {
                "case_id": f"CASE-{uuid.uuid4().hex[:8].upper()}",
                "caller_phone_number": "+15559876543", # Matches Tech Innovators
                "status": "In Progress",
                "structured_intake": structured_intake_tech,
                "call_summary": "Discussion about patent infringement defense strategy.",
                "full_transcript": "User: We're being sued for patent infringement. AI: I understand. Let's discuss your defense.",
                "follow_up_notes": json.dumps([{"timestamp": datetime.utcnow().isoformat(), "summary": "Discussed strategy for patent case."}]),
                "assigned_to": "David Lee",
                "last_updated_at": datetime.utcnow() - timedelta(days=1)
            },
            {
                "case_id": f"CASE-{uuid.uuid4().hex[:8].upper()}",
                "caller_phone_number": "+15551112222", # Matches Property Group
                "status": "Closed",
                "structured_intake": structured_intake_property,
                "call_summary": "Case resolved, zoning variance granted.",
                "full_transcript": "User: The zoning board approved our variance. AI: Excellent news!",
                "follow_up_notes": json.dumps([]),
                "assigned_to": "Emily Chen",
                "last_updated_at": datetime.utcnow() - timedelta(days=2)
            },
            {
                "case_id": f"CASE-{uuid.uuid4().hex[:8].upper()}",
                "caller_phone_number": "+15553334444", # Matches Global Services
                "status": "Open",
                "structured_intake": structured_intake_global,
                "call_summary": "Initial review of employment litigation claim.",
                "full_transcript": "User: I need help with a former employee's claim. AI: Tell me more.",
                "follow_up_notes": json.dumps([]),
                "assigned_to": "Michael Brown",
                "last_updated_at": datetime.utcnow() - timedelta(days=3)
            },
            {
                "case_id": f"CASE-{uuid.uuid4().hex[:8].upper()}",
                "caller_phone_number": "+15555556666", # Matches Strategic Ventures
                "status": "In Progress",
                "structured_intake": structured_intake_strategic,
                "call_summary": "Discussion on legal aspects of corporate merger.",
                "full_transcript": "User: We are planning a merger. AI: What are your legal concerns?",
                "follow_up_notes": json.dumps([]),
                "assigned_to": "Jessica White",
                "last_updated_at": datetime.utcnow() - timedelta(days=4)
            }
        ])

        print("--- Inserting sample contract data ---")
        await database.execute_many(contracts.insert(), [
            {
                "contract_id": uuid.uuid4().hex[:8].upper(),
                "name": "Acme Corp Agreement",
                "status": "Active",
                "signed_date": datetime.utcnow() - timedelta(days=30),
                "client_id": acme_client_record.id if acme_client_record else None
            },
            {
                "contract_id": uuid.uuid4().hex[:8].upper(),
                "name": "Tech Innovators Partnership",
                "status": "Active",
                "signed_date": datetime.utcnow() - timedelta(days=60),
                "client_id": tech_client_record.id if tech_client_record else None
            },
            {
                "contract_id": uuid.uuid4().hex[:8].upper(),
                "name": "Expired Contract A",
                "status": "Expired",
                "signed_date": datetime.utcnow() - timedelta(days=365),
                "expiration_date": datetime.utcnow() - timedelta(days=5)
            },
            {
                "contract_id": uuid.uuid4().hex[:8].upper(),
                "name": "Pending Review B",
                "status": "Review",
                "signed_date": datetime.utcnow() - timedelta(days=10)
            }
        ])

        print("--- Inserting sample activity data ---")
        await database.execute_many(activities.insert(), [
            {"description": "Reviewed contract for Acme Corp", "activity_type": "Contract Review", "performed_at": datetime.utcnow() - timedelta(hours=2)},
            {"description": "Researched case law for Smith v. Jones", "activity_type": "Legal Research", "performed_at": datetime.utcnow() - timedelta(hours=5)},
            {"description": "Updated case status for Johnson v. Williams", "activity_type": "Case Management", "performed_at": datetime.utcnow() - timedelta(hours=10)},
            {"description": "Initiated client onboarding for new client A", "activity_type": "Client Onboarding", "performed_at": datetime.utcnow() - timedelta(days=1)},
        ])

        print("--- Inserting sample task/deadline data ---")
        # Get a sample case_id to link tasks (fetch from cases just inserted)
        # Fix: Cast structured_intake to Text before using .contains() / LIKE
        sample_case_record = await database.fetch_one(
            select(cases.c.id)
            .where(cast(cases.c.structured_intake, Text).contains("Acme Corp"))
            .limit(1)
        ) # Link to Acme's case
        sample_case_id = sample_case_record.id if sample_case_record else None
        
        await database.execute_many(tasks.insert(), [
            {"task_id": uuid.uuid4().hex[:8].upper(), "title": "Review contract for Acme Corp", "task_type": "Review", "due_date": datetime.utcnow() + timedelta(days=2), "status": "Pending", "assigned_to": "Alex"},
            {"task_id": uuid.uuid4().hex[:8].upper(), "title": "Prepare for deposition in Smith v. Jones", "task_type": "Litigation", "due_date": datetime.utcnow() + timedelta(days=5), "status": "In Progress", "assigned_to": "Sarah Johnson", "related_case_id": sample_case_id},
            {"task_id": uuid.uuid4().hex[:8].upper(), "title": "Review compliance report for Johnson v. Williams", "task_type": "Compliance", "due_date": datetime.utcnow() + timedelta(days=7), "status": "Pending"},
            {"task_id": uuid.uuid4().hex[:8].upper(), "title": "Draft initial client intake form", "task_type": "Intake", "due_date": datetime.utcnow() + timedelta(days=1), "status": "Pending", "assigned_to": "Alex"},
            {"task_id": uuid.uuid4().hex[:8].upper(), "title": "Follow up on client XYZ", "task_type": "Communication", "due_date": datetime.utcnow() + timedelta(days=10), "status": "Pending"},
        ])

        print("--- Inserting sample notification data ---")
        await database.execute_many(notifications.insert(), [
            {
                "id": 1, # Explicit ID
                "message": "Contract for Acme Corp requires your review",
                "notification_type": "Contract Review",
                "is_read": False,
                "created_at": datetime.utcnow() - timedelta(minutes=30),
                "related_url": "/documents"
            },
            {
                "id": 2, # Explicit ID
                "message": "New case law found for Smith v. Jones",
                "notification_type": "Legal Research",
                "is_read": False,
                "created_at": datetime.utcnow() - timedelta(hours=1),
                "related_url": "/research"
            },
            {
                "id": 3, # Explicit ID
                "message": "Case status updated for Johnson v. Williams",
                "notification_type": "Case Status",
                "is_read": False,
                "created_at": datetime.utcnow() - timedelta(hours=2),
                "related_url": "/cases"
            },
            {
                "id": 4, # Explicit ID
                "message": "Welcome to LegalAI!",
                "notification_type": "Welcome",
                "is_read": True,
                "created_at": datetime.utcnow() - timedelta(days=1)
            },
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

# --- MODIFIED /api/cases endpoint ---
@app.get("/api/cases", response_model=List[Case])
async def get_all_cases():
    """
    Fetches all case records from the database, formatted for the UI.
    """
    print("--- Fetching all cases from the database ---")
    try:
        # Explicitly select all columns needed by the Case Pydantic model
        # This makes it robust against internal caching issues or implicit column selection.
        query = select(
            cases.c.id,
            cases.c.case_id,
            cases.c.caller_phone_number,
            cases.c.status,
            cases.c.structured_intake,
            cases.c.call_summary,
            cases.c.full_transcript,
            cases.c.follow_up_notes,
            cases.c.created_at,
            cases.c.vapi_call_id,
            cases.c.assigned_to,
            cases.c.last_updated_at, # Explicitly selected here
            clients.c.name.label("client_actual_name") # From the join
        ).outerjoin(clients, cases.c.caller_phone_number == clients.c.phone_number)
        
        all_case_records = await database.fetch_all(query)
        
        result_cases = []
        for record in all_case_records:
            # Convert SQLAlchemy Row to a mutable dictionary
            case_dict = dict(record)
            
            print(f"DEBUG (get_all_cases): Raw record dict keys: {case_dict.keys()}")
            print(f"DEBUG (get_all_cases): Value of last_updated_at from DB: {case_dict.get('last_updated_at')}")
            # Ensure 'last_updated_at' key is always present, even if its value is None from DB for old records
            db_last_updated_at = case_dict.get('last_updated_at')
            if db_last_updated_at is None:
                # Fallback to created_at if last_updated_at is null or not found
                case_dict['last_updated_at'] = case_dict['created_at'] 
                print(f"DEBUG (get_all_cases): last_updated_at was None/Missing, defaulting to created_at: {case_dict['last_updated_at']}")
            else:
                # Ensure it's a datetime object. databases/asyncpg usually does this, but being explicit.
                if not isinstance(db_last_updated_at, datetime):
                    try:
                        case_dict['last_updated_at'] = datetime.fromisoformat(str(db_last_updated_at))
                        print(f"DEBUG (get_all_cases): Converted last_updated_at string to datetime: {case_dict['last_updated_at']}")
                    except ValueError:
                        print(f"WARNING (get_all_cases): Could not convert last_updated_at '{db_last_updated_at}' to datetime, defaulting to created_at.")
                        case_dict['last_updated_at'] = case_dict['created_at']


            # Parse structured_intake JSON
            structured_intake_data = {}
            if case_dict.get('structured_intake'): # Use .get() for safety
                try:
                    if isinstance(case_dict['structured_intake'], str):
                         structured_intake_data = json.loads(case_dict['structured_intake'])
                    else:
                         structured_intake_data = case_dict['structured_intake']
                except (json.JSONDecodeError, TypeError):
                    print(f"Warning: Could not parse structured_intake for case {case_dict.get('case_id')}")
                    structured_intake_data = {}
            
            # Derive 'case_name', 'client_name', 'type'
            case_name = structured_intake_data.get('summary_of_facts', 'N/A')
            if len(case_name) > 50:
                case_name = case_name[:50] + '...'

            client_name = case_dict.get('client_actual_name')
            if not client_name and structured_intake_data:
                client_name = structured_intake_data.get('client_name', 'N/A')
            if not client_name:
                client_name = 'Unknown Client'

            case_type = structured_intake_data.get('case_type', 'N/A')

            # Handle follow_up_notes and ensure it's a list
            follow_up_notes_parsed = []
            if case_dict.get('follow_up_notes'):
                try:
                    if isinstance(case_dict['follow_up_notes'], str):
                        follow_up_notes_parsed = json.loads(case_dict['follow_up_notes'])
                    else:
                        follow_up_notes_parsed = case_dict['follow_up_notes']
                except (json.JSONDecodeError, TypeError):
                    print(f"Warning: Could not parse follow_up_notes for case {case_dict.get('case_id')}")
                    follow_up_notes_parsed = []
            
            if not isinstance(follow_up_notes_parsed, list):
                print(f"Warning: follow_up_notes for case {case_dict.get('case_id')} not a list after parsing, resetting to empty.")
                follow_up_notes_parsed = []
# Ensure all keys Pydantic expects are present, even if their value is None
            final_case_data_for_pydantic = {
                "id": case_dict['id'],
                "case_id": case_dict['case_id'],
                "case_name": case_name,
                "client_name": client_name,
                "type": case_type,
                "status": case_dict['status'],
                "assigned_to": case_dict.get('assigned_to'),
                "last_updated_at": case_dict['last_updated_at'], # This is the key Pydantic's alias looks for
                "caller_phone_number": case_dict.get('caller_phone_number'),
                "structured_intake": structured_intake_data,
                "call_summary": case_dict.get('call_summary'),
                "full_transcript": case_dict.get('full_transcript'),
                "follow_up_notes": follow_up_notes_parsed,
                "created_at": case_dict['created_at'],
                "vapi_call_id": case_dict.get('vapi_call_id')
            }
            print(f"DEBUG (get_all_cases): Final dict for Pydantic (partial): id={final_case_data_for_pydantic['id']}, case_id={final_case_data_for_pydantic['case_id']}, last_updated_at={final_case_data_for_pydantic.get('last_updated_at')}, follow_up_notes_type={type(final_case_data_for_pydantic['follow_up_notes'])}")

            # Use model_validate for robust Pydantic v2 validation
            case_model = Case.model_validate(final_case_data_for_pydantic)
            result_cases.append(case_model)

        return result_cases
    except Exception as e:
        print(f"Error fetching cases: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Could not fetch cases")
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


# --- NEW CLIENTS API ENDPOINT ---
@app.get("/api/clients", response_model=List[Client])
async def get_all_clients():
    """
    Fetches all client records from the database, including their case count.
    """
    print("--- Fetching all clients from the database ---")
    try:
        # Subquery to count cases per client (linked by phone_number for now,
        # ideally by a client_id foreign key in the cases table)
        case_counts_subquery = (
            select(
                cases.c.caller_phone_number,
                func.count().label("num_cases")
            )
            .group_by(cases.c.caller_phone_number)
            .alias("case_counts")
        )

        # Main query to select clients and join with case counts
        query = (
            select(
                clients, # Select all columns from clients table
                case_counts_subquery.c.num_cases # Select num_cases from subquery
            )
            .outerjoin(
                case_counts_subquery,
                clients.c.phone_number == case_counts_subquery.c.caller_phone_number
            )
            .order_by(clients.c.name.asc())
        )

        client_records = await database.fetch_all(query)
        
        # Manually construct Client Pydantic models to include num_cases
        result_clients = []
        for record in client_records:
            client_dict = dict(record)
            # Ensure 'num_cases' is an integer, default to 0 if NULL (no cases)
            client_dict['num_cases'] = client_dict['num_cases'] if client_dict['num_cases'] is not None else 0
            
            # Remove any extra fields from the raw record that are not in the Client schema
            # This is important if you select 'clients' and the join adds more.
            # Convert datetime objects to ISO format if Pydantic doesn't handle it implicitly
            client_dict['last_activity_at'] = client_dict['last_activity_at'].isoformat() if isinstance(client_dict['last_activity_at'], datetime) else client_dict['last_activity_at']
            client_dict['created_at'] = client_dict['created_at'].isoformat() if isinstance(client_dict['created_at'], datetime) else client_dict['created_at']


            # Create the Pydantic model
            result_clients.append(Client(**client_dict))

        return result_clients
    except Exception as e:
        print(f"Error fetching clients: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Could not fetch clients")


# --- Static Files Mounting ---
# This is a "catch-all" route, so it should be at the end.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")