# backend/app/core/tools.py

from langchain.tools import Tool
from langchain_tavily import TavilySearch
from pydantic import BaseModel, Field
from .schemas import CaseIntake
from .llm_factory import get_llm
from .rag_pipeline import create_rag_chain
from .database import database, cases
from sqlalchemy import select
import json
import asyncio

# --- Tool 1: Internal Document Retriever ---
try:
    rag_chain = create_rag_chain()
    print("DEBUG: RAG chain initialized successfully.")
except Exception as e:
    print(f"ERROR: Failed to initialize RAG chain: {e}")
    rag_chain = None

def legal_document_retriever_sync(query: str) -> str:
    """Synchronous wrapper for the RAG chain."""
    print(f"DEBUG: LegalDocumentRetriever called with query: '{query}'")
    if rag_chain is None:
        return "Error: Internal RAG system not initialized. Please check server logs."
    
    try:
        # Check if rag_chain has async methods
        if hasattr(rag_chain, 'ainvoke'):
            # Handle async rag_chain
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop in current thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                # If we're in an async context, we need to handle this differently
                # For now, use the synchronous invoke method if available
                if hasattr(rag_chain, 'invoke'):
                    result = rag_chain.invoke(query)
                else:
                    return "Error: Cannot run async RAG chain in sync context"
            else:
                result = loop.run_until_complete(rag_chain.ainvoke(query))
        else:
            # Synchronous rag_chain
            result = rag_chain.invoke(query)
         # --- IMPORTANT: ADD THIS EXTRA PRINT ---
        print(f"DEBUG: Raw result from rag_chain.invoke: {result}")
        # --- END EXTRA PRINT ---
        # Process result
        if isinstance(result, dict) and "answer" in result:
            final_result = result["answer"]
        elif isinstance(result, str):
            final_result = result
        else:
            final_result = str(result)
            
        print(f"DEBUG: LegalDocumentRetriever returned: {final_result[:200]}...")
        return final_result
        
    except Exception as e:
        print(f"ERROR: Exception in LegalDocumentRetriever for query '{query}': {e}")
        import traceback
        traceback.print_exc()
        return f"An error occurred while retrieving internal legal documents: {e}"

LegalDocumentRetrieverTool = Tool(
    name="Internal_Legal_Document_Retriever",
    func=legal_document_retriever_sync,
    description="""Use this tool to answer questions about internal legal documents, 
    case files, contracts, and other documents stored within the firm's private knowledge base. 
    This is your primary tool for retrieving specific information from the firm's data like 'What is the termination policy in the Innovate Corp agreement?'."""
)

# --- Tool 2: Web Search ---
try:
    WebSearchTool = TavilySearch(
        name="Live_Web_Search",
        k=5,  # Number of results to return
        description="""Use this tool to search the live internet for recent information,
        current events, breaking news, or information about new case law or regulations
        that may not be in the internal knowledge base. For example, use it to answer 'What were the results of the latest Supreme Court ruling on AI copyright?'."""
    )
except Exception as e:
    print(f"WARNING: Failed to initialize Tavily search tool: {e}")
    # Create a dummy tool as fallback
    def dummy_search(query: str) -> str:
        return "Web search is currently unavailable. Please check your Tavily API key configuration."
    
    WebSearchTool = Tool(
        name="Live_Web_Search",
        func=dummy_search,
        description="Web search tool (currently unavailable)"
    )

# --- Tool 3: Case Intake Information Extractor ---
class CaseIntakeInput(BaseModel):
    """Input schema for the Case Intake tool."""
    interview_summary: str = Field(description="The full, unstructured text from a client interview or case summary.")

try:
    structured_llm = get_llm().with_structured_output(CaseIntake)
except Exception as e:
    print(f"WARNING: Failed to create structured LLM: {e}")
    structured_llm = None

def case_intake_extractor(interview_summary: str) -> dict:
    """
    Processes an unstructured interview summary and extracts structured case data.
    """
    print("--- Running Case Intake Extractor ---")
    
    if structured_llm is None:
        return {
            "error": "Case intake extractor not available. Please check LLM configuration.",
            "client_name": "Unknown",
            "case_type": "Unknown",
            "summary": interview_summary[:200] + "..." if len(interview_summary) > 200 else interview_summary
        }
    
    try:
        result = structured_llm.invoke(f"Please extract the case details from the following text: \n\n{interview_summary}")
        return result.dict() if hasattr(result, 'dict') else result
    except Exception as e:
        print(f"ERROR in case_intake_extractor: {e}")
        return {
            "error": f"Extraction failed: {str(e)}",
            "client_name": "Unknown",
            "case_type": "Unknown", 
            "summary": interview_summary[:200] + "..." if len(interview_summary) > 200 else interview_summary
        }

CaseIntakeExtractorTool = Tool(
    name="Case_Intake_Information_Extractor",
    func=case_intake_extractor,
    args_schema=CaseIntakeInput,
    description="""Use this tool to process a new client interview summary or an unstructured block of text about a new case.
    It will extract key details like client name, opposing party, case type, and a summary of facts into a structured format.
    This is the perfect tool to use when the user says 'create a new case from this text' or 'process this client intake'."""
)

# --- Tool 4: Database Case Reader Tool ---
class DatabaseToolInput(BaseModel):
    """Input for the database case reader tool."""
    phone_number: str = Field(description="The caller's phone number to look up cases for.")

def database_case_reader_sync(phone_number: str) -> str:
    """
    Synchronous wrapper for database case reader.
    """
    print(f"--- Running Database Case Reader Tool for: {phone_number} ---")
    
    try:
        # Since we can't use async in a sync tool easily, we'll need to handle this
        # For now, return a placeholder or use a sync approach
        return f"Database lookup for {phone_number} requires async context. Please use the async version of this tool."
    except Exception as e:
        print(f"Database tool error: {e}")
        return "An error occurred while trying to access the database."

async def database_case_reader_async(phone_number: str) -> str:
    """
    Async version of database case reader.
    """
    print(f"--- Running Database Case Reader Tool for: {phone_number} ---")
    try:
        query = select(cases.c.case_id, cases.c.status, cases.c.call_summary, cases.c.full_transcript).where(cases.c.caller_phone_number == phone_number)
        results = await database.fetch_all(query)
        
        if not results:
            return f"No existing cases found for the phone number {phone_number}."
        
        formatted_results = "Found the following cases for this caller:\n"
        for row in results:
            case_data = dict(row)
            formatted_results += f"- Case ID: {case_data['case_id']}, Status: {case_data['status']}, Summary: {case_data['call_summary']}\n"
        
        return formatted_results
    except Exception as e:
        print(f"Database tool error: {e}")
        return "An error occurred while trying to access the database."

# Create both sync and async versions
DatabaseCaseReaderTool = Tool(
    name="Database_Case_Reader",
    func=database_case_reader_sync,
    args_schema=DatabaseToolInput,
    description="""Use this tool to retrieve information about a caller's existing cases from the firm's database.
    You must provide the caller's phone_number. This tool is essential for answering questions like
    'What is the status of my case?' or 'Do I have any open cases with you?'."""
)

# For async contexts, you might want to create a separate tool
AsyncDatabaseCaseReaderTool = Tool(
    name="Database_Case_Reader_Async",
    func=database_case_reader_async,
    args_schema=DatabaseToolInput,
    description="""Async version of database case reader tool.""",
    coroutine=database_case_reader_async
)