#!/bin/bash
# Pull an Ollama model into the container
set -e

MODEL=${1:-"mistral:7b"}

echo "Pulling model: $MODEL"
docker exec cc-ollama ollama pull "$MODEL"

echo ""
echo "Available models:"
docker exec cc-ollama ollama list
