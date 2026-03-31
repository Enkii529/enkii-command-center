#!/bin/bash
# Command Center — Health Check
echo "=== Command Center Health Check ==="
echo ""

check() {
  local name=$1
  local url=$2
  if curl -sf "$url" > /dev/null 2>&1; then
    echo "  [OK]  $name"
  else
    echo "  [!!]  $name — OFFLINE"
  fi
}

check "API           :8080"    "http://localhost:8080/health"
check "Dashboard     :5629"    "http://localhost:5629"
check "Appsmith      :8081"    "http://localhost:8081"
check "Metabase      :3000"    "http://localhost:3000"
check "Grafana       :3001"    "http://localhost:3001"
check "n8n           :5678"    "http://localhost:5678"
check "Prometheus    :9090"    "http://localhost:9090"
check "Ollama        :11434"   "http://localhost:11434/api/tags"

echo ""
echo "Docker containers:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
