import { useState } from 'react'
import { usePolling } from '../../hooks/usePolling'
import { api } from '../../api/client'
import { CurrencyBar } from './CurrencyBar'

const WINDOWS = [15, 30, 60, 120]

export function Insights() {
  const [window, setWindow] = useState(60)
  const { data, loading } = usePolling(() => api.getInsights(window), 30000, [window])

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Market Pressures</h2>
        <div className="panel-controls">
          {WINDOWS.map(w => (
            <button
              key={w}
              className={`btn-window ${window === w ? 'active' : ''}`}
              onClick={() => setWindow(w)}
            >
              {w}m
            </button>
          ))}
        </div>
      </div>

      {!data?.redis_available && (
        <p className="empty-state warning">Redis unavailable — impact graph offline</p>
      )}

      {loading && <p className="empty-state">Loading…</p>}

      {data?.redis_available && !loading && data.currencies.length === 0 && (
        <p className="empty-state">No activity in the last {window} minutes</p>
      )}

      <div className="insights-list">
        {(data?.currencies ?? []).map(ccy => (
          <CurrencyBar key={ccy.currency} currency={ccy} />
        ))}
      </div>
    </div>
  )
}
