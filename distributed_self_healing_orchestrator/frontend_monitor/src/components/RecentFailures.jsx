import React from 'react'
import { escapeHtml } from '../utils/helpers'

function RecentFailures({ failures, onFailureClick }) {
  if (!failures || failures.length === 0) {
    return <div className="muted">No failures yet</div>
  }

  const recentFailures = failures.slice(0, 10)

  return (
    <div>
      {recentFailures.map((f, idx) => {
        const t = new Date((f.timestamp || 0) * 1000)
        const meta = []
        if (f.failure_type) meta.push(`Type: ${f.failure_type}`)
        if (f.last_action || f.failed_action)
          meta.push(`Action: ${f.failed_action || f.last_action}`)
        if (f.strategy) meta.push(`Strategy: ${f.strategy}`)
        if (f.priority) meta.push(`Priority: ${f.priority}`)
        if (f.category) meta.push(`Classified: ${f.category}`)
        const soundLabel = (f.metadata && f.metadata.sound) || 'Alert tone'
        if (f.category || f.failure_type) meta.push(`Sound: ${soundLabel}`)
        if (f.locator_report?.metadata?.report_id)
          meta.push(`Locator Report: ${f.locator_report.metadata.report_id}`)

        const categoryBadge = f.category ? (
          <div style={{ marginLeft: '8px', display: 'inline-block' }}>
            <span
              className={
                f.category === 'unknown'
                  ? 'category-badge unknown'
                  : f.confidence && f.confidence >= 0.7
                  ? 'category-badge confident'
                  : 'category-badge'
              }
            >
              {f.category}
              {typeof f.confidence === 'number' ? ` ${Math.round(f.confidence * 100)}%` : ''}
            </span>
          </div>
        ) : null

        return (
          <div
            key={idx}
            className="failure-card"
            onClick={() => onFailureClick(f)}
            style={{ marginBottom: '10px', padding: '10px', borderRadius: '8px' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong>{f.botId || ''}</strong>
                <div className="muted" style={{ marginTop: '4px' }}>
                  {t.toLocaleString()}
                </div>
              </div>
              {categoryBadge}
            </div>
            {f.error && (
              <div style={{ marginTop: '8px', color: '#ffdede', fontSize: '0.9rem' }}>
                {escapeHtml(f.error).slice(0, 240)}
              </div>
            )}
            <div style={{ marginTop: '8px', color: 'var(--muted)', fontSize: '0.85rem' }}>
              {meta.join(' • ')}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default RecentFailures
