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
  }catch(e){
    console.error(e);
    document.getElementById('bots-tbody').innerHTML = '<tr><td colspan="3" class="muted">Error loading status</td></tr>';
  }
}

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
