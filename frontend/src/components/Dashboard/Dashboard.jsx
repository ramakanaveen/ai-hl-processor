import { usePolling } from '../../hooks/usePolling'
import { api } from '../../api/client'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

function StatTile({ label, value, sub }) {
  return (
    <div className="stat-tile">
      <span className="stat-value">{value ?? '—'}</span>
      <span className="stat-label">{label}</span>
      {sub && <span className="stat-sub">{sub}</span>}
    </div>
  )
}

export function Dashboard() {
  const { data: stats } = usePolling(api.getStats, 30000)
  const { data: throughput } = usePolling(() => api.getThroughput(24, 60), 300000)

  const chartData = (throughput?.buckets ?? []).map(b => ({
    time: new Date(b.bucket).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    count: b.count,
  }))

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>System Dashboard</h2>
        <span className="env-badge">{stats?.environment ?? '…'}</span>
      </div>

      <div className="stat-grid">
        <StatTile
          label="Total Analyses"
          value={stats?.total_analyses?.toLocaleString()}
        />
        <StatTile
          label="Per Hour (avg)"
          value={stats?.analyses_per_hour}
        />
        <StatTile
          label="SSE Clients"
          value={stats?.active_sse_clients}
        />
        <StatTile
          label="Redis"
          value={stats?.redis_available ? '✓ Connected' : '✗ Offline'}
          sub={stats?.redis_available ? null : 'file memory only'}
        />
      </div>

      <h3 className="chart-title">Analyses per hour (last 24h)</h3>
      {chartData.length === 0 ? (
        <p className="empty-state">No data yet</p>
      ) : (
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData}>
              <XAxis dataKey="time" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#4f87ff"
                fill="#4f87ff22"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
