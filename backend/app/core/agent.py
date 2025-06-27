# backend/app/core/agent.py

from langchain import hub
from langchain.agents import create_react_agent, AgentExecutor
from langchain_ollama.chat_models import ChatOllama

# Import our configuration and the tool we just created
from . import config
from .tools import LegalDocumentRetrieverTool

def create_agent_executor():
    """
    Creates and returns the main agent executor.
    """
    print("--- Initializing agent ---")

    # 1. Define the list of tools the agent can use.
    tools = [LegalDocumentRetrieverTool]

    # 2. Get the prompt template for the ReAct agent.
    # ReAct (Reasoning and Acting) is a common agentic prompting strategy.
    # We pull a pre-made, high-quality prompt from the LangChain Hub.
    prompt = hub.pull("hwchase17/react-chat")

    # 3. Choose the LLM that will power the agent's reasoning.
    llm = ChatOllama(model=config.LLM_MODEL, temperature=0)

    # 4. Create the agent itself.
    # This binds the LLM, the prompt, and the tools together.
    agent = create_react_agent(llm, tools, prompt)

    # 5. Create the Agent Executor.
    # This is the runtime that will actually execute the agent's reasoning loop.
    # verbose=True allows us to see the agent's "thoughts" in the console.
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True,
        handle_parsing_errors=True # Handles cases where the LLM output is not perfect
    )

    print("--- Agent executor created successfully ---")
    return agent_executor