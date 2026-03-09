import React, { useState } from 'react'
import { escapeHtml } from '../utils/helpers'

function FailureModal({ failure, onClose }) {
  const [showDom, setShowDom] = useState(false)
  const soundLabel = (failure?.metadata && failure.metadata.sound) || 'Alert tone'
  const locatorReport = failure?.locator_report
  const healingResult = failure?.healing_result || locatorReport?.healing_result
  const healingRequest = failure?.healing_request || locatorReport?.healing_request
  const healingError = failure?.healing_error || locatorReport?.healing_error
  const healingSummary = healingResult?.healing_summary
  const ptqaResult = failure?.ptqa_result
  const ptqaError = failure?.ptqa_error

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

    if (healingSummary?.status) parts.push(['Healing Status', healingSummary.status])
    if (healingSummary?.strategy_used)
      parts.push(['Healing Strategy', healingSummary.strategy_used])
    if (healingSummary?.new_locator)
      parts.push(['Healed Locator', healingSummary.new_locator])
    if (healingSummary?.validation?.reason)
      parts.push(['Healing Reason', healingSummary.validation.reason])
    if (healingError) parts.push(['Healing Error', healingError])

    if (ptqaResult?.recommendation)
      parts.push(['PTQA Recommendation', ptqaResult.recommendation])
    if (ptqaResult?.risk_level) parts.push(['PTQA Risk', ptqaResult.risk_level])
    if (typeof ptqaResult?.confidence === 'number')
      parts.push(['PTQA Confidence', `${Math.round(ptqaResult.confidence * 100)}%`])
    if (typeof ptqaResult?.will_work_probability === 'number')
      parts.push([
        'PTQA Will Work',
        `${Math.round(ptqaResult.will_work_probability * 100)}%`,
      ])
    if (ptqaError) parts.push(['PTQA Error', ptqaError])

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

          {healingResult && (
            <>
              <div style={{ marginTop: '12px' }}>
                <strong>AI Healing Output</strong>
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
                {JSON.stringify(healingResult, null, 2)}
              </pre>
            </>
          )}

          {healingRequest && (
            <>
              <div style={{ marginTop: '12px' }}>
                <strong>Healing Request Body</strong>
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
                {JSON.stringify(healingRequest, null, 2)}
              </pre>
            </>
          )}

          {ptqaResult && (
            <>
              <div style={{ marginTop: '20px', marginBottom: '12px' }}>
                <strong style={{ fontSize: '16px' }}>PTQA Service Details</strong>
              </div>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                  gap: '12px',
                  marginBottom: '16px',
                }}
              >
                {/* Recommendation */}
                <div
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.06)',
                  }}
                >
                  <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '6px' }}>
                    Recommendation
                  </div>
                  <div
                    style={{
                      fontWeight: 700,
                      color:
                        ptqaResult.recommendation === 'APPROVE_HEALING'
                          ? '#4ade80'
                          : ptqaResult.recommendation === 'BLOCK_HEALING'
                          ? '#f87171'
                          : '#fbbf24',
                    }}
                  >
                    {ptqaResult.recommendation || '-'}
                  </div>
                </div>

                {/* Risk Level */}
                <div
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.06)',
                  }}
                >
                  <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '6px' }}>
                    Risk Level
                  </div>
                  <div style={{ fontWeight: 700 }}>{ptqaResult.risk_level || '-'}</div>
                </div>

                {/* Confidence */}
                <div
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.06)',
                  }}
                >
                  <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '6px' }}>
                    Confidence
                  </div>
                  <div style={{ fontWeight: 700 }}>
                    {typeof ptqaResult.confidence === 'number'
                      ? `${Math.round(ptqaResult.confidence * 100)}%`
                      : '-'}
                  </div>
                </div>

                {/* Will Work Probability */}
                <div
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.06)',
                  }}
                >
                  <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '6px' }}>
                    Will Work Probability
                  </div>
                  <div style={{ fontWeight: 700 }}>
                    {typeof ptqaResult.will_work_probability === 'number'
                      ? `${Math.round(ptqaResult.will_work_probability * 100)}%`
                      : '-'}
                  </div>
                </div>

                {/* Model Name */}
                <div
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.06)',
                  }}
                >
                  <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '6px' }}>
                    Model Name
                  </div>
                  <div style={{ fontWeight: 700, fontSize: '14px' }}>
                    {ptqaResult.model_name || '-'}
                  </div>
                </div>

                {/* Pass Rate (Before -> After) */}
                {ptqaResult.before_results && ptqaResult.after_results && (
                  <div
                    style={{
                      padding: '12px',
                      borderRadius: '8px',
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid rgba(255,255,255,0.06)',
                    }}
                  >
                    <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '6px' }}>
                      Pass Rate (Before → After)
                    </div>
                    <div style={{ fontWeight: 700 }}>
                      {(() => {
                        const beforeTotal = ptqaResult.before_results.total_tests || 0
                        const beforePassed = ptqaResult.before_results.passed_tests || 0
                        const afterTotal = ptqaResult.after_results.total_tests || 0
                        const afterPassed = ptqaResult.after_results.passed_tests || 0
                        const beforeRate =
                          beforeTotal > 0 ? ((beforePassed / beforeTotal) * 100).toFixed(1) : '0.0'
                        const afterRate =
                          afterTotal > 0 ? ((afterPassed / afterTotal) * 100).toFixed(1) : '0.0'
                        return `${beforeRate}% → ${afterRate}%`
                      })()}
                    </div>
                  </div>
                )}

                {/* Pass Rate Delta */}
                {ptqaResult.before_results && ptqaResult.after_results && (
                  <div
                    style={{
                      padding: '12px',
                      borderRadius: '8px',
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid rgba(255,255,255,0.06)',
                    }}
                  >
                    <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '6px' }}>
                      Pass Rate Delta
                    </div>
                    <div style={{ fontWeight: 700 }}>
                      {(() => {
                        const beforeTotal = ptqaResult.before_results.total_tests || 0
                        const beforePassed = ptqaResult.before_results.passed_tests || 0
                        const afterTotal = ptqaResult.after_results.total_tests || 0
                        const afterPassed = ptqaResult.after_results.passed_tests || 0
                        const beforeRate = beforeTotal > 0 ? (beforePassed / beforeTotal) * 100 : 0
                        const afterRate = afterTotal > 0 ? (afterPassed / afterTotal) * 100 : 0
                        const delta = afterRate - beforeRate
                        const color = delta > 0 ? '#4ade80' : delta < 0 ? '#f87171' : '#94a3b8'
                        const sign = delta > 0 ? '+' : ''
                        return (
                          <span style={{ color }}>
                            {sign}
                            {delta.toFixed(1)}%
                          </span>
                        )
                      })()}
                    </div>
                  </div>
                )}

                {/* Latency Delta */}
                {ptqaResult.before_results && ptqaResult.after_results && (
                  <div
                    style={{
                      padding: '12px',
                      borderRadius: '8px',
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid rgba(255,255,255,0.06)',
                    }}
                  >
                    <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '6px' }}>
                      Latency Delta
                    </div>
                    <div style={{ fontWeight: 700 }}>
                      {(() => {
                        const beforeLatency = ptqaResult.before_results.avg_exec_time || 0
                        const afterLatency = ptqaResult.after_results.avg_exec_time || 0
                        const delta = afterLatency - beforeLatency
                        const color = delta < 0 ? '#4ade80' : delta > 0 ? '#f87171' : '#94a3b8'
                        const sign = delta > 0 ? '+' : ''
                        return (
                          <span style={{ color }}>
                            {sign}
                            {delta.toFixed(2)}s
                          </span>
                        )
                      })()}
                    </div>
                  </div>
                )}

                {/* Healing Effect */}
                {typeof ptqaResult.healing_accuracy === 'number' && (
                  <div
                    style={{
                      padding: '12px',
                      borderRadius: '8px',
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid rgba(255,255,255,0.06)',
                    }}
                  >
                    <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '6px' }}>
                      Healing Effect
                    </div>
                    <div style={{ fontWeight: 700 }}>
                      {(ptqaResult.healing_accuracy * 100).toFixed(1)}%
                    </div>
                  </div>
                )}

                {/* Has Regression */}
                <div
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.06)',
                  }}
                >
                  <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '6px' }}>
                    Has Regression
                  </div>
                  <div style={{ fontWeight: 700 }}>
                    {(() => {
                      if (!ptqaResult.before_results || !ptqaResult.after_results) return '-'
                      const beforeTotal = ptqaResult.before_results.total_tests || 0
                      const beforePassed = ptqaResult.before_results.passed_tests || 0
                      const afterTotal = ptqaResult.after_results.total_tests || 0
                      const afterPassed = ptqaResult.after_results.passed_tests || 0
                      const beforeRate = beforeTotal > 0 ? (beforePassed / beforeTotal) * 100 : 0
                      const afterRate = afterTotal > 0 ? (afterPassed / afterTotal) * 100 : 0
                      const hasRegression = afterRate < beforeRate
                      return (
                        <span style={{ color: hasRegression ? '#f87171' : '#4ade80' }}>
                          {hasRegression ? 'Yes' : 'No'}
                        </span>
                      )
                    })()}
                  </div>
                </div>
              </div>

              <div style={{ marginTop: '12px' }}>
                <strong>PTQA Raw Output</strong>
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
                {JSON.stringify(ptqaResult, null, 2)}
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
