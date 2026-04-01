import React, { useState, useEffect, useRef } from 'react'
import {
  fetchN8nStatus,
  fetchN8nWorkflows,
  startN8nBuildJob,
  pollN8nBuildJob,
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
  title: { fontSize: '14px', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' },
  statusDot: (ok) => ({
    width: '8px', height: '8px', borderRadius: '50%',
    background: ok ? '#4ade80' : '#ef4444',
    flexShrink: 0,
  }),
  statusText: (ok) => ({ fontSize: '11px', color: ok ? '#4ade80' : '#ef4444' }),
  body: { padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' },
  label: {
    fontSize: '11px', color: '#888',
    textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px',
  },
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
    transition: 'border-color 0.15s',
  },
  buildBtn: (loading, disabled) => ({
    background: disabled ? '#1e1e2e' : '#7c6ff7',
    color: disabled ? '#555' : '#fff',
    border: 'none',
    borderRadius: '8px',
    padding: '11px 20px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontFamily: 'Inter, sans-serif',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    width: '100%',
  }),
  progressWrap: {
    background: '#1a1a2a',
    border: '1px solid #2a2a3a',
    borderRadius: '8px',
    padding: '12px 14px',
    fontSize: '12px',
    color: '#aaa',
  },
  progressBar: (pct) => ({
    height: '4px',
    background: '#1e1e2e',
    borderRadius: '2px',
    marginTop: '8px',
    overflow: 'hidden',
    position: 'relative',
  }),
  progressFill: (pct, indeterminate) => ({
    height: '100%',
    background: 'linear-gradient(90deg, #7c6ff7, #a78bfa)',
    borderRadius: '2px',
    width: indeterminate ? '40%' : `${pct}%`,
    animation: indeterminate ? 'slide 1.4s ease-in-out infinite' : 'none',
    transition: 'width 0.4s ease',
  }),
  resultBox: (ok) => ({
    background: ok ? '#0d2818' : '#1e0a0a',
    border: `1px solid ${ok ? '#166534' : '#7f1d1d'}`,
    borderRadius: '8px',
    padding: '12px 14px',
    fontSize: '12px',
    color: ok ? '#4ade80' : '#f87171',
  }),
  resultRow: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: '6px',
  },
  link: { color: '#7c6ff7', textDecoration: 'none', fontSize: '12px' },
  divider: { height: '1px', background: '#1e1e2e' },
  wfList: { display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '200px', overflowY: 'auto' },
  wfItem: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    background: '#1a1a2a', borderRadius: '6px', padding: '8px 12px', fontSize: '12px',
  },
  wfName: { color: '#e0e0e0', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  wfBadge: (active) => ({
    fontSize: '10px', padding: '2px 7px', borderRadius: '10px',
    background: active ? '#14532d' : '#1e1e2e', color: active ? '#4ade80' : '#666',
    marginLeft: '8px', flexShrink: 0,
  }),
  iconBtn: {
    background: 'transparent', border: '1px solid #2a2a3a', borderRadius: '4px',
    padding: '3px 8px', color: '#aaa', fontSize: '11px', cursor: 'pointer',
    marginLeft: '6px', flexShrink: 0, textDecoration: 'none', display: 'inline-block',
  },
  emptyText: { color: '#555', fontSize: '12px', textAlign: 'center', padding: '12px' },
}

const SUGGESTIONS = [
  'Pull crypto news every 6 hours and save titles to documents',
  'Fetch top Reddit posts from r/technology every day at 8am',
  'Monitor Hacker News top AI stories every morning',
  'Pull latest GitHub trending repos each day and save to documents',
  'Fetch BTC price every 30 minutes and log to a document',
]

const PROGRESS_MESSAGES = [
  'Starting up the coding model...',
  'Analyzing your requirements...',
  'Designing workflow structure...',
  'Generating nodes and connections...',
  'Validating workflow JSON...',
  'Deploying to n8n...',
  'Almost there...',
]

export default function N8nBuilder({ model }) {
  const [connected, setConnected] = useState(false)
  const [description, setDescription] = useState('')
  const [jobState, setJobState] = useState(null) // null | {status, message, pct}
  const [result, setResult] = useState(null)
  const [workflows, setWorkflows] = useState([])
  const [loadingWf, setLoadingWf] = useState(false)
  const pollRef = useRef(null)
  const msgIdx = useRef(0)

  useEffect(() => {
    fetchN8nStatus().then(d => setConnected(d.healthy)).catch(() => setConnected(false))
    loadWorkflows()
    return () => clearPoll()
  }, [])

  const clearPoll = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  const loadWorkflows = () => {
    setLoadingWf(true)
    fetchN8nWorkflows()
      .then(d => setWorkflows(d.workflows || []))
      .catch(() => {})
      .finally(() => setLoadingWf(false))
  }

  const handleBuild = async () => {
    if (!description.trim() || jobState?.status === 'running') return
    setResult(null)
    msgIdx.current = 0
    setJobState({ status: 'pending', message: 'Queuing build job...', pct: 5 })

    try {
      const useModel = model || 'qwen2.5-coder:7b'
      const { job_id } = await startN8nBuildJob(description.trim(), useModel, true)

      // Poll every 3 seconds
      pollRef.current = setInterval(async () => {
        try {
          const job = await pollN8nBuildJob(job_id)
          msgIdx.current = Math.min(msgIdx.current + 1, PROGRESS_MESSAGES.length - 1)
          const pct = { pending: 10, running: 30 + msgIdx.current * 10, done: 100, failed: 0 }[job.status] || 10

          if (job.status === 'done') {
            clearPoll()
            setJobState(null)
            setResult({ success: true, data: job.result })
            loadWorkflows()
          } else if (job.status === 'failed') {
            clearPoll()
            setJobState(null)
            setResult({ success: false, error: job.error || 'Build failed' })
          } else {
            setJobState({ status: job.status, message: PROGRESS_MESSAGES[msgIdx.current], pct })
          }
        } catch (e) {
          clearPoll()
          setJobState(null)
          setResult({ success: false, error: 'Lost connection to API' })
        }
      }, 3000)

    } catch (err) {
      setJobState(null)
      setResult({ success: false, error: err.message })
    }
  }

  const handleToggle = async (wf) => {
    try {
      if (wf.active) { await deactivateN8nWorkflow(wf.id) }
      else { await activateN8nWorkflow(wf.id) }
      loadWorkflows()
    } catch (_) {}
  }

  const isBuilding = jobState !== null

  return (
    <div style={s.container}>
      <div style={s.header}>
        <div style={s.title}>
          <span style={{ fontSize: '16px' }}>&#9889;</span>
          n8n Workflow Builder
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={s.statusDot(connected)} />
          <span style={s.statusText(connected)}>{connected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </div>

      <div style={s.body}>
        {/* Description input */}
        <div>
          <div style={s.label}>Describe your automation in plain English</div>
          <textarea
            style={s.textarea}
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="e.g. Pull AI news from Hacker News and Reddit every hour, rank by popularity, save top 10 to documents..."
            disabled={isBuilding}
          />
        </div>

        {/* Quick suggestion chips */}
        <div>
          <div style={s.label}>Quick templates</div>
          <div style={s.suggestions}>
            {SUGGESTIONS.map((s2, i) => (
              <span key={i} style={s.chip} onClick={() => !isBuilding && setDescription(s2)}>
                {s2.length > 48 ? s2.slice(0, 48) + '…' : s2}
              </span>
            ))}
          </div>
        </div>

        {/* Build button */}
        <button
          style={s.buildBtn(isBuilding, !connected || !description.trim() || isBuilding)}
          onClick={handleBuild}
          disabled={!connected || !description.trim() || isBuilding}
        >
          {isBuilding ? '&#8987; Building...' : '&#9654; Build & Deploy to n8n'}
        </button>

        {/* Progress indicator */}
        {jobState && (
          <div style={s.progressWrap}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>{jobState.message}</span>
              <span style={{ color: '#555' }}>{jobState.pct}%</span>
            </div>
            <div style={s.progressBar()}>
              <div style={s.progressFill(jobState.pct, jobState.pct < 100)} />
            </div>
            <div style={{ marginTop: '6px', color: '#555', fontSize: '11px' }}>
              Complex workflows can take 1–3 minutes to generate. Hang tight &#9749;
            </div>
          </div>
        )}

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
                  {result.data.node_count} nodes &nbsp;&middot;&nbsp; ID: {result.data.workflow_id}
                </div>
                <div style={{ color: '#555', marginTop: '4px' }}>
                  Activate it in the list below or directly in n8n. Review nodes before activating.
                </div>
              </>
            ) : (
              <div>&#10007; {result.error}</div>
            )}
          </div>
        )}

        <div style={s.divider} />

        {/* Existing workflows */}
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
                  <span style={s.wfName} title={wf.name}>{wf.name}</span>
                  <span style={s.wfBadge(wf.active)}>{wf.active ? 'Active' : 'Inactive'}</span>
                  <button style={s.iconBtn} onClick={() => handleToggle(wf)}>
                    {wf.active ? 'Pause' : 'Activate'}
                  </button>
                  <a
                    href={`http://localhost:5678/workflow/${wf.id}`}
                    target="_blank" rel="noreferrer"
                    style={s.iconBtn}
                  >
                    Edit &#8599;
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes slide {
          0%   { transform: translateX(-150%); }
          100% { transform: translateX(350%); }
        }
      `}</style>
    </div>
  )
}
