import { useState } from 'react'
import { mergeResultWithOverride } from '../../utils/results'

function confidenceClass(conf) {
  if (conf >= 0.7) return 'badge-green'
  if (conf >= 0.5) return 'badge-amber'
  return 'badge-red'
}

function timeAgo(isoStr) {
  try {
    const diff = (Date.now() - new Date(isoStr).getTime()) / 1000
    if (diff < 60) return `${Math.round(diff)}s ago`
    if (diff < 3600) return `${Math.round(diff / 60)}m ago`
    return new Date(isoStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function formatTimestamp(isoStr) {
  try {
    return new Date(isoStr).toLocaleString([], {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

export function HeadlineCard({
  result,
  onCorrect,
  correctionOverrides,
  defaultExpanded = false,
  isLive = false,
}) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const data = mergeResultWithOverride(result, correctionOverrides)

  if (!data) return null

  const entities = data.impacted_entities ?? []
  const hasError = !!data.error
  const ts = data.timestamp
  const lastModifiedAt = data.last_modified_at ?? ts
  const isCorrected = !!data.is_corrected
  const correctedBy = data.corrected_by || 'user'

  return (
    <div className={`card ${hasError ? 'card-error' : ''}`}>
      <div className="card-header">
        <span className="card-time">{timeAgo(ts)}</span>
        {onCorrect && (
          <button className="btn-correct" onClick={() => onCorrect(data)}>
            Adjust
          </button>
        )}
      </div>

      <p className="card-headline">{data.headline}</p>

      {(isCorrected || isLive) && (
        <div className="card-meta">
          {isLive && (
            <span className="badge badge-amber">Live</span>
          )}
          {isCorrected && (
            <>
              <span className="badge badge-blue">Edited</span>
              <span className="card-meta-text">
                Updated by {correctedBy} on {formatTimestamp(lastModifiedAt)}
              </span>
            </>
          )}
        </div>
      )}

      {hasError && <p className="card-error-msg">Error: {data.error}</p>}

      {!hasError && entities.length === 0 && (
        <p className="card-no-impact">No significant currency impact detected</p>
      )}

      {!hasError && entities.length > 0 && (
        <div className="badges">
          {entities.map((e) => {
            const ccy = e.currency?.value ?? e.currency
            return (
              <span key={ccy} className={`badge ${confidenceClass(e.confidence)}`}>
                {ccy} {Math.round(e.confidence * 100)}%
              </span>
            )
          })}
        </div>
      )}

      {!hasError && entities.length > 0 && (
        <>
          <button className="btn-expand" onClick={() => setExpanded(!expanded)}>
            {expanded ? '▲ Hide reasoning' : '▼ Show reasoning'}
          </button>
          {expanded && (
            <div className="reasoning">
              {entities.map((e) => {
                const ccy = e.currency?.value ?? e.currency
                return (
                  <div key={ccy} className="reasoning-row">
                    <span className={`badge-sm ${confidenceClass(e.confidence)}`}>{ccy}</span>
                    <span>{e.reasoning}</span>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}

      <div className="card-footer">
        <span>{data.model_used}</span>
        <span>Last modified {timeAgo(lastModifiedAt)}</span>
        {data.processing_time_ms && (
          <span>{Math.round(data.processing_time_ms)}ms</span>
        )}
      </div>
    </div>
  )
}
