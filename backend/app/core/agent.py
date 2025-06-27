# backend/app/core/agent.py

from langchain import hub
from langchain.agents import create_react_agent, AgentExecutor
from langchain_ollama.chat_models import ChatOllama

# Import our configuration and the tool we just created
from . import config
# backend/app/core/agent.py
# ... imports ...
# Import both tools now
from .tools import LegalDocumentRetrieverTool, WebSearchTool

def create_agent_executor():
    """
    Creates and returns the main agent executor.
    """
    print("--- Initializing agent with tools ---")

    # 1. Define the list of tools the agent can use.
    # Now it has two options!
    tools = [LegalDocumentRetrieverTool, WebSearchTool]

    # ... the rest of the function remains the same ...
    prompt = hub.pull("hwchase17/react-chat")
    llm = ChatOllama(model=config.LLM_MODEL, temperature=0)
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True,
        handle_parsing_errors=True
    )

    print("--- Agent executor created successfully ---")
    return agent_executor