#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "---- Starting Docker service (if not running) ----"
if ! docker info > /dev/null 2>&1; then
  echo "Docker not running. Starting it..."
  sudo service docker start
  while ! docker info > /dev/null 2>&1; do
    echo "Waiting for Docker to start..."
    sleep 1
  done
else
  echo "Docker is already running."
fi

echo "---- Installing/Updating Ollama ----"
curl -fsSL https://ollama.com/install.sh | sh

echo "---- Installing Python dependencies ----"
# This is the updated, more robust line
python3 -m pip install --no-cache-dir -r requirements.txt

echo "---- Starting Ollama in the background ----"
nohup ollama serve > /workspaces/${CODESPACE_NAME}/ollama.log 2>&1 &

echo "---- Waiting for Ollama server to be ready ----"
while ! curl -s http://localhost:11434 > /dev/null; do
  echo "Waiting for Ollama server to start... (checking in 2s)"
  sleep 2
done
echo "---- Ollama server is running! ----"

echo "---- Pulling LLM models ----"
ollama pull llama3:8b
ollama pull nomic-embed-text

echo "---- Environment setup complete! ----"