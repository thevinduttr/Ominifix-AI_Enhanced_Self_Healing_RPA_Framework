import React from 'react'
import { formatAge } from '../utils/helpers'

function BotsTable({ bots }) {
  const botIds = Object.keys(bots).sort()
  const now = Date.now() / 1000

  if (botIds.length === 0) {
    return (
      <table>
        <thead>
          <tr>
            <th style={{ width: '38%' }}>Bot ID</th>
            <th style={{ width: '20%' }}>Status</th>
            <th style={{ width: '42%' }}>Last Seen</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td colSpan="3" className="muted">
              No bots seen yet
            </td>
          </tr>
        </tbody>
      </table>
    )
  }

  return (
    <table>
      <thead>
        <tr>
          <th style={{ width: '38%' }}>Bot ID</th>
          <th style={{ width: '20%' }}>Status</th>
          <th style={{ width: '42%' }}>Last Seen</th>
        </tr>
      </thead>
      <tbody>
        {botIds.map((id) => {
          const info = bots[id] || {}
          const lastSeen = info.last_seen || 0
          const age = Math.max(0, Math.round(now - lastSeen))
          const status = age > 10 ? 'FAILED' : info.status || 'UNKNOWN'
          const badgeClass =
            status === 'FAILED'
              ? 'badge failed'
              : status === 'RUNNING'
              ? 'badge running'
              : 'badge muted'
          const lastSeenText = lastSeen
            ? new Date(lastSeen * 1000).toLocaleString()
            : 'never'

          return (
            <tr key={id}>
              <td>
                <code>{id}</code>
                {info.meta && (
                  <div className="muted" style={{ marginTop: '6px', fontWeight: 500 }}>
                    {JSON.stringify(info.meta)}
                  </div>
                )}
              </td>
              <td>
                <span className={badgeClass}>{status}</span>
              </td>
              <td>
                <div>{formatAge(age)}</div>
                <div className="muted" style={{ marginTop: '6px' }}>
                  {lastSeenText}
                </div>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

export default BotsTable
