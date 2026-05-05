function formatAge(seconds) {
  if (seconds < 5) return 'now';
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s ago`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m ago`;
}

async function fetchStatus() {
  try {
    const res = await fetch('/status');
    if (!res.ok) throw new Error('Network response was not ok');
    const data = await res.json();
    renderBots(data.bots || {});
    document.getElementById('last-update').textContent = new Date().toLocaleString();
    // update charts based on current data
    updateChartsFromData(data.bots || {});
    // render recent failures list if available
    if (data.failures) { renderFailures(data.failures); }

    // Detect PTQA blocked decisions and show banner/desktop notification
    try {
      checkForPtqaBlocked(data.failures || []);
    } catch (_e) { /* non-fatal */ }
  } catch (e) {
    console.error(e);
    document.getElementById('bots-tbody').innerHTML = '<tr><td colspan="3" class="muted">Error loading status</td></tr>';
  }
}

function clearPtqaBanner() {
  const b = document.getElementById('ptqa-banner');
  const title = document.getElementById('ptqa-banner-title');
  const body = document.getElementById('ptqa-banner-body');
  if (!b) return;
  b.style.display = 'none';
  if (title) title.textContent = 'PTQA: BLOCK_HEALING';
  if (body) body.textContent = '';
}

function showPtqaBanner(failure) {
  const b = document.getElementById('ptqa-banner');
  const title = document.getElementById('ptqa-banner-title');
  const body = document.getElementById('ptqa-banner-body');
  if (!b) return;
  const bot = failure.botId || (failure.metadata && failure.metadata.bot_id) || 'unknown';
  const ptqa = (failure.ptqa_result) ? failure.ptqa_result : (failure.ptqaResult || {});
  const reason = Array.isArray(ptqa.reasons) && ptqa.reasons.length ? String(ptqa.reasons[0]) : (ptqa.reason || failure.error || 'Blocked by PTQA');
  if (title) title.textContent = `PTQA BLOCK on ${bot}`;
  if (body) body.textContent = reason;
  b.style.display = 'block';

  // Make banner clickable to open the failure modal if available
  b.onclick = async () => {
    try {
      // try to resolve latest version of the failure and open modal
      const resolved = await resolveLatestFailure(failure);
      showFailureJson(resolved || failure);
    } catch (e) { console.warn('Could not open failure modal', e); }
  };

  // Desktop notification (request permission if needed)
  try {
    if (typeof Notification !== 'undefined') {
      if (Notification.permission === 'granted') {
        new Notification('PTQA: BLOCK_HEALING', { body: `${bot}: ${reason}` });
      } else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then(p => { if (p === 'granted') new Notification('PTQA: BLOCK_HEALING', { body: `${bot}: ${reason}` }); });
      }
    }
  } catch (_e) { }
}

function checkForPtqaBlocked(failures) {
  if (!Array.isArray(failures) || failures.length === 0) { clearPtqaBanner(); return; }
  // find most recent failure that has PTQA result recommending BLOCK_HEALING
  for (const f of failures) {
    const ptqa = f && (f.ptqa_result || f.ptqaResult || f.ptqa_output || {});
    const rec = (ptqa && ptqa.recommendation) ? String(ptqa.recommendation).toUpperCase() : '';
    if (rec === 'BLOCK_HEALING') {
      showPtqaBanner(f);
      return;
    }
    // Also support raw top-level recommendation field as fallback
    const topRec = (f && f.recommendation) ? String(f.recommendation).toUpperCase() : '';
    if (topRec === 'BLOCK_HEALING') {
      showPtqaBanner(f);
      return;
    }
  }
  clearPtqaBanner();
}

function renderFailures(failures) {
  const el = document.getElementById('recent-failures');
  if (!el) return;
  if (!failures || failures.length === 0) { el.innerHTML = '<div class="muted">No failures yet</div>'; return; }
  const items = failures.slice(0, 10).map((f, idx) => {
    const t = new Date((f.timestamp || 0) * 1000);
    const err = f.error ? `<div style="margin-top:8px;color:#ffdede;font-size:0.9rem">${escapeHtml((f.error || '')).slice(0, 240)}</div>` : '';
    // build category badge with confidence and emphasis
    let categoryBadge = '';
    if (f.category) {
      const conf = (typeof f.confidence === 'number') ? ` ${Math.round(f.confidence * 100)}%` : '';
      const cls = (f.category === 'unknown') ? 'category-badge unknown' : ((f.confidence && f.confidence >= 0.7) ? 'category-badge confident' : 'category-badge');
      categoryBadge = `<div style="margin-left:8px;display:inline-block"><span class="${cls}">${escapeHtml(f.category)}${conf}</span></div>`;
    }
    const meta = [];
    if (f.failure_type) meta.push(`<strong>Type:</strong> ${escapeHtml(f.failure_type)}`);
    if (f.last_action || f.failed_action) meta.push(`<strong>Action:</strong> ${escapeHtml(f.failed_action || f.last_action)}`);
    if (f.strategy) meta.push(`<strong>Strategy:</strong> ${escapeHtml(f.strategy)}`);
    if (f.priority) meta.push(`<strong>Priority:</strong> ${escapeHtml(f.priority)}`);
    if (f.locator_report_id) meta.push(`<strong>Locator Report:</strong> ${escapeHtml(f.locator_report_id)}`);
    if (f.locator_report && f.locator_report.element_candidate) {
      const c = f.locator_report.element_candidate;
      const score = (typeof c.score === 'number') ? c.score.toFixed(3) : 'N/A';
      meta.push(`<strong>Locator:</strong> ${escapeHtml(c.strategy || 'N/A')} (score ${escapeHtml(score)})`);
    }

    // New comprehensive fields display
    const comprehensiveInfo = [];
    if (f.page_url) comprehensiveInfo.push(`<strong>Page URL:</strong> <a href="${escapeHtml(f.page_url)}" target="_blank" style="color:#60a5fa">${escapeHtml(f.page_url).slice(0, 60)}${f.page_url.length > 60 ? '...' : ''}</a>`);
    if (f.element_role) comprehensiveInfo.push(`<strong>Element Role:</strong> ${escapeHtml(f.element_role)}`);
    if (f.expected_text) comprehensiveInfo.push(`<strong>Expected Text:</strong> ${escapeHtml(f.expected_text).slice(0, 50)}${f.expected_text.length > 50 ? '...' : ''}`);
    if (f.old_locator) comprehensiveInfo.push(`<strong>Old Locator:</strong> <code style="background:rgba(0,0,0,0.3);padding:2px 6px;border-radius:4px">${escapeHtml(f.old_locator).slice(0, 60)}${f.old_locator.length > 60 ? '...' : ''}</code>`);
    if (f.old_locator_type) comprehensiveInfo.push(`<strong>Locator Type:</strong> ${escapeHtml(f.old_locator_type)}`);
    if (f.screenshot_path) comprehensiveInfo.push(`<strong>Screenshot:</strong> <span style="color:#10b981">${escapeHtml(f.screenshot_path.split('/').pop())}</span>`);

    const comprehensiveHtml = comprehensiveInfo.length > 0 ? `<div style="margin-top:8px;color:#cbd5e1;font-size:0.85rem;line-height:1.8">${comprehensiveInfo.join('<br>')}</div>` : '';

    const domSnippet = f.dom ? escapeHtml(f.dom).slice(0, 200) + (f.dom.length > 200 ? '...' : '') : '';
    const domHtml = f.dom ? `<details style="margin-top:8px"><summary style="cursor:pointer">View DOM snapshot</summary><pre style="white-space:pre-wrap;max-height:220px;overflow:auto;background:rgba(0,0,0,0.04);padding:8px;border-radius:6px">${escapeHtml(f.dom)}</pre></details>` : '';

    // Page HTML info
    const pageHtmlSize = f.page_html ? (f.page_html.length / 1024).toFixed(2) : null;
    const pageHtmlInfo = pageHtmlSize ? `<div style="margin-top:8px;color:#fbbf24;font-size:0.85rem"><strong>Page HTML:</strong> ${pageHtmlSize} KB captured</div>` : '';

    return `
      <div class="failure-card" data-idx="${idx}" style="margin-bottom:10px;padding:10px;border-radius:8px;background:rgba(255,255,255,0.02);cursor:pointer">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div><strong>${escapeHtml(f.botId || '')}</strong><div class="muted" style="margin-top:4px">${t.toLocaleString()}</div></div>
          <div>${categoryBadge}</div>
        </div>
        ${err}
        <div style="margin-top:8px;color:var(--muted);font-size:0.85rem">${meta.join(' • ')}</div>
        ${comprehensiveHtml}
        ${pageHtmlInfo}
        ${domHtml}
      </div>
    `;
  });
  el.innerHTML = items.join('');

  // attach click handlers to open modal with raw JSON
  const cards = el.querySelectorAll('.failure-card');
  cards.forEach((card) => {
    card.addEventListener('click', () => {
      const idx = parseInt(card.getAttribute('data-idx'), 10);
      const f = failures[idx];
      if (f) showFailureJson(f);
    });
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatUnixTime(seconds) {
  if (!seconds) return '-';
  const d = new Date(seconds * 1000);
  return Number.isNaN(d.getTime()) ? String(seconds) : d.toLocaleString();
}

function formatIsoTime(value) {
  if (!value) return '-';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString();
}

function formatPercent(value) {
  if (typeof value !== 'number') return '-';
  return `${Math.round(value * 100)}%`;
}

function formatNumber(value, digits = 3) {
  if (typeof value !== 'number') return '-';
  return value.toFixed(digits);
}

function sectionCardHtml(title, rows) {
  const visible = rows.filter((row) => row && row.value !== undefined && row.value !== null);
  if (!visible.length) return '';
  const items = visible.map((row) => {
    const label = escapeHtml(row.label || '');
    const rawValue = row.value === '' ? '-' : String(row.value);
    const safeValue = escapeHtml(rawValue);
    const valueHtml = row.code
      ? `<code style="background:rgba(0,0,0,0.35);padding:3px 8px;border-radius:6px;font-size:12px;display:inline-block;word-break:break-all">${safeValue}</code>`
      : `<span style="font-weight:600;word-break:break-word">${safeValue}</span>`;
    return `
      <div style="display:grid;grid-template-columns:220px 1fr;gap:10px;align-items:start">
        <div style="color:var(--muted);font-size:12px">${label}</div>
        <div>${valueHtml}</div>
      </div>
    `;
  }).join('');

  return `
    <div style="border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:12px;background:rgba(255,255,255,0.02)">
      <div style="font-weight:700;margin-bottom:10px">${escapeHtml(title)}</div>
      <div style="display:grid;gap:8px">${items}</div>
    </div>
  `;
}

function listCardHtml(title, items) {
  if (!Array.isArray(items) || !items.length) return '';
  const listItems = items.map((item) => `<li style="margin-bottom:6px">${escapeHtml(String(item))}</li>`).join('');
  return `
    <div style="border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:12px;background:rgba(255,255,255,0.02)">
      <div style="font-weight:700;margin-bottom:10px">${escapeHtml(title)}</div>
      <ul style="margin:0;padding-left:18px">${listItems}</ul>
    </div>
  `;
}

function parseMaybeJsonObject(value) {
  if (!value) return null;
  if (typeof value === 'object') return value;
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  if (!(trimmed.startsWith('{') || trimmed.startsWith('['))) return null;
  try {
    const parsed = JSON.parse(trimmed);
    return (parsed && typeof parsed === 'object') ? parsed : null;
  } catch (_err) {
    return null;
  }
}

function firstObject(values) {
  for (const value of values) {
    const parsed = parseMaybeJsonObject(value);
    if (parsed) return parsed;
  }
  return {};
}

function looksLikeLocatorReport(value) {
  const obj = parseMaybeJsonObject(value);
  if (!obj || typeof obj !== 'object') return false;
  return !!(obj.failure_context && obj.element_expectation && obj.metadata);
}

function failureLoadingHtml() {
  const block = `
    <div class="skeleton-card">
      <div class="skeleton-title"></div>
      <div class="skeleton-line w40"></div>
      <div class="skeleton-line w90"></div>
      <div class="skeleton-line w80"></div>
      <div class="skeleton-line w65"></div>
    </div>
  `;
  return `<div class="detail-loading-grid">${block}${block}${block}${block}</div>`;
}

function openFailureModalLoading() {
  const modal = document.getElementById('failure-modal');
  const pre = document.getElementById('failure-json-pre');
  const sectionsEl = document.getElementById('failure-sections');
  const rawBtn = document.getElementById('failure-toggle-raw');
  const domContainer = document.getElementById('failure-dom-container');
  const renderBtn = document.getElementById('failure-render-dom');
  if (!modal || !sectionsEl) return false;

  sectionsEl.innerHTML = failureLoadingHtml();
  if (pre) pre.style.display = 'none';
  if (rawBtn) {
    rawBtn.textContent = 'Show Raw JSON (Debug)';
    rawBtn.onclick = null;
  }
  if (domContainer) {
    domContainer.innerHTML = '';
    domContainer.style.display = 'none';
  }
  if (renderBtn) renderBtn.style.display = 'none';

  modal.style.display = 'flex';
  return true;
}

function sameFailure(a, b) {
  if (!a || !b) return false;
  const ar = a.locator_report_id || a.locator_report?.metadata?.report_id;
  const br = b.locator_report_id || b.locator_report?.metadata?.report_id;
  if (ar && br && ar === br) return true;

  const at = Number(a.timestamp || 0);
  const bt = Number(b.timestamp || 0);
  if ((a.botId || '') === (b.botId || '') && at && bt && Math.abs(at - bt) < 0.01) return true;
  return false;
}

async function resolveLatestFailure(currentFailure) {
  try {
    const res = await fetch('/status');
    if (!res.ok) return currentFailure;
    const data = await res.json();
    const list = Array.isArray(data.failures) ? data.failures : [];
    for (const item of list) {
      if (sameFailure(item, currentFailure)) return item;
    }
    if (currentFailure?.botId) {
      const latestByBot = list.find((item) => item && item.botId === currentFailure.botId);
      if (latestByBot) return latestByBot;
    }
    return currentFailure;
  } catch (_err) {
    return currentFailure;
  }
}

async function showFailureJson(failure) {
  const modal = document.getElementById('failure-modal');
  const pre = document.getElementById('failure-json-pre');
  const sectionsEl = document.getElementById('failure-sections');
  const rawBtn = document.getElementById('failure-toggle-raw');
  if (!modal || !pre || !sectionsEl) return;

  openFailureModalLoading();
  const resolvedFailure = await resolveLatestFailure(failure);
  failure = resolvedFailure || failure;

  // pretty-print JSON for debug mode
  try {
    const pretty = JSON.stringify(failure, null, 2);
    pre.textContent = pretty;
  } catch (e) {
    pre.textContent = String(failure);
  }

  pre.style.display = 'none';
  if (rawBtn) {
    rawBtn.textContent = 'Show Raw JSON (Debug)';
    rawBtn.onclick = () => {
      const showing = pre.style.display === 'block';
      pre.style.display = showing ? 'none' : 'block';
      rawBtn.textContent = showing ? 'Show Raw JSON (Debug)' : 'Hide Raw JSON';
    };
  }

  const locatorReport = firstObject([
    failure.locator_report,
    failure.locatorReport,
    failure.element_locator_details,
    failure.ai_locator_output,
    looksLikeLocatorReport(failure) ? failure : null,
  ]);

  const healingRequest = firstObject([
    failure.healing_request,
    locatorReport.healing_request,
    failure.healingRequest,
    failure.healing_input,
  ]);

  const healingResult = firstObject([
    failure.healing_result,
    locatorReport.healing_result,
    failure.healingResult,
  ]);

  const healingSummary = healingResult.healing_summary || {};
  const ptqaResult = firstObject([
    failure.ptqa_result,
    failure.ptqaResult,
    failure.ptqa_output,
  ]);

  const categoryLabel = `${failure.category || failure.failure_type || '-'}${typeof failure.confidence === 'number' ? ` (${Math.round(failure.confidence * 100)}%)` : ''}`;

  const errorRows = [
    { label: 'Bot ID', value: failure.botId || failure.metadata?.bot_id || '-' },
    { label: 'Timestamp', value: formatUnixTime(failure.timestamp) },
    { label: 'Category', value: categoryLabel },
    { label: 'Failure Type', value: failure.failure_type || '-' },
    { label: 'Error Message', value: failure.error || '-' },
    { label: 'Last Action', value: failure.failed_action || failure.last_action || '-' },
    { label: 'Page URL', value: failure.page_url || failure.metadata?.target_url || '-' },
    { label: 'Element Role', value: failure.element_role || '-' },
    { label: 'Expected Text', value: failure.expected_text || '-' },
    { label: 'Old Locator', value: failure.old_locator || '-', code: true },
    { label: 'Locator Type', value: failure.old_locator_type || '-' },
    { label: 'Screenshot', value: failure.screenshot_path || '-' },
    { label: 'Page HTML Size', value: failure.page_html ? `${(failure.page_html.length / 1024).toFixed(2)} KB` : '-' },
    { label: 'Workflow Step', value: failure.metadata?.workflow_step || '-' },
    { label: 'Metadata Timestamp', value: formatIsoTime(failure.metadata?.timestamp) },
    { label: 'Error Type', value: failure.metadata?.error_type || '-' },
  ];

  const locatorRows = [
    { label: 'Report ID', value: locatorReport.metadata?.report_id || failure.locator_report_id || '-' },
    { label: 'Run ID', value: locatorReport.metadata?.run_id || '-' },
    { label: 'Source Component', value: locatorReport.metadata?.source_component || '-' },
    { label: 'Timestamp', value: formatIsoTime(locatorReport.metadata?.timestamp) },
    { label: 'Action', value: locatorReport.failure_context?.action || failure.last_action || '-' },
    { label: 'Error Type', value: locatorReport.failure_context?.error_type || failure.failure_type || '-' },
    { label: 'Error Message', value: locatorReport.failure_context?.error_message || failure.error || '-' },
    { label: 'Old Locator', value: locatorReport.failure_context?.old_locator || failure.old_locator || '-', code: true },
    { label: 'Expected Role', value: locatorReport.element_expectation?.expected_role || failure.element_role || '-' },
    { label: 'Expected Text', value: locatorReport.element_expectation?.expected_text || failure.expected_text || '-' },
    { label: 'Candidate Strategy', value: locatorReport.element_candidate?.strategy || '-' },
    { label: 'Candidate Score', value: formatNumber(locatorReport.element_candidate?.score) },
    { label: 'Candidate XPath', value: locatorReport.element_candidate?.xpath || '-', code: !!locatorReport.element_candidate?.xpath },
    { label: 'Candidate CSS', value: locatorReport.element_candidate?.css || '-', code: !!locatorReport.element_candidate?.css },
    { label: 'Locator Error', value: failure.locator_error || '-' },
  ];

  const healingRows = [
    { label: 'Healing ID', value: healingResult.metadata?.healing_id || '-' },
    { label: 'Report ID', value: healingResult.metadata?.report_id || locatorReport.metadata?.report_id || '-' },
    { label: 'Run ID', value: healingResult.metadata?.run_id || locatorReport.metadata?.run_id || '-' },
    { label: 'Timestamp', value: formatIsoTime(healingResult.metadata?.timestamp) },
    { label: 'Status', value: healingSummary.status || failure.healing_status || '-' },
    { label: 'Strategy Used', value: healingSummary.strategy_used || '-' },
    { label: 'Action', value: healingSummary.action || healingResult.failure_context?.action || '-' },
    { label: 'Old Locator', value: healingSummary.old_locator || healingResult.failure_context?.old_locator || '-', code: true },
    { label: 'New Locator', value: healingSummary.new_locator || '-', code: !!healingSummary.new_locator },
    { label: 'Confidence', value: formatNumber(healingSummary.confidence) },
    { label: 'Model', value: healingResult.model_info?.model || '-' },
    { label: 'Model Confidence', value: formatNumber(healingResult.model_info?.confidence) },
    { label: 'Original Script Path', value: healingResult.script_output?.original_script_path || healingRequest.failure_context?.script_path || '-' },
    { label: 'Healed Script Path', value: healingResult.script_output?.healed_script_path || '-' },
    { label: 'Validation Result', value: healingSummary.validation?.valid === true ? 'Valid' : (healingSummary.validation?.valid === false ? 'Invalid' : '-') },
    { label: 'Validation Reason', value: healingSummary.validation?.reason || '-' },
    { label: 'Healing Error', value: failure.healing_error || locatorReport.healing_error || '-' },
  ];

  const ptqaRows = [
    { label: 'Recommendation', value: ptqaResult.recommendation || '-' },
    { label: 'Risk Level', value: ptqaResult.risk_level || '-' },
    { label: 'Confidence', value: formatPercent(ptqaResult.confidence) },
    { label: 'Will Work Probability', value: formatPercent(ptqaResult.will_work_probability) },
    { label: 'Model Name', value: ptqaResult.model_name || '-' },
    { label: 'Pass Rate (Before -> After)', value: (typeof ptqaResult.quality_metrics?.pass_rate_before === 'number' && typeof ptqaResult.quality_metrics?.pass_rate_after === 'number') ? `${Math.round(ptqaResult.quality_metrics.pass_rate_before * 100)}% -> ${Math.round(ptqaResult.quality_metrics.pass_rate_after * 100)}%` : '-' },
    { label: 'Pass Rate Delta', value: formatPercent(ptqaResult.quality_metrics?.pass_rate_delta) },
    { label: 'Latency Delta', value: typeof ptqaResult.quality_metrics?.latency_delta === 'number' ? `${ptqaResult.quality_metrics.latency_delta.toFixed(3)}s` : '-' },
    { label: 'Healing Effect', value: ptqaResult.quality_metrics?.healing_effect || '-' },
    { label: 'Has Regression', value: typeof ptqaResult.quality_metrics?.has_regression === 'boolean' ? (ptqaResult.quality_metrics.has_regression ? 'Yes' : 'No') : '-' },
  ];

  sectionsEl.innerHTML = [
    sectionCardHtml('Failure Details', errorRows),
    sectionCardHtml('Element Locator Details', locatorRows),
    sectionCardHtml('Healing Details', healingRows),
    sectionCardHtml('PTQA Service Details', ptqaRows),
    listCardHtml('PTQA Reasons', ptqaResult.reasons),
    listCardHtml('PTQA Validation Steps', ptqaResult.validation_steps),
  ].join('');

  // prepare DOM render button (for page_html if available, fallback to dom)
  const domContainer = document.getElementById('failure-dom-container');
  const renderBtn = document.getElementById('failure-render-dom');
  if (renderBtn && domContainer) {
    const htmlContent = failure.page_html || failure.dom;
    if (htmlContent) {
      renderBtn.style.display = 'inline-block';
      domContainer.style.display = 'none';
      renderBtn.textContent = failure.page_html ? 'Render Page HTML' : 'Render DOM';
      renderBtn.onclick = () => {
        // sanitize by not executing scripts: use sandboxed iframe with no allow-scripts
        domContainer.innerHTML = '';
        const iframe = document.createElement('iframe');
        iframe.setAttribute('sandbox', '');
        iframe.style.width = '100%';
        iframe.style.height = '500px';
        iframe.style.border = '0';
        try {
          iframe.srcdoc = htmlContent;
        } catch (e) {
          // fallback: show escaped HTML inside pre
          domContainer.innerHTML = `<pre style="white-space:pre-wrap;padding:8px;max-height:500px;overflow:auto">${escapeHtml(htmlContent)}</pre>`;
          domContainer.style.display = 'block';
          modal.style.display = 'flex';
          return;
        }
        domContainer.appendChild(iframe);
        domContainer.style.display = 'block';
      };
    } else {
      renderBtn.style.display = 'none';
      domContainer.style.display = 'none';
    }
  }

  modal.style.display = 'flex';
}

function closeFailureModal() {
  const modal = document.getElementById('failure-modal');
  if (modal) modal.style.display = 'none';
}

// wire modal close
document.addEventListener('click', (ev) => {
  const target = ev.target;
  if (target && target.id === 'failure-modal-close') closeFailureModal();
  if (target && target.id === 'failure-overlay') closeFailureModal();
});

function renderBots(bots) {
  const tbody = document.getElementById('bots-tbody');
  tbody.innerHTML = '';
  const ids = Object.keys(bots).sort();
  if (ids.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" class="muted">No bots seen yet</td></tr>';
    return;
  }
  const now = Date.now() / 1000;
  for (const id of ids) {
    const info = bots[id] || {};
    const lastSeen = info.last_seen || 0;
    const age = Math.max(0, Math.round(now - lastSeen));
    const status = (age > 10) ? 'FAILED' : (info.status || 'UNKNOWN');
    const badgeClass = (status === 'FAILED') ? 'badge failed' : (status === 'RUNNING' ? 'badge running' : 'badge muted');
    const lastSeenText = lastSeen ? new Date(lastSeen * 1000).toLocaleString() : 'never';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><code>${id}</code><div class="muted" style="margin-top:6px;font-weight:500">${info.meta ? JSON.stringify(info.meta) : ''}</div></td>
      <td><span class="${badgeClass}">${status}</span></td>
      <td><div>${formatAge(age)}</div><div class="muted" style="margin-top:6px">${lastSeenText}</div></td>
    `;
    tbody.appendChild(tr);
  }
}

// Charts: track history
const historyMax = 24;
let historyLabels = [];
let historyActive = [];

// Chart instances
let doughnutChart = null;
let lineChart = null;

function createCharts() {
  const dCtx = document.getElementById('doughnutChart').getContext('2d');
  doughnutChart = new Chart(dCtx, {
    type: 'doughnut',
    data: {
      labels: ['Running', 'Failed'],
      datasets: [{ data: [0, 0], backgroundColor: ['rgba(16,185,129,0.9)', 'rgba(239,68,68,0.9)'], hoverOffset: 6 }]
    },
    options: { maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
  });

  const lCtx = document.getElementById('lineChart').getContext('2d');
  lineChart = new Chart(lCtx, {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'Active bots', data: [], borderColor: 'rgba(96,165,250,0.9)', backgroundColor: 'rgba(96,165,250,0.12)', tension: 0.25, fill: true }] },
    options: { maintainAspectRatio: false, scales: { y: { beginAtZero: true, precision: 0 } } }
  });
}

function updateChartsFromData(bots) {
  const ids = Object.keys(bots || {});
  const now = Date.now() / 1000;
  let running = 0;
  for (const id of ids) {
    const info = bots[id] || {};
    const lastSeen = info.last_seen || 0;
    const age = Math.max(0, Math.round(now - lastSeen));
    if (age <= 10) running++;
  }
  const failed = Math.max(0, ids.length - running);

  // update doughnut
  if (doughnutChart) {
    doughnutChart.data.datasets[0].data = [running, failed];
    doughnutChart.update();
  }

  // push to history
  const label = new Date().toLocaleTimeString();
  historyLabels.push(label);
  historyActive.push(running);
  if (historyLabels.length > historyMax) { historyLabels.shift(); historyActive.shift(); }

  if (lineChart) {
    lineChart.data.labels = historyLabels.slice();
    lineChart.data.datasets[0].data = historyActive.slice();
    lineChart.update();
  }
}

// Controls
document.getElementById('refresh-btn').addEventListener('click', fetchStatus);

// create charts once DOM is ready
try { createCharts(); } catch (e) { console.warn('Charts not available yet', e); }

// Poll every 3 seconds
fetchStatus();
setInterval(fetchStatus, 3000);
