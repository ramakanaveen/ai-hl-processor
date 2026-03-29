import { useState } from 'react'

function confidenceClass(conf) {
  if (conf >= 0.7) return 'badge-green'
  if (conf >= 0.5) return 'badge-amber'
  return 'badge-red'
}

export function CurrencyBar({ currency }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="currency-bar">
      <div className="currency-bar-header" onClick={() => setExpanded(!expanded)}>
        <div className="currency-bar-left">
          <span className="currency-code">{currency.currency}</span>
          <span className="event-count">{currency.event_count} event{currency.event_count !== 1 ? 's' : ''}</span>
        </div>
        <div className="currency-bar-right">
          <div className="conf-bar-track">
            <div
              className={`conf-bar-fill ${confidenceClass(currency.max_confidence)}`}
              style={{ width: `${currency.max_confidence * 100}%` }}
            />
          </div>
          <span className="conf-label">{Math.round(currency.max_confidence * 100)}%</span>
          <span className="expand-arrow">{expanded ? '▲' : '▼'}</span>
        </div>
      </div>

      {expanded && (
        <div className="currency-events">
          {currency.events.map((ev, i) => (
            <div key={i} className="currency-event">
              <div className="currency-event-meta">
                <span className={`badge-sm ${confidenceClass(ev.confidence)}`}>
                  {Math.round(ev.confidence * 100)}%
                </span>
                <span className="event-time">
                  {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <p className="event-headline">"{ev.headline}"</p>
              <p className="event-reasoning">→ {ev.reasoning}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
