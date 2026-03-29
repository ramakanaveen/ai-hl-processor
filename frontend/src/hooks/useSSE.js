import { useEffect, useRef, useState } from 'react'
import { normalizeHeadline } from '../utils/results'

const MAX_EVENTS = 200

export function useSSE(url = '/events') {
  const [events, setEvents] = useState([])
  const [status, setStatus] = useState('connecting') // connecting | open | closed
  const bufferRef = useRef([])
  const timerRef = useRef(null)
  const esRef = useRef(null)

  function flush() {
    setEvents([...bufferRef.current])
  }

  function connect() {
    if (esRef.current) esRef.current.close()

    const es = new EventSource(url)
    esRef.current = es
    setStatus('connecting')

    es.onopen = () => setStatus('open')

    es.onmessage = (e) => {
      try {
        const parsed = JSON.parse(e.data)
        if (parsed?.type === 'analysis_corrected') {
          const key = normalizeHeadline(parsed?.data?.headline)
          bufferRef.current = bufferRef.current.map(event => {
            const eventData = event?.data ?? event
            return normalizeHeadline(eventData?.headline) === key
              ? { ...event, data: parsed.data }
              : event
          })
        } else {
          bufferRef.current = [parsed, ...bufferRef.current].slice(0, MAX_EVENTS)
        }
        // Debounce state updates to avoid 60fps re-renders
        clearTimeout(timerRef.current)
        timerRef.current = setTimeout(flush, 300)
      } catch {
        // ignore malformed messages
      }
    }

    es.onerror = () => {
      setStatus('closed')
      es.close()
      // Auto-reconnect after 3s
      setTimeout(connect, 3000)
    }
  }

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(timerRef.current)
      esRef.current?.close()
    }
  }, [url])

  return { events, status, reconnect: connect }
}
