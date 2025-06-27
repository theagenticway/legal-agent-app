# backend/app/core/tools.py

from langchain.tools import Tool
# The new, correct import for the Tavily tool
from langchain_tavily import TavilySearch
from pydantic import BaseModel, Field
from .schemas import CaseIntake
from .llm_factory import get_llm
from .rag_pipeline import create_rag_chain


# --- Tool 1: Internal Document Retriever ---
rag_chain = create_rag_chain()

def legal_document_retriever(query: str) -> str:
    """Invokes the RAG chain to answer a question."""
    return rag_chain.invoke(query)

LegalDocumentRetrieverTool = Tool(
    name="Internal Legal Document Retriever",
    func=legal_document_retriever,
    description="""Use this tool to answer questions about internal legal documents, 
    case files, contracts, and other documents stored within the firm's private knowledge base. 
    This is your primary tool for retrieving specific information from the firm's data like 'What is the termination policy in the Innovate Corp agreement?'."""
)


# --- Tool 2: Web Search ---
# The class name has changed from TavilySearchResults to TavilySearch
WebSearchTool = TavilySearch(
    name="Live Web Search",
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
    name="Case Intake Information Extractor",
    func=case_intake_extractor,
    args_schema=CaseIntakeInput,
    description="""Use this tool to process a new client interview summary or an unstructured block of text about a new case.
    It will extract key details like client name, opposing party, case type, and a summary of facts into a structured format.
    This is the perfect tool to use when the user says 'create a new case from this text' or 'process this client intake'."""
)