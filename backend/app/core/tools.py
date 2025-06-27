# backend/app/core/tools.py

from langchain.tools import Tool
from langchain_community.tools.tavily_search import TavilySearchResults
from .rag_pipeline import create_rag_chain
# ... other imports ...
# Remove direct ChatOllama import, add the factory
# from .schemas import CaseIntake
from .llm_factory import get_llm # <-- NEW IMPORT

# ... Tool 1 and Tool 2 ...


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
# The Tavily tool is pre-built and simple to initialize.
# It will automatically use the TAVILY_API_KEY from your .env file.
WebSearchTool = TavilySearchResults(
    name="Live Web Search",
    description="""Use this tool to search the live internet for recent information,
    current events, breaking news, or information about new case law or regulations
    that may not be in the internal knowledge base. For example, use it to answer 'What were the results of the latest Supreme Court ruling on AI copyright?'."""
)
# --- Tool 3: Case Intake Information Extractor ---
""" class CaseIntakeInput(BaseModel):
    """Input schema for the Case Intake tool."""
    interview_summary: str = Field(description="...")
 """
# Use the factory to get a structured output LLM
""" structured_llm = get_llm().with_structured_output(CaseIntake) # <-- USE THE FACTORY

def case_intake_extractor(interview_summary: str) -> dict:
    # ...
    result = structured_llm.invoke(...)
    return result.dict()

CaseIntakeExtractorTool = Tool(...) """