import React, { useState, useEffect } from 'react'
import { fetchActivity } from '../api.js'

const styles = {
  container: {
    background: '#12121a',
    border: '1px solid #1e1e2e',
    borderRadius: '12px',
    padding: '16px',
    maxHeight: '340px',
    overflow: 'auto',
  },
  header: {
    fontSize: '14px',
    fontWeight: 700,
    color: '#fff',
    marginBottom: '12px',
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '8px 0',
    borderBottom: '1px solid #1a1a2a',
  },
  badge: (type) => ({
    fontSize: '10px',
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: '4px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    flexShrink: 0,
    background: type === 'task' ? '#1a1a3a' : type === 'document' ? '#1a2a1a' : '#2a1a1a',
    color: type === 'task' ? '#818cf8' : type === 'document' ? '#4ade80' : '#fb923c',
  }),
  title: {
    fontSize: '13px',
    color: '#e0e0e0',
    flex: 1,
  },
  status: {
    fontSize: '11px',
    color: '#666',
    flexShrink: 0,
  },
  empty: {
    fontSize: '13px',
    color: '#666',
    textAlign: 'center',
    padding: '20px',
  },
}

export default function ActivityFeed() {
  const [items, setItems] = useState([])

  useEffect(() => {
    const load = () => {
      fetchActivity(15)
        .then((data) => setItems(data.items || []))
        .catch(() => {})
    }
    load()
    const interval = setInterval(load, 15000)
    return () => clearInterval(interval)
  }, [])

  if (items.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>Activity Feed</div>
        <div style={styles.empty}>No activity yet. Use the AI chat to create tasks and documents.</div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>Activity Feed</div>
      {items.map((item, i) => (
        <div key={`${item.item_type}-${item.id}-${i}`} style={styles.item}>
          <span style={styles.badge(item.item_type)}>
            {item.item_type}
          </span>
          <span style={styles.title}>{item.title}</span>
          <span style={styles.status}>
            {item.status || item.stage || item.priority || ''}
          </span>
        </div>
      ))}
    </div>
  )
}
