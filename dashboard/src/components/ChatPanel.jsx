import React, { useState, useRef, useEffect } from 'react'
import { sendAIAction } from '../api.js'

const styles = {
  container: {
    background: '#12121a',
    border: '1px solid #1e1e2e',
    borderRadius: '12px',
    display: 'flex',
    flexDirection: 'column',
    height: '500px',
  },
  header: {
    padding: '14px 18px',
    borderBottom: '1px solid #1e1e2e',
    fontSize: '14px',
    fontWeight: 700,
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  messages: {
    flex: 1,
    overflow: 'auto',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  message: (isUser) => ({
    alignSelf: isUser ? 'flex-end' : 'flex-start',
    background: isUser ? '#7c6ff7' : '#1a1a2e',
    color: isUser ? '#fff' : '#e0e0e0',
    padding: '10px 14px',
    borderRadius: isUser ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
    maxWidth: '85%',
    fontSize: '13px',
    lineHeight: '1.5',
    wordBreak: 'break-word',
  }),
  actionResult: {
    background: '#0d2818',
    border: '1px solid #166534',
    borderRadius: '8px',
    padding: '8px 12px',
    fontSize: '12px',
    color: '#4ade80',
    marginTop: '4px',
  },
  inputRow: {
    display: 'flex',
    gap: '8px',
    padding: '12px 16px',
    borderTop: '1px solid #1e1e2e',
  },
  input: {
    flex: 1,
    background: '#1a1a2a',
    border: '1px solid #2a2a3a',
    borderRadius: '8px',
    padding: '10px 14px',
    color: '#e0e0e0',
    fontSize: '14px',
    fontFamily: 'Inter, sans-serif',
    outline: 'none',
  },
  sendBtn: {
    background: '#7c6ff7',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: 'Inter, sans-serif',
  },
  sendBtnDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  thinking: {
    color: '#888',
    fontSize: '12px',
    fontStyle: 'italic',
    padding: '8px 14px',
  },
}

export default function ChatPanel({ model }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hey! I\'m your Command Center AI. Ask me anything — create tasks, list documents, summarize text, draft content, or check system status. What would you like to do?', action: null, result: null },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEnd = useRef(null)

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { role: 'user', content: text }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const history = messages
        .filter((m) => m.role !== 'system')
        .slice(-10)
        .map((m) => ({ role: m.role, content: m.content }))

      const data = await sendAIAction(text, model, history)

      const aiMsg = {
        role: 'assistant',
        content: data.response || 'Done.',
        action: data.action_executed,
        result: data.result,
      }
      setMessages((prev) => [...prev, aiMsg])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Something went wrong connecting to the AI. Is Ollama running?', action: null, result: null },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span>&#9889;</span> AI Assistant
        {model && <span style={{ fontSize: '11px', color: '#666', marginLeft: 'auto' }}>{model}</span>}
      </div>

      <div style={styles.messages}>
        {messages.map((msg, i) => (
          <div key={i}>
            <div style={styles.message(msg.role === 'user')}>
              {msg.content}
            </div>
            {msg.result && msg.result.success && (
              <div style={styles.actionResult}>
                Action: {msg.action} — {msg.result.message}
                {msg.result.data && Array.isArray(msg.result.data) && msg.result.data.length > 0 && (
                  <div style={{ marginTop: '6px', fontSize: '11px', color: '#86efac' }}>
                    {msg.result.data.slice(0, 5).map((item, j) => (
                      <div key={j}>
                        {item.title || item.name || item.symbol || JSON.stringify(item).slice(0, 80)}
                      </div>
                    ))}
                    {msg.result.data.length > 5 && <div>...and {msg.result.data.length - 5} more</div>}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && <div style={styles.thinking}>Thinking...</div>}
        <div ref={messagesEnd} />
      </div>

      <div style={styles.inputRow}>
        <input
          style={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask me anything... (create tasks, summarize, draft content)"
          disabled={loading}
        />
        <button
          style={{ ...styles.sendBtn, ...(loading ? styles.sendBtnDisabled : {}) }}
          onClick={handleSend}
          disabled={loading}
        >
          Send
        </button>
      </div>
    </div>
  )
}
