const API = 'http://localhost:8080'

export async function fetchStatus() {
  const res = await fetch(`${API}/dashboard/status`)
  return res.json()
}

export async function fetchActivity(limit = 20) {
  const res = await fetch(`${API}/dashboard/activity?limit=${limit}`)
  return res.json()
}

export async function fetchModels() {
  const res = await fetch(`${API}/ai/models`)
  return res.json()
}

export async function fetchSummary() {
  const res = await fetch(`${API}/summary`)
  return res.json()
}

export async function sendAIAction(message, model, history = []) {
  const res = await fetch(`${API}/dashboard/ai-action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, model, history }),
  })
  return res.json()
}

export async function fetchTasks() {
  const res = await fetch(`${API}/tasks`)
  return res.json()
}

export async function fetchDocuments() {
  const res = await fetch(`${API}/documents`)
  return res.json()
}

export async function fetchN8nStatus() {
  const res = await fetch(`${API}/n8n/status`)
  return res.json()
}

export async function fetchN8nWorkflows() {
  const res = await fetch(`${API}/n8n/workflows`)
  return res.json()
}

export async function buildN8nWorkflow(description, model = 'qwen2.5-coder:7b', deploy = true) {
  const res = await fetch(`${API}/n8n/build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description, model, deploy }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || 'Build failed')
  }
  return res.json()
}

export async function activateN8nWorkflow(id) {
  const res = await fetch(`${API}/n8n/workflows/${id}/activate`, { method: 'PATCH' })
  return res.json()
}

export async function deactivateN8nWorkflow(id) {
  const res = await fetch(`${API}/n8n/workflows/${id}/deactivate`, { method: 'PATCH' })
  return res.json()
}
