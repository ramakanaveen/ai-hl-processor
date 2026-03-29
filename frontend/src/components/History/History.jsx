import { useState, useEffect } from 'react'
import { api } from '../../api/client'
import { HeadlineCard } from '../LiveFeed/HeadlineCard'

const PAGE_SIZES = [10, 20, 50]

export function History({ onCorrect, correctionOverrides, activeHeadlineKeys = [] }) {
  const [data, setData] = useState(null)
  const [limit, setLimit] = useState(20)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)

  async function load(lim, off) {
    setLoading(true)
    try {
      const result = await api.getHistory(lim, off)
      setData(result)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(limit, offset) }, [limit, offset])

  const total = data?.total ?? 0
  const pages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit)
  const activeSet = new Set(activeHeadlineKeys)
  const items = data?.items ?? []

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>History</h2>
        <div className="panel-controls">
          <label>Show
            <select value={limit} onChange={e => { setLimit(Number(e.target.value)); setOffset(0) }}>
              {PAGE_SIZES.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <span className="total-count">{total} total</span>
        </div>
      </div>

      {loading && <p className="empty-state">Loading…</p>}

      {!loading && items.length === 0 && (
        <p className="empty-state">No analyses stored yet.</p>
      )}

      <div className="card-list">
        {items.map((item, i) => (
          <HeadlineCard
            key={i}
            result={item}
            onCorrect={onCorrect}
            correctionOverrides={correctionOverrides}
            isLive={activeSet.has((item?.headline ?? '').trim().toLowerCase())}
          />
        ))}
      </div>

      {pages > 1 && (
        <div className="pagination">
          <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
            ← Prev
          </button>
          <span>{currentPage + 1} / {pages}</span>
          <button
            disabled={offset + limit >= total}
            onClick={() => setOffset(offset + limit)}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
