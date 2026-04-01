import React, { useState, useEffect } from 'react'
import {
  fetchN8nStatus,
  fetchN8nWorkflows,
  buildN8nWorkflow,
  activateN8nWorkflow,
  deactivateN8nWorkflow,
} from '../api.js'

const s = {
  container: {
    background: '#12121a',
    border: '1px solid #1e1e2e',
    borderRadius: '12px',
    overflow: 'hidden',
  },
  header: {
    padding: '14px 18px',
    borderBottom: '1px solid #1e1e2e',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerLeft: { display: 'flex', alignItems: 'center', gap: '8px' },
  title: { fontSize: '14px', fontWeight: 700, color: '#fff' },
  statusDot: (ok) => ({
    width: '8px', height: '8px', borderRadius: '50%',
    background: ok ? '#4ade80' : '#ef4444',
    display: 'inline-block',
  }),
  statusText: (ok) => ({
    fontSize: '11px',
    color: ok ? '#4ade80' : '#ef4444',
  }),
  body: { padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' },
  label: { fontSize: '11px', color: '#888', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px' },
  textarea: {
    width: '100%',
    background: '#1a1a2a',
    border: '1px solid #2a2a3a',
    borderRadius: '8px',
    padding: '10px 14px',
    color: '#e0e0e0',
    fontSize: '13px',
    fontFamily: 'Inter, sans-serif',
    lineHeight: '1.5',
    resize: 'vertical',
    minHeight: '90px',
    outline: 'none',
    boxSizing: 'border-box',
  },
  suggestions: { display: 'flex', flexWrap: 'wrap', gap: '6px' },
  chip: {
    background: '#1a1a2e',
    border: '1px solid #2a2a3a',
    borderRadius: '20px',
    padding: '4px 10px',
    fontSize: '11px',
    color: '#aaa',
    cursor: 'pointer',
  },
  buildBtn: (loading, disabled) => ({
    background: disabled ? '#333' : loading ? '#5a50cc' : '#7c6ff7',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontFamily: 'Inter, sans-serif',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    opacity: disabled ? 0.5 : 1,
  }),
  resultBox: (success) => ({
    background: success ? '#0d2818' : '#1e0a0a',
    border: `1px solid ${success ? '#166534' : '#7f1d1d'}`,
    borderRadius: '8px',
    padding: '12px 14px',
    fontSize: '12px',
    color: success ? '#4ade80' : '#f87171',
  }),
  resultRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' },
  link: { color: '#7c6ff7', textDecoration: 'none', fontSize: '12px' },
  divider: { height: '1px', background: '#1e1e2e', margin: '4px 0' },
  wfList: { display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '220px', overflowY: 'auto' },
  wfItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    background: '#1a1a2a',
    borderRadius: '6px',
    padding: '8px 12px',
    fontSize: '12px',
  },
  wfName: { color: '#e0e0e0', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  wfBadge: (active) => ({
    fontSize: '10px',
    padding: '2px 7px',
    borderRadius: '10px',
    background: active ? '#14532d' : '#1e1e2e',
    color: active ? '#4ade80' : '#666',
    marginLeft: '8px',
    flexShrink: 0,
  }),
  iconBtn: {
    background: 'transparent',
    border: '1px solid #2a2a3a',
    borderRadius: '4px',
    padding: '3px 8px',
    color: '#aaa',
    fontSize: '11px',
    cursor: 'pointer',
    marginLeft: '6px',
    flexShrink: 0,
  },
  emptyText: { color: '#555', fontSize: '12px', textAlign: 'center', padding: '16px' },
  spinner: { display: 'inline-block', animation: 'spin 1s linear infinite' },
}

const SUGGESTIONS = [
  'Pull crypto news every 6 hours and save to documents',
  'Fetch top Reddit posts from r/technology daily',
  'Monitor Hacker News and save top stories every morning',
  'Pull latest GitHub trending repos each day',
  'Fetch weather data every hour and log it',
]

export default function N8nBuilder({ model }) {
  const [connected, setConnected] = useState(false)
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [workflows, setWorkflows] = useState([])
  const [loadingWf, setLoadingWf] = useState(false)

  useEffect(() => {
    fetchN8nStatus().then(d => setConnected(d.healthy)).catch(() => setConnected(false))
    loadWorkflows()
  }, [])

  const loadWorkflows = () => {
    setLoadingWf(true)
    fetchN8nWorkflows()
      .then(d => setWorkflows(d.workflows || []))
      .catch(() => {})
      .finally(() => setLoadingWf(false))
  }

  const handleBuild = async () => {
    if (!description.trim() || loading) return
    setLoading(true)
    setResult(null)
    try {
      const useModel = model || 'qwen2.5-coder:7b'
      const data = await buildN8nWorkflow(description.trim(), useModel, true)
      setResult({ success: true, data })
      loadWorkflows()
    } catch (err) {
      setResult({ success: false, error: err.message })
    } finally {
      setLoading(false)
    }
  }

  const handleToggle = async (wf) => {
    try {
      if (wf.active) {
        await deactivateN8nWorkflow(wf.id)
      } else {
        await activateN8nWorkflow(wf.id)
      }
      loadWorkflows()
    } catch (e) { /* ignore */ }
  }

  return (
    <div style={s.container}>
      <div style={s.header}>
        <div style={s.headerLeft}>
          <span style={{ fontSize: '16px' }}>&#9889;</span>
          <span style={s.title}>n8n Workflow Builder</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={s.statusDot(connected)} />
          <span style={s.statusText(connected)}>{connected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </div>

      <div style={s.body}>
        {/* Description input */}
        <div>
          <div style={s.label}>Describe your automation</div>
          <textarea
            style={s.textarea}
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="e.g. Pull crypto news every 6 hours and save the most liked posts to my documents..."
            disabled={loading}
          />
        </div>

        {/* Quick suggestions */}
        <div>
          <div style={s.label}>Quick templates</div>
          <div style={s.suggestions}>
            {SUGGESTIONS.map((s2, i) => (
              <span key={i} style={s.chip} onClick={() => setDescription(s2)}>
                {s2.length > 45 ? s2.slice(0, 45) + '...' : s2}
              </span>
            ))}
          </div>
        </div>

        {/* Build button */}
        <button
          style={s.buildBtn(loading, !connected || !description.trim())}
          onClick={handleBuild}
          disabled={!connected || !description.trim() || loading}
        >
          {loading ? (
            <>
              <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>&#9696;</span>
              Building workflow...
            </>
          ) : (
            <> &#9654; Build &amp; Deploy to n8n</>
          )}
        </button>

        {/* Build result */}
        {result && (
          <div style={s.resultBox(result.success)}>
            {result.success ? (
              <>
                <div style={s.resultRow}>
                  <strong>&#10003; Deployed: {result.data.name}</strong>
                  {result.data.n8n_url && (
                    <a href={result.data.n8n_url} target="_blank" rel="noreferrer" style={s.link}>
                      Open in n8n &#8599;
                    </a>
                  )}
                </div>
                <div style={{ color: '#86efac' }}>
                  {result.data.node_count} nodes &nbsp;|&nbsp; ID: {result.data.workflow_id}
                </div>
                <div style={{ color: '#555', marginTop: '4px' }}>
                  Activate it in the list below or directly in n8n.
                </div>
              </>
            ) : (
              <div>&#10007; {result.error}</div>
            )}
          </div>
        )}

        {/* Existing workflows */}
        <div style={s.divider} />
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <div style={s.label}>Your workflows ({workflows.length})</div>
            <button style={s.iconBtn} onClick={loadWorkflows}>&#8635; Refresh</button>
          </div>
          {loadingWf ? (
            <div style={s.emptyText}>Loading...</div>
          ) : workflows.length === 0 ? (
            <div style={s.emptyText}>No workflows yet — build one above!</div>
          ) : (
            <div style={s.wfList}>
              {workflows.map(wf => (
                <div key={wf.id} style={s.wfItem}>
                  <span style={s.wfName}>{wf.name}</span>
                  <span style={s.wfBadge(wf.active)}>{wf.active ? 'Active' : 'Inactive'}</span>
                  <button style={s.iconBtn} onClick={() => handleToggle(wf)}>
                    {wf.active ? 'Pause' : 'Activate'}
                  </button>
                  <a
                    href={`http://localhost:5678/workflow/${wf.id}`}
                    target="_blank"
                    rel="noreferrer"
                    style={{ ...s.iconBtn, textDecoration: 'none' }}
                  >
                    Edit &#8599;
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
