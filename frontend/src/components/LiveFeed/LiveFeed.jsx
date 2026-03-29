import { useEffect, useMemo, useState } from 'react'
import { useSSE } from '../../hooks/useSSE'
import { HeadlineCard } from './HeadlineCard'
import { normalizeHeadline } from '../../utils/results'

const LIVE_WINDOW_OPTIONS = [
  { label: '30s', value: 30 * 1000 },
  { label: '1m', value: 60 * 1000 },
  { label: '2m', value: 2 * 60 * 1000 },
  { label: '5m', value: 5 * 60 * 1000 },
  { label: '10m', value: 10 * 60 * 1000 },
]

function getEventTimestamp(event) {
  const data = event?.data ?? event
  return event?.timestamp ?? data?.last_modified_at ?? data?.timestamp ?? null
}

export function LiveFeed({
  onCorrect,
  correctionOverrides,
  onActiveHeadlinesChange,
  liveWindowMs,
  onLiveWindowChange,
}) {
  const { events, status } = useSSE('/events')
  const [now, setNow] = useState(Date.now())

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])

  const liveEvents = useMemo(() => (
    events.filter((event) => {
      const ts = getEventTimestamp(event)
      const ms = ts ? new Date(ts).getTime() : NaN
      return Number.isFinite(ms) && now - ms <= liveWindowMs
    })
  ), [events, now, liveWindowMs])

  useEffect(() => {
    const activeKeys = liveEvents
      .map(event => normalizeHeadline((event?.data ?? event)?.headline))
      .filter(Boolean)
    onActiveHeadlinesChange?.(activeKeys)
  }, [liveEvents, onActiveHeadlinesChange])

  const statusDot = {
    open: 'dot-green',
    connecting: 'dot-amber',
    closed: 'dot-red',
  }[status] ?? 'dot-red'

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Live Feed</h2>
        <div className="panel-controls">
          <label className="inline-control">
            Review window
            <select
              value={liveWindowMs}
              onChange={(e) => onLiveWindowChange?.(Number(e.target.value))}
            >
              {LIVE_WINDOW_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <span className={`dot ${statusDot}`} title={status} />
        </div>
      </div>

      {liveEvents.length === 0 && (
        <p className="empty-state">
          {status === 'open'
            ? 'Waiting for fresh headlines…'
            : status === 'connecting'
            ? 'Connecting to SSE stream…'
            : 'Disconnected — retrying…'}
        </p>
      )}

      <div className="card-list">
        {liveEvents.map((ev, i) => (
          <HeadlineCard
            key={i}
            result={ev}
            onCorrect={onCorrect}
            correctionOverrides={correctionOverrides}
            defaultExpanded
          />
        ))}
      </div>
    </div>
  )
}
