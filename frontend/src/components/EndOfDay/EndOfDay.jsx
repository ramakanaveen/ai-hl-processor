export function EndOfDay() {
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>End of Day Analysis</h2>
        <span className="badge-coming-soon">Coming soon</span>
      </div>
      <div className="placeholder-box">
        <p>Daily summary will appear here.</p>
        <ul>
          <li>Most-impacted currencies of the day</li>
          <li>Top headlines by confidence</li>
          <li>Cumulative impact graph across all sessions</li>
          <li>Comparison vs. prior day</li>
        </ul>
      </div>
    </div>
  )
}
