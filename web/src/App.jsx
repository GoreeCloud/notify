import { useCallback, useEffect, useState } from 'react'

const validTopic = /^[a-zA-Z0-9_-]{1,64}$/
const describeTime = (value) => new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
const apiPath = (topic) => '/api/v1/topics/' + encodeURIComponent(topic)

export default function App() {
  const [token, setToken] = useState('')
  const [topic, setTopic] = useState('general')
  const [draftTopic, setDraftTopic] = useState('general')
  const [messages, setMessages] = useState([])
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [priority, setPriority] = useState('3')
  const [status, setStatus] = useState('Enter a token to connect')
  const [posting, setPosting] = useState(false)
  const enabled = token.length >= 32 && validTopic.test(topic)

  const load = useCallback(async (signal) => {
    if (!enabled) return
    const response = await fetch(apiPath(topic) + '/messages?limit=100', {
      headers: { Authorization: 'Bearer ' + token },
      signal,
      cache: 'no-store',
    })
    const result = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(result.error || 'HTTP ' + response.status)
    setMessages(result.messages || [])
    setStatus('Connected · notifications are private to this server')
  }, [enabled, token, topic])

  useEffect(() => {
    if (!enabled) {
      setMessages([])
      setStatus('Enter a token to connect')
      return
    }
    const controller = new AbortController()
    const refresh = () => load(controller.signal).catch((err) => {
      if (err.name !== 'AbortError') setStatus('Connection error: ' + err.message)
    })
    refresh()
    const interval = setInterval(refresh, 30000)
    return () => { controller.abort(); clearInterval(interval) }
  }, [enabled, load])

  useEffect(() => {
    if (!enabled) return
    const controller = new AbortController()
    let retryTimer
    async function stream() {
      try {
        const response = await fetch(apiPath(topic) + '/events', {
          headers: { Authorization: 'Bearer ' + token, Accept: 'text/event-stream' },
          cache: 'no-store',
          signal: controller.signal,
        })
        if (!response.ok || !response.body) throw new Error('Live stream unavailable')
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let pending = ''
        while (!controller.signal.aborted) {
          const { value, done } = await reader.read()
          if (done) break
          pending += decoder.decode(value, { stream: true })
          const events = pending.split('\n\n')
          pending = events.pop() || ''
          for (const event of events) {
            const line = event.split('\n').find((entry) => entry.startsWith('data: '))
            if (!line) continue
            try {
              const message = JSON.parse(line.slice(6))
              setMessages((previous) => [message, ...previous.filter((m) => m.id !== message.id)].slice(0, 100))
            } catch { /* ignore malformed stream frame; next poll reconciles */ }
          }
        }
      } catch (error) {
        if (!controller.signal.aborted) setStatus('Stream interrupted; history polling remains active')
      }
      if (!controller.signal.aborted) retryTimer = setTimeout(stream, 3000)
    }
    stream()
    return () => { controller.abort(); clearTimeout(retryTimer) }
  }, [enabled, token, topic])

  async function publish(event) {
    event.preventDefault()
    if (!enabled || !body.trim()) return
    setPosting(true)
    try {
      const response = await fetch(apiPath(topic) + '/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
        body: JSON.stringify({ title, body, priority: Number(priority) }),
      })
      const result = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(result.error || 'HTTP ' + response.status)
      setTitle('')
      setBody('')
      await load()
    } catch (err) {
      setStatus('Publish failed: ' + err.message)
    } finally {
      setPosting(false)
    }
  }

  return (
    <div className="gc-app notify-app" data-gc-theme="light">
      <header className="notify-header">
        <div className="gc-container notify-header-inner">
          <div className="notify-logo" aria-hidden="true">N</div>
          <div><div className="gc-heading">GoreeCloud Notify</div><div className="gc-support">Your alerts, your infrastructure</div></div>
          <span className="notify-local-pill">Self-hosted</span>
        </div>
      </header>
      <main className="gc-container notify-main">
        <div className="notify-intro">
          <div><div className="notify-overline">MESSAGE CENTER</div><h1 className="gc-title">Stay in the know.</h1><p className="gc-support">Publish and follow private notification topics, without advertising or tracking.</p></div>
          <div className="notify-live" role="status">{status}</div>
        </div>
        <section className="gc-card notify-connection" aria-label="Connection settings">
          <div className="notify-connection-title"><h2 className="gc-heading">Connection</h2><span className="gc-support">Token stays in this browser tab's memory</span></div>
          <div className="notify-settings">
            <div className="gc-field"><label htmlFor="token">Server API token</label><input id="token" className="gc-input" type="password" autoComplete="off" spellCheck="false" value={token} onChange={(e) => setToken(e.target.value)} placeholder="Paste your private token" /></div>
            <form className="gc-field" onSubmit={(e) => { e.preventDefault(); if (validTopic.test(draftTopic)) setTopic(draftTopic) }}>
              <label htmlFor="topic">Topic</label><div className="notify-topic-entry"><input id="topic" className="gc-input" value={draftTopic} maxLength={64} onChange={(e) => setDraftTopic(e.target.value)} aria-invalid={!validTopic.test(draftTopic)} /><button className="gc-button gc-button--secondary" type="submit" disabled={!validTopic.test(draftTopic)}>Open</button></div>
            </form>
          </div>
        </section>
        <div className="notify-columns">
          <section className="gc-card" aria-labelledby="compose-title">
            <div className="notify-section-header"><h2 id="compose-title" className="gc-heading">New notification</h2><span className="gc-support">#{topic}</span></div>
            <form className="gc-stack" onSubmit={publish}>
              <div className="gc-field"><label htmlFor="title">Title <span className="gc-support">(optional)</span></label><input className="gc-input" id="title" maxLength={160} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Status update" /></div>
              <div className="gc-field"><label htmlFor="message">Message</label><textarea className="gc-textarea" id="message" required maxLength={4096} rows={5} value={body} onChange={(e) => setBody(e.target.value)} placeholder="What should your devices know?" /></div>
              <div className="gc-field"><label htmlFor="priority">Priority</label><select className="gc-select" id="priority" value={priority} onChange={(e) => setPriority(e.target.value)}><option value="1">Minimum</option><option value="2">Low</option><option value="3">Default</option><option value="4">High</option><option value="5">Urgent</option></select></div>
              <button className="gc-button notify-send" type="submit" disabled={!enabled || posting || !body.trim()}>{posting ? 'Publishing…' : 'Publish notification'}</button>
            </form>
          </section>
          <section className="gc-card notify-inbox" aria-labelledby="inbox-title">
            <div className="notify-section-header"><h2 className="gc-heading" id="inbox-title">Inbox</h2><span className="notify-count">{messages.length} recent</span></div>
            {!enabled ? <div className="notify-empty">Enter your server token to load this topic.</div> :
              messages.length === 0 ? <div className="notify-empty">No messages yet. Publish a notification to see it here.</div> :
                <ul className="notify-message-list">{messages.map((message) => <li className="notify-message" key={message.id}>
                  <div className="notify-message-top"><span className="notify-priority">P{message.priority}</span><time dateTime={message.created_at}>{describeTime(message.created_at)}</time></div>
                  {message.title && <h3 className="gc-heading">{message.title}</h3>}
                  <p>{message.body}</p>
                </li>)}</ul>}
          </section>
        </div>
        <footer className="gc-support notify-footer">GoreeCloud UI · No analytics · Single-server preview</footer>
      </main>
    </div>
  )
}
