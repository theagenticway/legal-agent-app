# backend/app/core/agent.py

from langchain import hub
# Import the new agent creation function
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools.render import render_text_description
from .llm_factory import get_llm
from .tools import (
    LegalDocumentRetrieverTool, 
    WebSearchTool, 
    CaseIntakeExtractorTool,
    DatabaseCaseReaderTool
)
def create_agent_executor():
    print("--- Initializing new Tool-Calling Agent ---")

    tools = [
        LegalDocumentRetrieverTool, 
        WebSearchTool, 
        CaseIntakeExtractorTool,
        ContractAnalysisTool,
        DatabaseCaseReaderTool
    ]
    
    # --- THIS IS THE FIX for the KeyError ---
    # 1. Render the tools into a string format that the prompt expects.
    rendered_tools = render_text_description(tools)
    
    # 2. Pull the base prompt from the hub.
    prompt_template = hub.pull("hwchase17/xml-agent-convo")
    
    # 3. Partially format the prompt, injecting the rendered tools.
    # This creates a new prompt that now only expects 'input', 'chat_history', and 'agent_scratchpad'.
    prompt = prompt_template.partial(tools=rendered_tools)
    
    llm = get_llm()
    
    agent = create_tool_calling_agent(llm, tools, prompt)

    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True,
        handle_parsing_errors=True
    )

    print("--- Agent executor created successfully ---")
    return agent_executor