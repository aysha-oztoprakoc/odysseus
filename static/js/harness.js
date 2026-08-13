// Harness dashboard — data_rein wiki/trail/router/budgets, reached over the
// backend's /api/reins/* routes (see routes/reins_routes.py), which in turn
// talk to the `reins` MCP server over streamable-HTTP (integrations/reins/mcp_client.py).
// ES6 module, following the shape of tasks.js/gallery.js.

const API_BASE = window.location.origin;
let _open = false;

async function _get(path) {
  const res = await fetch(`${API_BASE}${path}`, { credentials: 'same-origin' });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

async function _post(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

function _escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s ?? '';
  return div.innerHTML;
}

async function _refreshTrail() {
  const body = document.getElementById('harness-trail-body');
  if (!body) return;
  body.innerHTML = '<tr><td colspan="4" style="padding:8px;opacity:0.6;">Loading…</td></tr>';
  try {
    const tasks = await _get('/api/reins/trail');
    if (!Array.isArray(tasks) || !tasks.length) {
      body.innerHTML = '<tr><td colspan="4" style="padding:8px;opacity:0.6;">No task trail entries.</td></tr>';
      return;
    }
    body.innerHTML = tasks.slice().reverse().map(t => `
      <tr style="border-top:1px solid var(--border);">
        <td style="padding:4px;">${_escapeHtml(t.status)}</td>
        <td style="padding:4px;">${_escapeHtml(t.task_type)}</td>
        <td style="padding:4px;">${_escapeHtml(t.target_node)}</td>
        <td style="padding:4px;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${_escapeHtml(t.prompt)}</td>
      </tr>
    `).join('');
  } catch (e) {
    body.innerHTML = `<tr><td colspan="4" style="padding:8px;color:var(--red);">Harness unreachable: ${_escapeHtml(e.message)}</td></tr>`;
  }
}

async function _refreshAgents() {
  const list = document.getElementById('harness-agents-list');
  if (!list) return;
  list.innerHTML = '<div style="opacity:0.6;">Loading…</div>';
  try {
    const { budgets } = await _get('/api/reins/agents');
    const names = Object.keys(budgets || {});
    if (!names.length) {
      list.innerHTML = '<div style="opacity:0.6;">No known agents.</div>';
      return;
    }
    list.innerHTML = names.map(name => {
      const b = budgets[name];
      return `
        <div class="admin-card" data-agent="${_escapeHtml(name)}" style="display:flex;flex-direction:column;gap:6px;">
          <strong>${_escapeHtml(name)}</strong>
          <label style="display:flex;align-items:center;gap:8px;font-size:12px;">
            CPU %
            <input type="number" min="1" max="100" class="harness-cpu-input" value="${b.cpu_pct}" style="width:64px;" />
          </label>
          <label style="display:flex;align-items:center;gap:8px;font-size:12px;">
            GPU VRAM (GB)
            <input type="number" min="0" step="0.5" class="harness-vram-input" value="${b.gpu_vram_gb}" style="width:64px;" />
          </label>
          <button class="memory-toolbar-btn harness-save-budget" style="align-self:flex-start;">Save</button>
        </div>
      `;
    }).join('');
    list.querySelectorAll('.harness-save-budget').forEach(btn => {
      btn.addEventListener('click', async () => {
        const card = btn.closest('[data-agent]');
        const name = card.dataset.agent;
        const cpu_pct = parseInt(card.querySelector('.harness-cpu-input').value, 10);
        const gpu_vram_gb = parseFloat(card.querySelector('.harness-vram-input').value);
        btn.textContent = 'Saving…';
        try {
          await _post(`/api/reins/agents/${encodeURIComponent(name)}/budget`, { cpu_pct, gpu_vram_gb });
          btn.textContent = 'Saved';
          setTimeout(() => { btn.textContent = 'Save'; }, 1200);
        } catch (e) {
          btn.textContent = 'Failed';
        }
      });
    });
  } catch (e) {
    list.innerHTML = `<div style="color:var(--red);">Harness unreachable: ${_escapeHtml(e.message)}</div>`;
  }
}

async function _runWikiSearch(query) {
  const results = document.getElementById('harness-wiki-results');
  if (!results) return;
  if (!query.trim()) { results.innerHTML = ''; return; }
  results.innerHTML = '<div style="opacity:0.6;">Searching…</div>';
  try {
    const res = await _get(`/api/reins/wiki/search?q=${encodeURIComponent(query)}&limit=8`);
    const pages = res.pages || [];
    const memories = res.memories || [];
    if (!pages.length && !memories.length) {
      results.innerHTML = '<div style="opacity:0.6;">No results.</div>';
      return;
    }
    results.innerHTML = [
      ...pages.map(p => `<div><strong>[${_escapeHtml(p.category)}]</strong> ${_escapeHtml(p.slug)}<br><span style="opacity:0.7;">${_escapeHtml(p.snippet)}</span></div>`),
      ...memories.map(m => `<div><strong>[${_escapeHtml(m.category)}]</strong> ${_escapeHtml(m.snippet)}</div>`),
    ].join('<hr style="border-color:var(--border);opacity:0.3;">');
  } catch (e) {
    results.innerHTML = `<div style="color:var(--red);">Harness unreachable: ${_escapeHtml(e.message)}</div>`;
  }
}

async function _refreshTokens() {
  const strip = document.getElementById('harness-tokens-strip');
  if (!strip) return;
  try {
    const report = await _get('/api/reins/tokens');
    const parts = Object.entries(report || {}).map(([provider, windows]) => {
      const day = windows?.day || windows?.["24h"] || {};
      return `${provider}: ${day.count ?? 0} calls`;
    });
    strip.textContent = parts.length ? `Token usage: ${parts.join(' · ')}` : 'Token usage: no data';
  } catch (e) {
    strip.textContent = 'Token usage: harness unreachable';
  }
}

async function _refreshOmnigent() {
  const statusEl = document.getElementById('harness-omnigent-status');
  const frame = document.getElementById('harness-omnigent-frame');
  if (!statusEl || !frame) return;
  statusEl.textContent = 'Checking…';
  frame.style.display = 'none';
  try {
    const { reachable, port } = await _get('/api/reins/omnigent/status');
    if (reachable && port) {
      statusEl.textContent = `Omnigent is running on port ${port}.`;
      frame.src = `${window.location.protocol}//${window.location.hostname}:${port}/`;
      frame.style.display = 'block';
    } else {
      statusEl.textContent = 'Omnigent is not currently reachable.';
    }
  } catch (e) {
    statusEl.textContent = `Could not check Omnigent status: ${e.message}`;
  }
}

async function _refreshHardware() {
  const statusEl = document.getElementById('harness-hardware-status');
  const gapsEl = document.getElementById('harness-hardware-gaps');
  if (!statusEl || !gapsEl) return;
  statusEl.textContent = 'Scanning hardware...';
  gapsEl.textContent = '';
  try {
    const scan = await _get('/api/reins/hardware/scan');
    statusEl.textContent = JSON.stringify(scan, null, 2);
    const gaps = await _get('/api/reins/hardware/gaps');
    if (gaps && Object.keys(gaps).length) {
      gapsEl.textContent = 'Gaps:\n' + JSON.stringify(gaps, null, 2);
    }
  } catch (e) {
    statusEl.textContent = `Hardware scan failed: ${e.message}`;
  }
}

async function _refreshCoord() {
  const statusEl = document.getElementById('harness-coord-status');
  if (!statusEl) return;
  statusEl.textContent = 'Loading coordinator status...';
  try {
    const status = await _get('/api/reins/coord/status');
    statusEl.textContent = JSON.stringify(status, null, 2);
  } catch (e) {
    statusEl.textContent = `Coordinator unreachable: ${e.message}`;
  }
}

async function _exportDataset() {
  const statusEl = document.getElementById('harness-ds-status');
  const pathIn = document.getElementById('harness-ds-path');
  const catsIn = document.getElementById('harness-ds-cats');
  if (!statusEl || !pathIn) return;
  const out_path = pathIn.value.trim();
  if (!out_path) {
    statusEl.textContent = 'Output path is required.';
    return;
  }
  statusEl.textContent = 'Exporting dataset...';
  try {
    const res = await _post('/api/reins/dataset/export', {
      out_path,
      categories: catsIn ? catsIn.value.trim() : ''
    });
    statusEl.textContent = `Export complete: ${JSON.stringify(res)}`;
  } catch (e) {
    statusEl.textContent = `Export failed: ${e.message}`;
  }
}

async function _refreshTraining() {
  const statusEl = document.getElementById('harness-train-status');
  if (!statusEl) return;
  statusEl.textContent = 'Checking capability...';
  try {
    const status = await _get('/api/reins/train/status');
    statusEl.textContent = JSON.stringify(status, null, 2);
  } catch (e) {
    statusEl.textContent = `Check failed: ${e.message}`;
  }
}

function _switchTab(name) {
  document.querySelectorAll('#harness-modal [data-harness-tab]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.harnessTab === name);
  });
  document.querySelectorAll('#harness-modal [data-harness-panel]').forEach(panel => {
    panel.classList.toggle('hidden', panel.dataset.harnessPanel !== name);
  });
  if (name === 'trail') _refreshTrail();
  else if (name === 'agents') _refreshAgents();
  else if (name === 'omnigent') _refreshOmnigent();
  else if (name === 'hardware') { _refreshHardware(); _refreshCoord(); }
  else if (name === 'training') _refreshTraining();
}

function _wireOnce() {
  if (_wireOnce._done) return;
  _wireOnce._done = true;

  document.getElementById('close-harness-modal')?.addEventListener('click', closeHarness);
  document.querySelectorAll('#harness-modal [data-harness-tab]').forEach(btn => {
    btn.addEventListener('click', () => _switchTab(btn.dataset.harnessTab));
  });
  document.getElementById('harness-trail-refresh')?.addEventListener('click', _refreshTrail);
  document.getElementById('harness-agents-refresh')?.addEventListener('click', _refreshAgents);
  const searchInput = document.getElementById('harness-wiki-search-input');
  if (searchInput) {
    let debounce;
    searchInput.addEventListener('input', () => {
      clearTimeout(debounce);
      debounce = setTimeout(() => _runWikiSearch(searchInput.value), 300);
    });
  }

  document.getElementById('harness-hardware-refresh')?.addEventListener('click', _refreshHardware);
  document.getElementById('harness-train-refresh')?.addEventListener('click', _refreshTraining);
  document.getElementById('harness-ds-export')?.addEventListener('click', _exportDataset);

  const coordLoadBtn = document.getElementById('harness-coord-load');
  const coordUnloadBtn = document.getElementById('harness-coord-unload');
  const coordModelIn = document.getElementById('harness-coord-model');
  
  if (coordLoadBtn && coordModelIn) {
    coordLoadBtn.addEventListener('click', async () => {
      const model = coordModelIn.value.trim();
      if (!model) return;
      coordLoadBtn.textContent = '...';
      try {
        await _post('/api/reins/coord/load', { model });
        await _refreshCoord();
      } finally {
        coordLoadBtn.textContent = 'Load';
      }
    });
  }
  
  if (coordUnloadBtn && coordModelIn) {
    coordUnloadBtn.addEventListener('click', async () => {
      const model = coordModelIn.value.trim();
      if (!model) return;
      coordUnloadBtn.textContent = '...';
      try {
        await _post('/api/reins/coord/unload', { model });
        await _refreshCoord();
      } finally {
        coordUnloadBtn.textContent = 'Unload';
      }
    });
  }
}

export function openHarness() {
  const modal = document.getElementById('harness-modal');
  if (!modal) return;
  _wireOnce();
  modal.classList.remove('hidden');
  _open = true;
  _switchTab('trail');
  _refreshTokens();
}

export function closeHarness() {
  const modal = document.getElementById('harness-modal');
  if (modal) modal.classList.add('hidden');
  _open = false;
}

export function isHarnessOpen() {
  return _open;
}

const harnessModule = { openHarness, closeHarness, isHarnessOpen };
window.harnessModule = harnessModule;
export default harnessModule;
