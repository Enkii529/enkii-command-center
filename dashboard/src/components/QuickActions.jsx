import React from 'react'

const styles = {
  container: {
    background: '#12121a',
    border: '1px solid #1e1e2e',
    borderRadius: '12px',
    padding: '16px',
  },
  header: {
    fontSize: '14px',
    fontWeight: 700,
    color: '#fff',
    marginBottom: '12px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '8px',
  },
  btn: {
    background: '#1a1a2e',
    border: '1px solid #2a2a3a',
    borderRadius: '8px',
    padding: '10px 12px',
    color: '#e0e0e0',
    fontSize: '12px',
    fontWeight: 500,
    cursor: 'pointer',
    fontFamily: 'Inter, sans-serif',
    textAlign: 'left',
    transition: 'background 0.2s, border-color 0.2s',
  },
}

const actions = [
  { label: 'API Docs', icon: '>', url: 'http://localhost:8080/docs' },
  { label: 'Appsmith', icon: '>', url: 'http://localhost:8081' },
  { label: 'Metabase', icon: '>', url: 'http://localhost:3000' },
  { label: 'Grafana', icon: '>', url: 'http://localhost:3001' },
  { label: 'n8n Workflows', icon: '>', url: 'http://localhost:5678' },
  { label: 'Prometheus', icon: '>', url: 'http://localhost:9090' },
]

export default function QuickActions() {
  return (
    <div style={styles.container}>
      <div style={styles.header}>Quick Links</div>
      <div style={styles.grid}>
        {actions.map((a) => (
          <button
            key={a.label}
            style={styles.btn}
            onClick={() => window.open(a.url, '_blank')}
            onMouseEnter={(e) => {
              e.target.style.background = '#252540'
              e.target.style.borderColor = '#7c6ff7'
            }}
            onMouseLeave={(e) => {
              e.target.style.background = '#1a1a2e'
              e.target.style.borderColor = '#2a2a3a'
            }}
          >
            {a.icon} {a.label}
          </button>
        ))}
      </div>
    </div>
  )
}
