#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "---- Starting Docker service (if not running) ----"
# This is a more robust way to ensure Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Docker not running. Starting it..."
  sudo service docker start
  # Wait for the Docker socket to be available
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
pip install -r /workspaces/${CODESPACE_NAME}/requirements.txt

echo "---- Starting Ollama in the background ----"
# Use nohup to run ollama serve in the background and log its output
nohup ollama serve > /workspaces/${CODESPACE_NAME}/ollama.log 2>&1 &

echo "---- Waiting for Ollama server to be ready ----"
# This loop will wait until the Ollama API is responsive
while ! curl -s http://localhost:11434 > /dev/null; do
  echo "Waiting for Ollama server to start... (checking in 2s)"
  sleep 2
done
echo "---- Ollama server is running! ----"

echo "---- Pulling LLM models (this will take a few minutes) ----"
ollama pull llama3:8b
ollama pull nomic-embed-text

echo "---- Environment setup complete! ----"