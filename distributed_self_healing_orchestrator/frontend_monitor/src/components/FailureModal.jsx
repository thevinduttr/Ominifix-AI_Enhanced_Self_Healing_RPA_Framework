import React, { useState } from 'react'
import { escapeHtml } from '../utils/helpers'

function FailureModal({ failure, onClose }) {
  const [showDom, setShowDom] = useState(false)
  const soundLabel = (failure?.metadata && failure.metadata.sound) || 'Alert tone'
  const locatorReport = failure?.locator_report

  const handleOverlayClick = (e) => {
    if (e.target.id === 'failure-overlay') {
      onClose()
    }
  }

  const renderFields = () => {
    const parts = []

    if (failure.failure_type) parts.push(['Type', failure.failure_type])
    if (failure.last_action || failure.failed_action)
      parts.push(['Last action', failure.failed_action || failure.last_action])
    if (failure.strategy) parts.push(['Strategy', failure.strategy])
    if (failure.priority) parts.push(['Priority', failure.priority])
    if (failure.category)
      parts.push([
        'Category',
        failure.category +
          (failure.confidence ? ` (${Math.round(failure.confidence * 100)}%)` : ''),
      ])
    if (failure.category || failure.failure_type)
      parts.push(['Classification Error Type', failure.category || failure.failure_type])
    parts.push(['Sound', soundLabel])

    if (failure.page_url) parts.push(['Page URL', failure.page_url])
    if (failure.element_role) parts.push(['Element Role', failure.element_role])
    if (failure.expected_text) parts.push(['Expected Text', failure.expected_text])
    if (failure.old_locator) parts.push(['Old Locator', failure.old_locator])
    if (failure.old_locator_type) parts.push(['Locator Type', failure.old_locator_type])
    if (failure.screenshot_path) parts.push(['Screenshot', failure.screenshot_path])
    if (failure.page_html)
      parts.push(['Page HTML Size', `${(failure.page_html.length / 1024).toFixed(2)} KB`])

    if (failure.metadata) {
      if (failure.metadata.bot_id) parts.push(['Metadata: Bot ID', failure.metadata.bot_id])
      if (failure.metadata.workflow_step)
        parts.push(['Workflow Step', failure.metadata.workflow_step])
      if (failure.metadata.base_url) parts.push(['Base URL', failure.metadata.base_url])
      if (failure.metadata.target_url) parts.push(['Target URL', failure.metadata.target_url])
      if (failure.metadata.timestamp)
        parts.push(['Metadata Timestamp', new Date(failure.metadata.timestamp).toLocaleString()])
      if (failure.metadata.error_type) parts.push(['Error Type', failure.metadata.error_type])
    }

    if (locatorReport?.metadata?.report_id)
      parts.push(['Locator Report ID', locatorReport.metadata.report_id])
    if (locatorReport?.metadata?.run_id) parts.push(['Locator Run ID', locatorReport.metadata.run_id])
    if (locatorReport?.element_candidate?.strategy)
      parts.push(['Locator Strategy', locatorReport.element_candidate.strategy])
    if (typeof locatorReport?.element_candidate?.score === 'number')
      parts.push(['Locator Score', locatorReport.element_candidate.score.toFixed(3)])
    if (locatorReport?.element_candidate?.xpath)
      parts.push(['Locator XPath', locatorReport.element_candidate.xpath])
    if (locatorReport?.element_candidate?.css)
      parts.push(['Locator CSS', locatorReport.element_candidate.css])

    parts.push(['Bot ID', failure.botId || ''])
    parts.push([
      'Timestamp',
      failure.timestamp ? new Date(failure.timestamp * 1000).toLocaleString() : '',
    ])

    return parts.map((p, idx) => {
      const key = escapeHtml(p[0])
      const val = escapeHtml(String(p[1] || ''))

      let valDisplay
      if (p[0] === 'Category') {
        valDisplay = <span className="category-badge">{val}</span>
      } else if (p[0].includes('URL') || p[0] === 'Screenshot') {
        valDisplay = (
          <span style={{ wordBreak: 'break-all', fontSize: '0.85rem' }}>{val}</span>
        )
      } else if (p[0].includes('Locator')) {
        valDisplay = (
          <code
            style={{
              background: 'rgba(0,0,0,0.3)',
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '0.85rem',
              display: 'block',
              marginTop: '4px',
            }}
          >
            {val}
          </code>
        )
      } else {
        valDisplay = val
      }

      return (
        <div
          key={idx}
          style={{
            minWidth: '160px',
            padding: '8px',
            borderRadius: '8px',
            background: 'rgba(255,255,255,0.02)',
          }}
        >
          <div style={{ fontSize: '12px', color: 'var(--muted)' }}>{key}</div>
          <div style={{ fontWeight: 700, marginTop: '6px' }}>{valDisplay}</div>
        </div>
      )
    })
  }

  const htmlContent = failure.page_html || failure.dom

  return (
    <div
      id="failure-modal"
      style={{
        display: 'flex',
        position: 'fixed',
        inset: 0,
        zIndex: 1200,
        alignItems: 'center',
        justifyContent: 'center',
      }}
      onClick={handleOverlayClick}
    >
      <div
        id="failure-overlay"
        style={{ position: 'absolute', inset: 0, background: 'rgba(2,6,23,0.6)' }}
      />
      <div
        style={{
          position: 'relative',
          maxWidth: '900px',
          width: 'calc(100% - 40px)',
          margin: 'auto',
          zIndex: 1210,
        }}
      >
        <div
          style={{
            background: 'var(--card)',
            borderRadius: '10px',
            padding: '16px',
            color: '#e6eef8',
            boxShadow: '0 12px 40px rgba(2,6,23,0.6)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontWeight: 700 }}>Failure Details</div>
            <button
              onClick={onClose}
              className="btn"
              style={{
                background: 'transparent',
                color: 'var(--muted)',
                border: '1px solid rgba(255,255,255,0.04)',
              }}
            >
              Close
            </button>
          </div>

          <div style={{ marginTop: '12px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            {renderFields()}
          </div>

          {htmlContent && (
            <div style={{ marginTop: '12px', display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button
                onClick={() => setShowDom(!showDom)}
                className="btn"
                style={{
                  background: 'transparent',
                  color: 'var(--muted)',
                  border: '1px solid rgba(255,255,255,0.04)',
                }}
              >
                {showDom ? 'Hide' : 'Render'} {failure.page_html ? 'Page HTML' : 'DOM'}
              </button>
              <div className="muted">
                (renders DOM snapshot in a sandboxed frame; scripts are blocked)
              </div>
            </div>
          )}

          {showDom && htmlContent && (
            <div
              style={{
                marginTop: '12px',
                borderRadius: '8px',
                overflow: 'hidden',
                border: '1px solid rgba(255,255,255,0.04)',
              }}
            >
              <iframe
                srcDoc={htmlContent}
                sandbox=""
                style={{ width: '100%', height: '500px', border: 0 }}
              />
            </div>
          )}

          {locatorReport && (
            <>
              <div style={{ marginTop: '12px' }}>
                <strong>AI Locator Output</strong>
              </div>
              <pre
                style={{
                  marginTop: '8px',
                  background: 'rgba(0,0,0,0.06)',
                  padding: '12px',
                  borderRadius: '6px',
                  maxHeight: '360px',
                  overflow: 'auto',
                  color: '#e6eef8',
                  fontSize: '13px',
                }}
              >
                {JSON.stringify(locatorReport, null, 2)}
              </pre>
            </>
          )}

          <div style={{ marginTop: '12px' }}>
            <strong>Raw JSON</strong>
          </div>
          <pre
            style={{
              marginTop: '8px',
              background: 'rgba(0,0,0,0.06)',
              padding: '12px',
              borderRadius: '6px',
              maxHeight: '420px',
              overflow: 'auto',
              color: '#e6eef8',
              fontSize: '13px',
            }}
          >
            {JSON.stringify(failure, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  )
}

export default FailureModal
