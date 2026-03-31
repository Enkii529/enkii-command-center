import React, { useState, useEffect } from 'react'
import { fetchStatus } from '../api.js'

const styles = {
  container: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
    gap: '12px',
  },
  card: {
    background: '#12121a',
    border: '1px solid #1e1e2e',
    borderRadius: '10px',
    padding: '14px 16px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    cursor: 'pointer',
    transition: 'border-color 0.2s, background 0.2s',
  },
  cardHover: {
    borderColor: '#7c6ff7',
    background: '#16162a',
  },
  dot: (online) => ({
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    background: online ? '#4ade80' : '#ef4444',
    flexShrink: 0,
    boxShadow: online ? '0 0 8px #4ade8066' : '0 0 8px #ef444466',
  }),
  name: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#fff',
  },
  port: {
    fontSize: '11px',
    color: '#666',
    marginLeft: 'auto',
  },
}

export default function ServiceHub() {
  const [services, setServices] = useState([])
  const [hoveredIdx, setHoveredIdx] = useState(-1)

  useEffect(() => {
    const load = () => {
      fetchStatus()
        .then((data) => setServices(data.services || []))
        .catch(() => {})
    }
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [])

  const openService = (url) => {
    window.open(url, '_blank')
  }

  return (
    <div style={styles.container}>
      {services.map((s, i) => (
        <div
          key={s.name}
          style={{
            ...styles.card,
            ...(hoveredIdx === i ? styles.cardHover : {}),
          }}
          onMouseEnter={() => setHoveredIdx(i)}
          onMouseLeave={() => setHoveredIdx(-1)}
          onClick={() => openService(s.url)}
          title={`Open ${s.name}`}
        >
          <div style={styles.dot(s.status === 'online')} />
          <span style={styles.name}>{s.name}</span>
          <span style={styles.port}>:{s.port}</span>
        </div>
      ))}
    </div>
  )
}
