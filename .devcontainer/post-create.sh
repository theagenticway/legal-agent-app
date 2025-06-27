#!/bin/bash

echo "---- Starting Docker service ----"
sudo service docker start

echo "---- Installing Ollama ----"
curl -fsSL https://ollama.com/install.sh | sh

echo "---- Installing Python dependencies ----"
pip install -r requirements.txt

echo "---- Starting Ollama in the background ----"
# Use nohup to run ollama serve in the background and log its output
nohup ollama serve > ollama.log 2>&1 &

# Wait a few seconds for the server to initialize
sleep 5

echo "---- Pulling LLM models (this will take a few minutes) ----"
# Pull a powerful model for analysis and a dedicated embedding model
ollama pull llama3:8b
ollama pull nomic-embed-text

echo "---- Environment setup complete! ----"