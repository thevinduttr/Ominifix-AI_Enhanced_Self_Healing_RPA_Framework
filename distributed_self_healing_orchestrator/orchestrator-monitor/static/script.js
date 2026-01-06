function formatAge(seconds){
  if(seconds < 5) return 'now';
  if(seconds < 60) return `${seconds}s ago`;
  if(seconds < 3600) return `${Math.floor(seconds/60)}m ${seconds%60}s ago`;
  return `${Math.floor(seconds/3600)}h ${Math.floor((seconds%3600)/60)}m ago`;
}

async function fetchStatus(){
  try{
    const res = await fetch('/status');
    if(!res.ok) throw new Error('Network response was not ok');
    const data = await res.json();
    renderBots(data.bots || {});
    document.getElementById('last-update').textContent = new Date().toLocaleString();
    // update charts based on current data
      updateChartsFromData(data.bots || {});
      // render recent failures list if available
      if(data.failures){ renderFailures(data.failures); }
  }catch(e){
    console.error(e);
    document.getElementById('bots-tbody').innerHTML = '<tr><td colspan="3" class="muted">Error loading status</td></tr>';
  }
}

function renderFailures(failures){
  const el = document.getElementById('recent-failures');
  if(!el) return;
  if(!failures || failures.length === 0){ el.innerHTML = '<div class="muted">No failures yet</div>'; return; }
    const items = failures.slice(0,10).map((f, idx) => {
    const t = new Date((f.timestamp||0)*1000);
    const err = f.error ? `<div style="margin-top:8px;color:#ffdede;font-size:0.9rem">${escapeHtml((f.error||'')).slice(0,240)}</div>` : '';
    // build category badge with confidence and emphasis
    let categoryBadge = '';
    if(f.category){
      const conf = (typeof f.confidence === 'number') ? ` ${Math.round(f.confidence*100)}%` : '';
      const cls = (f.category === 'unknown') ? 'category-badge unknown' : ((f.confidence && f.confidence >= 0.7) ? 'category-badge confident' : 'category-badge');
      categoryBadge = `<div style="margin-left:8px;display:inline-block"><span class="${cls}">${escapeHtml(f.category)}${conf}</span></div>`;
    }
    const meta = [];
    if(f.failure_type) meta.push(`<strong>Type:</strong> ${escapeHtml(f.failure_type)}`);
    if(f.last_action || f.failed_action) meta.push(`<strong>Action:</strong> ${escapeHtml(f.failed_action || f.last_action)}`);
    if(f.strategy) meta.push(`<strong>Strategy:</strong> ${escapeHtml(f.strategy)}`);
    if(f.priority) meta.push(`<strong>Priority:</strong> ${escapeHtml(f.priority)}`);
    
    // New comprehensive fields display
    const comprehensiveInfo = [];
    if(f.page_url) comprehensiveInfo.push(`<strong>Page URL:</strong> <a href="${escapeHtml(f.page_url)}" target="_blank" style="color:#60a5fa">${escapeHtml(f.page_url).slice(0,60)}${f.page_url.length>60?'...':''}</a>`);
    if(f.element_role) comprehensiveInfo.push(`<strong>Element Role:</strong> ${escapeHtml(f.element_role)}`);
    if(f.expected_text) comprehensiveInfo.push(`<strong>Expected Text:</strong> ${escapeHtml(f.expected_text).slice(0,50)}${f.expected_text.length>50?'...':''}`);
    if(f.old_locator) comprehensiveInfo.push(`<strong>Old Locator:</strong> <code style="background:rgba(0,0,0,0.3);padding:2px 6px;border-radius:4px">${escapeHtml(f.old_locator).slice(0,60)}${f.old_locator.length>60?'...':''}</code>`);
    if(f.old_locator_type) comprehensiveInfo.push(`<strong>Locator Type:</strong> ${escapeHtml(f.old_locator_type)}`);
    if(f.screenshot_path) comprehensiveInfo.push(`<strong>Screenshot:</strong> <span style="color:#10b981">${escapeHtml(f.screenshot_path.split('/').pop())}</span>`);
    
    const comprehensiveHtml = comprehensiveInfo.length > 0 ? `<div style="margin-top:8px;color:#cbd5e1;font-size:0.85rem;line-height:1.8">${comprehensiveInfo.join('<br>')}</div>` : '';
    
    const domSnippet = f.dom ? escapeHtml(f.dom).slice(0,200) + (f.dom.length>200? '...':'') : '';
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
  cards.forEach((card)=>{
    card.addEventListener('click', ()=>{
      const idx = parseInt(card.getAttribute('data-idx'),10);
      const f = failures[idx];
      if(f) showFailureJson(f);
    });
  });
}

function escapeHtml(str){
  if(!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function showFailureJson(failure){
  const modal = document.getElementById('failure-modal');
  const pre = document.getElementById('failure-json-pre');
  if(!modal || !pre) return;
  // pretty-print JSON, but sanitize
  try{
    const pretty = JSON.stringify(failure, null, 2);
    pre.textContent = pretty;
  }catch(e){
    pre.textContent = String(failure);
  }
  // populate structured fields with comprehensive data
  const fieldsEl = document.getElementById('failure-fields');
    if(fieldsEl){
      const parts = [];
      // Original fields
      if(failure.failure_type) parts.push(['Type', failure.failure_type]);
      if(failure.last_action || failure.failed_action) parts.push(['Last action', failure.failed_action || failure.last_action]);
      if(failure.strategy) parts.push(['Strategy', failure.strategy]);
      if(failure.priority) parts.push(['Priority', failure.priority]);
      if(failure.category) parts.push(['Category', failure.category + (failure.confidence ? ` (${Math.round(failure.confidence*100)}%)` : '')]);
      
      // Comprehensive new fields
      if(failure.page_url) parts.push(['Page URL', failure.page_url]);
      if(failure.element_role) parts.push(['Element Role', failure.element_role]);
      if(failure.expected_text) parts.push(['Expected Text', failure.expected_text]);
      if(failure.old_locator) parts.push(['Old Locator', failure.old_locator]);
      if(failure.old_locator_type) parts.push(['Locator Type', failure.old_locator_type]);
      if(failure.screenshot_path) parts.push(['Screenshot', failure.screenshot_path]);
      if(failure.page_html) parts.push(['Page HTML Size', `${(failure.page_html.length / 1024).toFixed(2)} KB`]);
      
      // Metadata object fields
      if(failure.metadata){
        if(failure.metadata.bot_id) parts.push(['Metadata: Bot ID', failure.metadata.bot_id]);
        if(failure.metadata.workflow_step) parts.push(['Workflow Step', failure.metadata.workflow_step]);
        if(failure.metadata.base_url) parts.push(['Base URL', failure.metadata.base_url]);
        if(failure.metadata.target_url) parts.push(['Target URL', failure.metadata.target_url]);
        if(failure.metadata.timestamp) parts.push(['Metadata Timestamp', new Date(failure.metadata.timestamp).toLocaleString()]);
        if(failure.metadata.error_type) parts.push(['Error Type', failure.metadata.error_type]);
      }
      
      parts.push(['Bot ID', failure.botId || '']);
      parts.push(['Timestamp', failure.timestamp ? new Date(failure.timestamp*1000).toLocaleString() : '']);
      fieldsEl.innerHTML = parts.map(p => {
        const key = escapeHtml(p[0]);
        const val = escapeHtml(String(p[1]||''));
        const valHtml = (p[0] === 'Category') ? `<span class="category-badge" style="font-size:0.95rem">${val}</span>` : 
                        (p[0].includes('URL') || p[0] === 'Screenshot') ? `<span style="word-break:break-all;font-size:0.85rem">${val}</span>` :
                        (p[0].includes('Locator')) ? `<code style="background:rgba(0,0,0,0.3);padding:4px 8px;border-radius:4px;font-size:0.85rem;display:block;margin-top:4px">${val}</code>` :
                        val;
        return `<div style="min-width:160px;padding:8px;border-radius:8px;background:rgba(255,255,255,0.02)"><div style="font-size:12px;color:var(--muted)">${key}</div><div style="font-weight:700;margin-top:6px">${valHtml}</div></div>`;
      }).join('');
    }

  // prepare DOM render button (for page_html if available, fallback to dom)
  const domContainer = document.getElementById('failure-dom-container');
  const renderBtn = document.getElementById('failure-render-dom');
  if(renderBtn && domContainer){
    const htmlContent = failure.page_html || failure.dom;
    if(htmlContent){
      renderBtn.style.display = 'inline-block';
      domContainer.style.display = 'none';
      renderBtn.textContent = failure.page_html ? 'Render Page HTML' : 'Render DOM';
      renderBtn.onclick = ()=>{
        // sanitize by not executing scripts: use sandboxed iframe with no allow-scripts
        domContainer.innerHTML = '';
        const iframe = document.createElement('iframe');
        iframe.setAttribute('sandbox', '');
        iframe.style.width = '100%';
        iframe.style.height = '500px';
        iframe.style.border = '0';
        try{
          iframe.srcdoc = htmlContent;
        }catch(e){
          // fallback: show escaped HTML inside pre
          domContainer.innerHTML = `<pre style="white-space:pre-wrap;padding:8px;max-height:500px;overflow:auto">${escapeHtml(htmlContent)}</pre>`;
          domContainer.style.display = 'block';
          modal.style.display = 'flex';
          return;
        }
        domContainer.appendChild(iframe);
        domContainer.style.display = 'block';
      };
    }else{
      renderBtn.style.display = 'none';
      domContainer.style.display = 'none';
    }
  }

  modal.style.display = 'flex';
}

function closeFailureModal(){
  const modal = document.getElementById('failure-modal');
  if(modal) modal.style.display = 'none';
}

// wire modal close
document.addEventListener('click', (ev)=>{
  const target = ev.target;
  if(target && target.id === 'failure-modal-close') closeFailureModal();
  if(target && target.id === 'failure-overlay') closeFailureModal();
});

function renderBots(bots){
  const tbody = document.getElementById('bots-tbody');
  tbody.innerHTML = '';
  const ids = Object.keys(bots).sort();
  if(ids.length === 0){
    tbody.innerHTML = '<tr><td colspan="3" class="muted">No bots seen yet</td></tr>';
    return;
  }
  const now = Date.now()/1000;
  for(const id of ids){
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

function createCharts(){
  const dCtx = document.getElementById('doughnutChart').getContext('2d');
  doughnutChart = new Chart(dCtx, {
    type: 'doughnut',
    data: {
      labels: ['Running','Failed'],
      datasets: [{data: [0,0], backgroundColor: ['rgba(16,185,129,0.9)','rgba(239,68,68,0.9)'], hoverOffset:6}]
    },
    options: {maintainAspectRatio:false, plugins:{legend:{position:'bottom'}}}
  });

  const lCtx = document.getElementById('lineChart').getContext('2d');
  lineChart = new Chart(lCtx, {
    type: 'line',
    data: {labels: [], datasets:[{label:'Active bots',data:[],borderColor:'rgba(96,165,250,0.9)',backgroundColor:'rgba(96,165,250,0.12)',tension:0.25,fill:true}]},
    options: {maintainAspectRatio:false, scales:{y:{beginAtZero:true,precision:0}}}
  });
}

function updateChartsFromData(bots){
  const ids = Object.keys(bots || {});
  const now = Date.now()/1000;
  let running = 0;
  for(const id of ids){
    const info = bots[id] || {};
    const lastSeen = info.last_seen || 0;
    const age = Math.max(0, Math.round(now - lastSeen));
    if(age <= 10) running++;
  }
  const failed = Math.max(0, ids.length - running);

  // update doughnut
  if(doughnutChart){
    doughnutChart.data.datasets[0].data = [running, failed];
    doughnutChart.update();
  }

  // push to history
  const label = new Date().toLocaleTimeString();
  historyLabels.push(label);
  historyActive.push(running);
  if(historyLabels.length > historyMax){ historyLabels.shift(); historyActive.shift(); }

  if(lineChart){
    lineChart.data.labels = historyLabels.slice();
    lineChart.data.datasets[0].data = historyActive.slice();
    lineChart.update();
  }
}

// Controls
document.getElementById('refresh-btn').addEventListener('click', fetchStatus);

// create charts once DOM is ready
try{ createCharts(); }catch(e){ console.warn('Charts not available yet', e); }

// Poll every 3 seconds
fetchStatus();
setInterval(fetchStatus, 3000);
