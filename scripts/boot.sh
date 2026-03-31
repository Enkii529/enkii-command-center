#!/bin/bash
# Command Center — Boot Script
set -e

echo "=== Command Center Boot ==="

# Check Docker
if ! command -v docker &> /dev/null; then
  echo "ERROR: Docker is not installed or not in PATH"
  exit 1
fi

echo "Docker found: $(docker --version)"

# Copy .env if missing
if [ ! -f .env ]; then
  echo "No .env found — copying from .env.example"
  cp .env.example .env
  echo "IMPORTANT: Edit .env and set strong passwords before production use!"
fi

# Build and start
echo ""
echo "Starting all services..."
docker compose up -d --build

echo ""
echo "Waiting for services to start..."
sleep 10

# Health checks
echo ""
echo "=== Service Status ==="
echo ""

check() {
  local name=$1
  local url=$2
  if curl -sf "$url" > /dev/null 2>&1; then
    echo "  [OK]  $name"
  else
    echo "  [--]  $name (not ready yet)"
  fi
}

check "API           http://localhost:8080"    "http://localhost:8080/health"
check "Dashboard     http://localhost:5629"    "http://localhost:5629"
check "Appsmith      http://localhost:8081"    "http://localhost:8081"
check "Metabase      http://localhost:3000"    "http://localhost:3000"
check "Grafana       http://localhost:3001"    "http://localhost:3001"
check "n8n           http://localhost:5678"    "http://localhost:5678"
check "Prometheus    http://localhost:9090"    "http://localhost:9090"
check "Ollama        http://localhost:11434"   "http://localhost:11434/api/tags"

echo ""
echo "=== Ready ==="
echo "Dashboard: http://localhost:5629"
echo "API Docs:  http://localhost:8080/docs"
