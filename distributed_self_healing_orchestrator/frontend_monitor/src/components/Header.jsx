import React from 'react'

function Header({ lastUpdate, onRefresh }) {
  return (
    <header>
      <div>
        <h1>Bots Monitor</h1>
        <div className="sub">Real-time view of bot heartbeats</div>
      </div>

      <div className="controls">
        <div className="muted">
          Last update: <strong>{lastUpdate}</strong>
        </div>
        <button className="btn" onClick={onRefresh}>
          Refresh
        </button>
      </div>
    </header>
  )
}

export default Header
