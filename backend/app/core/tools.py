# backend/app/core/tools.py

from langchain.tools import Tool
from langchain_community.tools.tavily_search import TavilySearchResults
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
# The Tavily tool is pre-built and simple to initialize.
# It will automatically use the TAVILY_API_KEY from your .env file.
WebSearchTool = TavilySearchResults(
    name="Live Web Search",
    description="""Use this tool to search the live internet for recent information,
    current events, breaking news, or information about new case law or regulations
    that may not be in the internal knowledge base. For example, use it to answer 'What were the results of the latest Supreme Court ruling on AI copyright?'."""
)