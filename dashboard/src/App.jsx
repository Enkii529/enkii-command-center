import React, { useState, useEffect } from 'react'
import ServiceHub from './components/ServiceHub.jsx'
import ChatPanel from './components/ChatPanel.jsx'
import QuickActions from './components/QuickActions.jsx'
import ActivityFeed from './components/ActivityFeed.jsx'
import ModelSelector from './components/ModelSelector.jsx'
import { fetchModels, fetchSummary } from './api.js'

const styles = {
  app: {
    minHeight: '100vh',
    background: '#08080e',
    color: '#e0e0e0',
    padding: '20px',
    maxWidth: '1400px',
    margin: '0 auto',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '24px',
    padding: '16px 20px',
    background: '#12121a',
    borderRadius: '12px',
    border: '1px solid #1e1e2e',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  title: {
    fontSize: '22px',
    fontWeight: 800,
    color: '#ffffff',
    letterSpacing: '-0.5px',
  },
  version: {
    fontSize: '11px',
    color: '#666',
    background: '#1a1a2a',
    padding: '2px 8px',
    borderRadius: '4px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '20px',
  },
  leftCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  rightCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  summaryBar: {
    display: 'flex',
    gap: '12px',
    flexWrap: 'wrap',
  },
  summaryCard: {
    background: '#12121a',
    border: '1px solid #1e1e2e',
    borderRadius: '10px',
    padding: '12px 16px',
    flex: '1 1 120px',
    textAlign: 'center',
  },
  summaryValue: {
    fontSize: '24px',
    fontWeight: 700,
    color: '#7c6ff7',
  },
  summaryLabel: {
    fontSize: '11px',
    color: '#888',
    marginTop: '4px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
}

export default function App() {
  const [selectedModel, setSelectedModel] = useState('')
  const [models, setModels] = useState([])
  const [summary, setSummary] = useState(null)

  useEffect(() => {
    fetchModels().then(data => {
      setModels(data.models || [])
      setSelectedModel(data.default || '')
    }).catch(() => {})

    fetchSummary().then(setSummary).catch(() => {})

    const interval = setInterval(() => {
      fetchSummary().then(setSummary).catch(() => {})
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <div style={styles.logo}>
          <span style={{ fontSize: '28px' }}>&#9881;</span>
          <div>
            <div style={styles.title}>Command Center</div>
            <span style={styles.version}>v2.0 Dashboard</span>
          </div>
        </div>
        <ModelSelector
          models={models}
          selected={selectedModel}
          onChange={setSelectedModel}
        />
      </header>

      {summary && (
        <div style={styles.summaryBar}>
          <div style={styles.summaryCard}>
            <div style={styles.summaryValue}>{summary.ventures_total}</div>
            <div style={styles.summaryLabel}>Ventures</div>
          </div>
          <div style={styles.summaryCard}>
            <div style={styles.summaryValue}>{summary.projects_active}</div>
            <div style={styles.summaryLabel}>Active Projects</div>
          </div>
          <div style={styles.summaryCard}>
            <div style={styles.summaryValue}>{summary.tasks_open}</div>
            <div style={styles.summaryLabel}>Open Tasks</div>
          </div>
          <div style={styles.summaryCard}>
            <div style={styles.summaryValue}>{summary.tasks_due_today}</div>
            <div style={styles.summaryLabel}>Due Today</div>
          </div>
          <div style={styles.summaryCard}>
            <div style={styles.summaryValue}>{summary.content_in_pipeline}</div>
            <div style={styles.summaryLabel}>Content Pipeline</div>
          </div>
          <div style={styles.summaryCard}>
            <div style={styles.summaryValue}>{summary.new_documents}</div>
            <div style={styles.summaryLabel}>New Docs</div>
          </div>
          <div style={styles.summaryCard}>
            <div style={styles.summaryValue}>{summary.trades_total}</div>
            <div style={styles.summaryLabel}>Trades</div>
          </div>
        </div>
      )}

      <div style={{ marginTop: '20px' }}>
        <ServiceHub />
      </div>

      <div style={{ ...styles.grid, marginTop: '20px' }}>
        <div style={styles.leftCol}>
          <ChatPanel model={selectedModel} />
        </div>
        <div style={styles.rightCol}>
          <QuickActions />
          <ActivityFeed />
        </div>
      </div>
    </div>
  )
}
