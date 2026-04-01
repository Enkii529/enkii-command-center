import React from 'react'

const styles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  label: {
    fontSize: '12px',
    color: '#888',
    fontWeight: 500,
  },
  select: {
    background: '#1a1a2a',
    color: '#e0e0e0',
    border: '1px solid #2a2a3a',
    borderRadius: '8px',
    padding: '8px 12px',
    fontSize: '13px',
    fontFamily: 'Inter, sans-serif',
    cursor: 'pointer',
    outline: 'none',
    minWidth: '200px',
  },
  dot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: '#4ade80',
    display: 'inline-block',
  },
}

export default function ModelSelector({ models, selected, onChange }) {
  return (
    <div style={styles.container}>
      <span style={styles.dot} />
      <span style={styles.label}>AI Model</span>
      <select
        style={styles.select}
        value={selected}
        onChange={(e) => onChange(e.target.value)}
      >
        {models.map((m) => (
          <option key={m.name} value={m.name}>
            {m.name} ({m.parameter_size})
          </option>
        ))}
      </select>
    </div>
  )
}
