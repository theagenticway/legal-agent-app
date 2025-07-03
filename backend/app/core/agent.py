# backend/app/core/agent.py

# Keep these imports
from langchain import hub # Re-add this for pulling the prompt
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools.render import render_text_description # Keep this for rendering tools into prompt
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder # New import for explicit prompt components
from .llm_factory import get_llm
from .tools import (
    LegalDocumentRetrieverTool,
    WebSearchTool,
    CaseIntakeExtractorTool,
    #DatabaseCaseReaderTool
    AsyncDatabaseCaseReaderTool # <-- NEW: Import the async version
)

def create_agent_executor():
    print("🚀 --- Starting Agent Initialization ---")

    # Test LLM first (already working, keep this)
    try:
        print("🧠 Testing LLM connection...")
        llm = get_llm() # Using temperature=0.5 now, which is good.
        test_response = llm.invoke("Test message")
        print(f"✅ LLM test successful: {test_response.content[:50]}...")
    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        raise

    # Define tools (already working, keep this)
    tools = [
        LegalDocumentRetrieverTool,
        WebSearchTool,
        CaseIntakeExtractorTool,
        AsyncDatabaseCaseReaderTool # <-- NEW: Use the async version here
    ]

    print(f"🔧 Testing {len(tools)} tools...")
    for i, tool in enumerate(tools):
        try:
            print(f"  Tool {i+1}: {tool.name} - ✅")
        except Exception as e:
            print(f"  Tool {i+1}: ERROR - {e}")

    # --- RE-ADD PROMPT PULLING, BUT USE A DIFFERENT ONE ---
    try:
        print("📝 Pulling tool-calling agent prompt template...")
        # This prompt is designed for native tool-calling LLMs (like Gemini/OpenAI models)
        # It handles the structure for tool calls and conversation history.
        prompt = hub.pull("hwchase17/openai-tools-agent") # This is the key change here!
        print("✅ Prompt template loaded successfully")

        # The prompt will internally use render_text_description, no need to pass it explicitly here.
        # But ensure it's still imported if used elsewhere or for general awareness.

        # The prompt needs to know about the tools and the conversation history.
        # This is typically handled by the prompt pulled from the hub.
        # No need to do .partial() manually here if the hub prompt is designed for it.
        # The agent creation will pass tools and history to the prompt.

    except Exception as e:
        print(f"❌ Prompt setup failed: {e}")
        raise

    # --- AGENT CREATION ---
    try:
        print("🤖 Creating tool-calling agent...")
        # Now, pass the 'prompt' argument back, but ensure it's the correct type of prompt
        agent = create_tool_calling_agent(llm, tools, prompt) # <<< 'prompt' ARGUMENT IS BACK!
        print("✅ Agent created successfully")
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        raise

    # --- AGENT EXECUTOR CREATION ---
    try:
        print("⚙️ Creating agent executor...")
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True, # Keep verbose=True for detailed logs
            handle_parsing_errors=True,
            max_iterations=5, # Increased iterations to give more room for complex tasks
            early_stopping_method="generate"
        )
        print("✅ Agent executor created successfully")
    except Exception as e:
        print(f"❌ Agent executor creation failed: {e}")
        raise

    # Test a simple invocation (already working, keep this)
    try:
        print("🧪 Testing simple agent invocation...")
        test_result = agent_executor.invoke({ # Use invoke here for the test, ainvoke in main.py
            "input": "Hello, can you help me?",
            "chat_history": []
        })
        print(f"✅ Agent test successful: {test_result.get('output', 'No output')[:100]}...")
    except Exception as e:
        print(f"❌ Agent test invocation failed: {e}")
        # Don't raise here - let's see if it works in practice

    print("🎉 --- Agent Initialization Complete ---")
    return agent_executor