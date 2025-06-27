/legal-agent-app
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py        <-- Our FastAPI server will live here
│   │   └── core/
│   │       └── __init__.py
│   │       └── rag_pipeline.py  <-- Our RAG logic will move here
├── data/
│   └── sample_contract.txt
├── .devcontainer/
├── requirements.txt
└── test_rag.py (we will no longer need this soon)