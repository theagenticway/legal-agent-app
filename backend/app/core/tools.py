# backend/app/core/tools.py

from langchain.tools import Tool
from .rag_pipeline import create_rag_chain

# First, we create the RAG chain instance that our tool will use.
rag_chain = create_rag_chain()

# Now, we define the function that the tool will execute.
def legal_document_retriever(query: str) -> str:
    """Invokes the RAG chain to answer a question."""
    return rag_chain.invoke(query)

# Finally, we create the Tool instance.
# The name and description are CRITICAL. The agent uses the description
# to decide when to use this tool.
LegalDocumentRetrieverTool = Tool(
    name="Internal Legal Document Retriever",
    func=legal_document_retriever,
    description="""Use this tool to answer questions about internal legal documents, 
    case files, contracts, and other documents stored within the firm's private knowledge base. 
    This is your primary tool for retrieving specific information from the firm's data."""
)