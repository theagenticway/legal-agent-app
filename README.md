# The Agentic Way: Legal AI Platform

## 🌟 Overview

"The Agentic Way" is a cutting-edge Legal AI platform designed to streamline legal operations through intelligent, context-aware AI agents. Leveraging a **Model Context Platform (MCP)** approach, this application integrates various AI capabilities – including Retrieval Augmented Generation (RAG), advanced natural language processing, and robust memory management – to automate client intake, facilitate document retrieval, provide legal research assistance, and manage case information.

This platform demonstrates how an agentic architecture can enable LLMs to reason, plan, and act in the real world by interacting with internal knowledge bases, external tools, and persistent memory.

## ✨ Features

*   **Agent Chat Interface:**
    *   Engage with a smart legal AI agent capable of answering questions, providing insights, and performing actions based on its extensive knowledge and toolset.
    *   Supports multi-turn conversations with memory of past interactions.
*   **Intelligent Case Intake:**
    *   **Manual Entry:** Manually input case details into a structured format.
    *   **Audio Transcription & Intake:** Upload audio files (e.g., client interviews) for automatic transcription (using Whisper) and subsequent structured data extraction by the AI agent.
*   **Retrieval Augmented Generation (RAG):**
    *   **Document Upload:** Upload legal documents (PDFs, TXT files) to build a private, domain-specific knowledge base.
    *   **Contextual Retrieval:** The agent can access and retrieve information from these indexed documents to answer specific queries, reducing hallucinations and grounding responses in factual data.
    *   **Document Management:** View currently indexed RAG documents and remove them from the system.
*   **Automated Call Processing (Vapi Integration):**
    *   Webhook integration to process real-time call transcripts from Vapi.
    *   Automatically generates call summaries and extracts structured case intake information at the end of a call.
    *   Intelligently updates existing cases or creates new ones based on caller information.
*   **Case Dashboard:**
    *   View and manage all recorded cases in a central dashboard.
    *   Detailed view for each case, including structured intake data, call summaries, full transcripts, and follow-up notes from subsequent calls.
*   **Dynamic Tool Use:** The AI agent is equipped with various tools (internal document retriever, web search, case intake extractor, database reader) and intelligently decides which one(s) to use to fulfill user requests.

## ⚙️ Architecture Overview

The application is built on a robust, modular architecture centered around a **Model Context Platform (MCP)**, which provides the necessary context for the AI agent to operate effectively. All services are containerized using Docker and orchestrated with Docker Compose for easy setup and scalability.

```
+---------------------+    +-------------------------+
|     User Interface  |    |  External Data Sources  |
| (Web App, Chatbot,  |<---| (Vapi, APIs, Files, DB) |
+----------+----------+    +-------------------------+
           |                            | Data Ingestion
           |                            v
+----------v----------+    +-------------------------+
|   API Gateway       |    |  Data & Content         |
|   (FastAPI)         |    |  Preparation (ETL)      |
|   (Docker Container)|    +-------------------------+
+----------+----------+                 ^
           |                            |
           | Request                    | Docker Bridge Network
           v                            |
+----------+----------+    +-------------------------+
|   Agent Orchestrator|    |                         |
|   (LangChain Agent) |<--->|  Model Context Platform |
|                     |    |       (MCP)             |
+----------+----------+    |   - Knowledge Base      |
           |                |     (ChromaDB/PostgreSQL)  |
           | LLM Call       |   - Memory Store        |
           v                |     (PostgreSQL)        |
+----------+----------+    |   - Tool Registry       |
|      LLM Service    |    |   - Embedding Service   |
| (Ollama/Google GenAI)|    +-------------------------+
| (Docker Container   |    (Within backend container)
|  or External API)   |
+---------------------+

+---------------------+
| PostgreSQL Database |
| (Docker Container)  |
+---------------------+
```

### Key Components of the Model Context Platform (MCP):

*   **Knowledge Base (RAG):**
    *   **ChromaDB:** Stores vector embeddings of your internal legal documents, enabling semantic search and retrieval.
    *   **PostgreSQL (`indexed_rag_documents` table):** Maintains metadata about the RAG documents (filenames, chunk count, indexed timestamp) for management.
*   **Memory Store:**
    *   **PostgreSQL (`cases` table):** Acts as the long-term memory, storing comprehensive details for each case, including structured intake, call summaries, full transcripts, and a chronological list of follow-up notes. This allows the agent to recall past interactions and case statuses.
    *   **In-context History (LangChain):** Manages the short-term conversational history, passing recent turns to the LLM within its context window.
*   **Tool Registry (`backend/app/core/tools.py`):**
    *   Defines the functions and APIs the agent can call. This includes:
        *   `Internal_Legal_Document_Retriever` (for RAG queries)
        *   `Live_Web_Search` (powered by Tavily)
        *   `Case_Intake_Information_Extractor` (for structured data extraction)
        *   `Database_Case_Reader` (for retrieving case info from PostgreSQL)
*   **Embedding Service (`backend/app/core/llm_factory.py`):**
    *   Converts text into numerical vector embeddings for RAG and semantic search. Supports Google Generative AI Embeddings or Ollama's Nomic Embed.
*   **LLM Service (`backend/app/core/llm_factory.py`):**
    *   The core large language model responsible for understanding, reasoning, and generation. Configurable to use Google Gemini (Flash 2.0) or local Ollama models (Llama3 8B).
*   **Agent Orchestrator (`backend/app/core/agent.py`):**
    *   Built with LangChain, this is the "brain" of the agent. It interprets user intent, plans multi-step actions, decides which tools to use, constructs LLM prompts, and synthesizes responses.
*   **Data Ingestion & Processing (`backend/app/main.py`, `backend/app/core/post_call_processor.py`, `backend/app/core/transcription.py`):**
    *   Handles the pipelines for uploading documents, transcribing audio, extracting structured data, and persisting case information into the database.

## 🛠️ Technologies Used

### Backend
*   **Python 3.9+**
*   **FastAPI:** Web framework for building the API.
*   **LangChain:** Framework for building LLM applications (agents, RAG, chains).
*   **ChromaDB:** Vector database for RAG (persisted via bind mount in Docker).
*   **PostgreSQL:** Relational database for persistent case data and RAG document metadata.
*   **SQLAlchemy & Databases:** ORM and async database access.
*   **Pydantic:** Data validation and settings management.
*   **Whisper (OpenAI):** Audio transcription.
*   **Tavily:** Web search tool integration.
*   **Ollama:** For running local LLMs and embeddings (Llama3, Nomic Embed).
*   **Google Generative AI:** For Google Gemini LLM and embeddings.
*   `requirements.txt` lists all specific Python dependencies.

### Frontend
*   **HTML5**
*   **CSS3**
*   **JavaScript:** Vanilla JS for dynamic client-side interactions (Fetch API).
*   **Feather Icons:** SVG icon library.
*   **List.js:** For searchable and sortable tables on the dashboard.

### Infrastructure & Deployment
*   **Docker:** Containerization of backend and database services.
*   **Docker Compose:** Orchestration of multi-container application.

## 🚀 Getting Started

Follow these steps to set up and run the Legal AI Platform using Docker Compose.

### Prerequisites

*   Docker Desktop (includes Docker Engine and Docker Compose) installed and running.
*   `git`

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/legal-ai-platform.git # Replace with your repo URL
cd legal-ai-platform
```

### 2. Environment Variables

Create a `.env` file in the **root directory** of the project (where `docker-compose.yml` is located) with the following variables:

```ini
# --- PostgreSQL Database Configuration ---
# These are used by Docker Compose to set up the DB
POSTGRES_DB=legal_ai_db
POSTGRES_USER=legal_user
POSTGRES_PASSWORD=secure_password

# This is the URL that the backend service will use to connect to the DB
# (The 'db' hostname resolves to the PostgreSQL service within the Docker network)
DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"

# --- LLM Provider Configuration ---
# Choose "google" or "ollama"
LLM_PROVIDER="google"
EMBEDDING_PROVIDER="google" # Must match LLM_PROVIDER or be compatible (e.g., "ollama")

# Google API Key (if LLM_PROVIDER/EMBEDDING_PROVIDER is "google")
# Get yours from https://makersuite.google.com/ or Google Cloud
GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"

# Tavily API Key (for Live Web Search tool)
# Get yours from https://tavily.com/
TAVILY_API_KEY="YOUR_TAVILY_API_KEY"

# (Optional) If you have an OpenAI key for other models/services
# OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
```

### 3. Build and Run Services with Docker Compose

From the **root directory** of the project:

```bash
docker-compose up --build
```

*   `--build`: This flag ensures that Docker images (especially for the `backend` service) are built from their `Dockerfile`s before starting.
*   This command will:
    *   Build the `backend` Docker image.
    *   Start a PostgreSQL database container (`db`).
    *   Start the `backend` API container (`backend`).
    *   Set up a shared network for the containers to communicate.
    *   Create `data/chroma_db` and `data/whisper_models` volumes for persistent data (RAG embeddings, Whisper model weights).

### 4. LLM and Embedding Model Setup (If using Ollama)

If you have set `LLM_PROVIDER="ollama"` and `EMBEDDING_PROVIDER="ollama"` in your `.env` file:

*   **Ensure Ollama Service is Running:** The `docker-compose.yml` does *not* include an Ollama container by default. You will need to run your Ollama server externally (e.g., using the [Ollama Docker image](https://ollama.ai/blog/ollama-in-a-docker-container) or the desktop app) and ensure it's accessible from the `backend` container (e.g., by mapping the Ollama port or adding it to the Docker Compose setup if you're comfortable).
*   **Pull Models:** Once Ollama is running, pull the necessary models:
    ```bash
    ollama pull llama3:8b
    ollama pull nomic-embed-text
    ```
    The `backend` container will then connect to this Ollama service.

## 🚀 Usage

Once the services are up and running (you should see logs from both `backend` and `db` services in your terminal):

1.  **Access the Web UI:** Open your browser and go to `http://localhost:8000`. This will load the `index.html` welcome page, served directly by the FastAPI backend container.

2.  **Navigate the Application:**
    *   **Home (`index.html`):** Welcome page with navigation links.
    *   **Dashboard (`dashboard.html`):** View all processed cases, their statuses, and details. Click on a case ID to see its structured intake, call summary, full transcript, and follow-up notes.
    *   **Intake (`case-intake.html`):**
        *   **Manual Entry:** Fill out the form to create a new structured case manually.
        *   **Audio File Intake:** Drag and drop an audio file (e.g., MP3, WAV) onto the dropzone. Click "Transcribe Audio & Process Intake" to transcribe it using Whisper and then process the transcript through the agent's case intake extractor.
    *   **Agent Chat (`agent.html`):**
        *   **Chat with the AI Agent:** Type your queries and interact with the legal AI. The agent will use its RAG, web search, and database tools as needed.
        *   **Upload Documents for RAG:** Use the "Attach Document" (paperclip icon) button to upload `.txt` or `.pdf` files. These documents will be indexed into the RAG knowledge base (persisted in the `data/chroma_db` volume), making their content available for the agent to retrieve.
        *   **View Indexed Documents:** The "Currently Indexed Documents" table shows all files processed for RAG, along with a delete option.

3.  **Vapi Integration (Optional - for Voice AI Calls):**
    *   To integrate with Vapi for real-time voice calls, configure your Vapi Assistant to send webhooks to your running backend.
    *   The webhook URL for conversation updates and status updates should point to: `http://your-server-ip:8000/api/vapi/agent-interaction`
    *   Vapi will send call transcripts to this endpoint, triggering the `post_call_processor` to summarize and save case data.

### Stopping the Services

To stop all running Docker containers and remove the network:

```bash
docker-compose down
```

To stop and remove containers, networks, and all volumes (including your RAG `chroma_db` data):

```bash
docker-compose down -v
```

## 📚 API Endpoints

The FastAPI backend exposes the following key endpoints:

*   **`/` (GET):** Serves the static `index.html` and other frontend files.
*   **`/agent-query` (POST):** Accepts a user query and conversation history, returns an AI response.
*   **`/case-intake` (POST):** Processes unstructured text into a structured case intake format.
*   **`/transcribe-audio` (POST):** Transcribes an uploaded audio file into text.
*   **`/api/cases` (GET):** Fetches all case records from the database.
*   **`/process-rag-documents` (POST):** Uploads and processes documents for RAG indexing.
*   **`/api/rag-documents` (GET):** Lists metadata for all currently indexed RAG documents.
*   **`/api/rag-documents/{filename:path}` (DELETE):** Removes a document and its associated chunks from the RAG system.
*   **`/api/vapi/agent-interaction` (POST):** Handles Vapi webhook events (conversation updates, call status updates).
*   **`/debug/*` (GET):** Various debug endpoints (`/debug/health`, `/debug/llm-test`, `/debug/database-test`, `/debug/tools-test`) for checking system health and connectivity.

## 🤝 Contributing

Contributions are welcome! Please feel free to open issues, submit pull requests, or suggest improvements.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
**Note:** Ensure you have an empty `data/.gitkeep` file in the `data` directory and `frontend/.gitkeep` in the `frontend` directory in your repository, so that these directories are included in the Git clone and Docker can create volumes within them. The `LICENSE` file should also be present in the root directory.
