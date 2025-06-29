# backend/app/core/agent.py - Enhanced Debug Version

from langchain import hub
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
    print("🚀 --- Starting Agent Initialization ---")

    # Test LLM first
    try:
        print("🧠 Testing LLM connection...")
        llm = get_llm()
        test_response = llm.invoke("Test message")
        print(f"✅ LLM test successful: {test_response.content[:50]}...")
    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        raise

    # Test tools individually
    tools = [
        LegalDocumentRetrieverTool, 
        WebSearchTool, 
        CaseIntakeExtractorTool,
        DatabaseCaseReaderTool
    ]
    
    print(f"🔧 Testing {len(tools)} tools...")
    for i, tool in enumerate(tools):
        try:
            print(f"  Tool {i+1}: {tool.name} - ✅")
        except Exception as e:
            print(f"  Tool {i+1}: ERROR - {e}")
    
    # Test prompt
    try:
        print("📝 Pulling prompt template...")
        prompt_template = hub.pull("hwchase17/xml-agent-convo")
        print("✅ Prompt template loaded successfully")
        
        rendered_tools = render_text_description(tools)
        print(f"✅ Tools rendered ({len(rendered_tools)} chars)")
        
        prompt = prompt_template.partial(tools=rendered_tools)
        print("✅ Prompt partially formatted")
        
    except Exception as e:
        print(f"❌ Prompt setup failed: {e}")
        raise

    # Test agent creation
    try:
        print("🤖 Creating tool-calling agent...")
        agent = create_tool_calling_agent(llm, tools, prompt)
        print("✅ Agent created successfully")
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        raise

    # Test executor creation
    try:
        print("⚙️ Creating agent executor...")
        agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3,  # Add iteration limit
            early_stopping_method="generate"  # Add early stopping
        )
        print("✅ Agent executor created successfully")
    except Exception as e:
        print(f"❌ Agent executor creation failed: {e}")
        raise

    # Test a simple invocation
    try:
        print("🧪 Testing simple agent invocation...")
        test_result = agent_executor.invoke({
            "input": "Hello, can you help me?",
            "chat_history": []
        })
        print(f"✅ Agent test successful: {test_result.get('output', 'No output')[:100]}...")
    except Exception as e:
        print(f"❌ Agent test invocation failed: {e}")
        # Don't raise here - let's see if it works in practice

    print("🎉 --- Agent Initialization Complete ---")
    return agent_executor