# backend/app/core/tools.py

from langchain.tools import Tool
# The new, correct import for the Tavily tool
from langchain_tavily import TavilySearch
from pydantic import BaseModel, Field
from .schemas import CaseIntake
from .llm_factory import get_llm
from .rag_pipeline import create_rag_chain
# Import our database objects
from .database import database, cases
from sqlalchemy import select
import json

# --- Tool 1: Internal Document Retriever ---
try:
    rag_chain = create_rag_chain()
    print("DEBUG: RAG chain initialized successfully.")
except Exception as e:
    print(f"ERROR: Failed to initialize RAG chain: {e}")
    rag_chain = None # Set to None to prevent further errors if it's critical

async def legal_document_retriever(query: str) -> str:
    """Invokes the RAG chain to answer a question."""
    print(f"DEBUG: LegalDocumentRetriever called with query: '{query}'")
    if rag_chain is None:
        return "Error: Internal RAG system not initialized. Please check server logs."
    try:
        # Assuming rag_chain.invoke returns a string or has an 'answer' key
        result = await rag_chain.invoke(query)
        # If result is a dict (e.g., from LangChain Runnable), extract the content
        if isinstance(result, dict) and "answer" in result:
            final_result = result["answer"]
        elif isinstance(result, str):
            final_result = result
        else:
            final_result = str(result) # Fallback to string conversion
            
        print(f"DEBUG: LegalDocumentRetriever returned: {final_result[:200]}...") # Print partial result
        return final_result
    except Exception as e:
        print(f"ERROR: Exception in LegalDocumentRetriever for query '{query}': {e}")
        import traceback
        traceback.print_exc() # Print full traceback for deeper debugging
        return f"An error occurred while retrieving internal legal documents: {e}"

LegalDocumentRetrieverTool = Tool(
    name="Internal_Legal_Document_Retriever",
    func=legal_document_retriever,
    description="""Use this tool to answer questions about internal legal documents, 
    case files, contracts, and other documents stored within the firm's private knowledge base. 
    This is your primary tool for retrieving specific information from the firm's data like 'What is the termination policy in the Innovate Corp agreement?'.""",
    # coroutine=legal_document_retriever
)


# --- Tool 2: Web Search ---
# The class name has changed from TavilySearchResults to TavilySearch
WebSearchTool = TavilySearch(
    name="Live_Web_Search",
    description="""Use this tool to search the live internet for recent information,
    current events, breaking news, or information about new case law or regulations
    that may not be in the internal knowledge base. For example, use it to answer 'What were the results of the latest Supreme Court ruling on AI copyright?'."""
)


# --- Tool 3: Case Intake Information Extractor ---
class CaseIntakeInput(BaseModel):
    """Input schema for the Case Intake tool."""
    interview_summary: str = Field(description="The full, unstructured text from a client interview or case summary.")

structured_llm = get_llm().with_structured_output(CaseIntake)

def case_intake_extractor(interview_summary: str) -> dict:
    """
    Processes an unstructured interview summary and extracts structured case data.
    """
    print("--- Running Case Intake Extractor ---")
    result = structured_llm.invoke(f"Please extract the case details from the following text: \n\n{interview_summary}")
    return result.dict()

CaseIntakeExtractorTool = Tool(
    name="Case_Intake_Information_Extractor",
    func=case_intake_extractor,
    args_schema=CaseIntakeInput,
    description="""Use this tool to process a new client interview summary or an unstructured block of text about a new case.
    It will extract key details like client name, opposing party, case type, and a summary of facts into a structured format.
    This is the perfect tool to use when the user says 'create a new case from this text' or 'process this client intake'."""
)
# --- Tool 5: Database Case Reader Tool ---
class DatabaseToolInput(BaseModel):
    """Input for the database case reader tool."""
    phone_number: str = Field(description="The caller's phone number to look up cases for.")

async def database_case_reader(phone_number: str) -> str:
    """
    Looks up existing case information in the database for a given phone number.
    Returns a summary of the cases found or a message if no cases are found.
    """
    print(f"--- Running Database Case Reader Tool for: {phone_number} ---")
    try:
        # Construct the SQL SELECT query using SQLAlchemy
        query = select(cases.c.case_id, cases.c.status, cases.c.call_summary).where(cases.c.caller_phone_number == phone_number)
        
        # Execute the query asynchronously
        results = await database.fetch_all(query)
        
        if not results:
            return f"No existing cases found for the phone number {phone_number}."
        
        # Format the results into a readable string for the LLM
        formatted_results = "Found the following cases for this caller:\n"
        for row in results:
            # The row is a SQLAlchemy Row object, access columns by name
            case_data = dict(row)
            formatted_results += f"- Case ID: {case_data['case_id']}, Status: {case_data['status']}, Summary: {case_data['call_summary']}\n"
        
        return formatted_results
    except Exception as e:
        print(f"Database tool error: {e}")
        return "An error occurred while trying to access the database."

DatabaseCaseReaderTool = Tool(
    name="Database_Case_Reader",
    func=database_case_reader, # Note: We pass the async function directly
    args_schema=DatabaseToolInput,
    description="""Use this tool to retrieve information about a caller's existing cases from the firm's database.
    You must provide the caller's phone_number. This tool is essential for answering questions like
    'What is the status of my case?' or 'Do I have any open cases with you?'.""",
    coroutine=database_case_reader # Tell LangChain this tool's function is async
)