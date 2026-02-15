import React, { useState, useEffect } from 'react'
import StatusDoughnut from './StatusDoughnut'
import ActiveBotsLine from './ActiveBotsLine'
import RecentFailures from './RecentFailures'

function ChartsPanel({ bots, failures, onFailureClick }) {
  const [historyLabels, setHistoryLabels] = useState([])
  const [historyActive, setHistoryActive] = useState([])

  useEffect(() => {
    const ids = Object.keys(bots || {})
    const now = Date.now() / 1000
    let running = 0

    for (const id of ids) {
      const info = bots[id] || {}
      const lastSeen = info.last_seen || 0
      const age = Math.max(0, Math.round(now - lastSeen))
      if (age <= 10) running++
    }

    const label = new Date().toLocaleTimeString()
    setHistoryLabels((prev) => {
      const updated = [...prev, label]
      return updated.length > 24 ? updated.slice(1) : updated
    })
    setHistoryActive((prev) => {
      const updated = [...prev, running]
      return updated.length > 24 ? updated.slice(1) : updated
    })
  }, [bots])

  const ids = Object.keys(bots || {})
  const now = Date.now() / 1000
  let running = 0
  for (const id of ids) {
    const info = bots[id] || {}
    const lastSeen = info.last_seen || 0
    const age = Math.max(0, Math.round(now - lastSeen))
    if (age <= 10) running++
  }
  const failed = Math.max(0, ids.length - running)

  return (
    <>
      <div className="chart-card card">
        <div className="muted" style={{ marginBottom: '8px', fontWeight: 600 }}>
          Bots Status
        </div>
        <StatusDoughnut running={running} failed={failed} />
      </div>

      <div className="chart-card card">
        <div className="muted" style={{ marginBottom: '8px', fontWeight: 600 }}>
          Active Bots (history)
        </div>
        <ActiveBotsLine labels={historyLabels} data={historyActive} />
      </div>

      <div className="chart-card card">
        <div className="muted" style={{ marginBottom: '8px', fontWeight: 600 }}>
          Recent Failures
        </div>
        <RecentFailures failures={failures} onFailureClick={onFailureClick} />
      </div>
    </>
  )
}

export default ChartsPanel
