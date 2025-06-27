# backend/app/core/agent.py

from langchain import hub
from langchain.agents import create_react_agent, AgentExecutor
from langchain_ollama.chat_models import ChatOllama

# Import our configuration and the tool we just created
from . import config
# backend/app/core/agent.py
# ... imports ...
# Import both tools now
# backend/app/core/agent.py
# ... other imports ...
# Remove the direct ChatOllama import, add the factory import
from .tools import LegalDocumentRetrieverTool, WebSearchTool, CaseIntakeExtractorTool
from .llm_factory import get_llm # <-- NEW IMPORT

def create_agent_executor():
    # ...
    tools = [...]
    prompt = hub.pull("hwchase17/react-chat")

    # Use the factory to get the LLM
    llm = get_llm() # <-- USE THE FACTORY

    agent = create_react_agent(llm, tools, prompt)
    # ... rest of the function ...#

    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True,
        handle_parsing_errors=True
    )

    print("--- Agent executor created successfully ---")
    return agent_executor