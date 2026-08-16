import * as Modals from './modalManager.js';
import uiModule from './ui.js';

const PAGE_SIZE = 100;
let capability = '';
let currentPath = '';
let editingPath = '';

function element(tag, text, className = '') {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

function button(text, action, className = 'memory-toolbar-btn') {
  const node = element('button', text, className);
  node.type = 'button';
  node.addEventListener('click', action);
  return node;
}

function capabilityHeaders(headers = {}) {
  return { ...headers, 'X-Odysseus-Files-Capability': capability };
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: capabilityHeaders(options.headers),
  });
  if (!response.ok) {
    if (response.status === 403) lockExplorer();
    throw new Error(await response.text());
  }
  return response;
}

function lockExplorer() {
  capability = '';
  const reauth = document.getElementById('files-reauth');
  reauth?.classList.remove('hidden');
  document.getElementById('files-admin-controls')?.classList.add('hidden');
}

function unlockExplorer() {
  const reauth = document.getElementById('files-reauth');
  reauth?.classList.add('hidden');
  const controls = document.getElementById('files-admin-controls');
  controls?.classList.remove('hidden');
}

function formatSize(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KiB', 'MiB', 'GiB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index ? 1 : 0)} ${units[index]}`;
}

async function reauthenticate() {
  const password = document.getElementById('files-reauth-password');
  const status = document.getElementById('files-reauth-status');
  if (!(password instanceof HTMLInputElement) || !status) return;
  status.textContent = '';
  try {
    const response = await fetch('/api/files/capability', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: password.value }),
    });
    password.value = '';
    if (!response.ok) throw new Error('Fresh admin authentication failed');
    capability = (await response.json()).capability;
    unlockExplorer();
    await loadFiles('');
  } catch (error) {
    status.textContent = error.message;
  }
}

function fileRow(item) {
  const row = element('div', '', 'memory-item files-admin-row');
  const open = button(`${item.is_dir ? 'DIR' : 'FILE'}  ${item.name}`, () => {
    if (item.is_dir) loadFiles(item.path);
    else openFileEditor(item.path, item.name);
  });
  open.classList.add('files-admin-open');
  const actions = element('div', '', 'files-admin-actions');
  if (!item.is_dir) {
    actions.append(element('span', formatSize(item.size)));
    actions.append(button('Download', () => downloadFile(item.path)));
  }
  if (!item.is_dir && /\.(zip|tar|tgz|tar\.gz)$/i.test(item.name)) {
    actions.append(button('Extract', () => extractArchive(item.path)));
  }
  actions.append(button('Delete', () => deletePath(item.path, item.is_dir), 'memory-toolbar-btn danger'));
  row.append(open, actions);
  return row;
}

async function loadFiles(path, offset = 0) {
  const list = document.getElementById('files-list');
  if (!list) return;
  list.replaceChildren(element('div', 'Loading...'));
  try {
    const query = new URLSearchParams({ path, limit: String(PAGE_SIZE), offset: String(offset) });
    const data = await (await request(`/api/files/browse?${query}`)).json();
    currentPath = data.path;
    document.getElementById('files-path-input').value = currentPath;
    const rows = [];
    if (data.parent) rows.push(button('UP  ..', () => loadFiles(data.parent)));
    rows.push(...data.items.map(fileRow));
    if (offset > 0) rows.push(button('Previous', () => loadFiles(currentPath, Math.max(0, offset - PAGE_SIZE))));
    if (offset + data.items.length < data.total) rows.push(button('Next', () => loadFiles(currentPath, offset + PAGE_SIZE)));
    list.replaceChildren(...rows);
  } catch (error) {
    uiModule.showToast(`Error loading files: ${error.message}`);
  }
}

async function extractArchive(path) {
  try {
    await request('/api/files/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
    await loadFiles(currentPath);
  } catch (error) {
    uiModule.showToast(`Extract failed: ${error.message}`);
  }
}

async function deletePath(path, recursive) {
  const prompt = recursive ? `Type the exact path to delete recursively:\n${path}` : `Type the exact path to delete:\n${path}`;
  if (window.prompt(prompt) !== path) return;
  try {
    await request('/api/files/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, confirm_path: path }),
    });
    await loadFiles(currentPath);
  } catch (error) {
    uiModule.showToast(`Delete failed: ${error.message}`);
  }
}

async function downloadFile(path) {
  try {
    const response = await request(`/api/files/download?path=${encodeURIComponent(path)}`);
    const link = document.createElement('a');
    link.href = URL.createObjectURL(await response.blob());
    link.download = path.split('/').pop();
    link.click();
    URL.revokeObjectURL(link.href);
  } catch (error) {
    uiModule.showToast(`Download failed: ${error.message}`);
  }
}

async function openFileEditor(path, name) {
  try {
    const data = await (await request(`/api/files/read?path=${encodeURIComponent(path)}`)).json();
    editingPath = path;
    document.getElementById('files-list').style.display = 'none';
    document.getElementById('files-editor-container').style.display = 'flex';
    document.getElementById('files-editor-name').textContent = name;
    document.getElementById('files-editor-textarea').value = data.content;
  } catch (error) {
    uiModule.showToast(`Read failed: ${error.message}`);
  }
}

async function saveFileEditor() {
  if (!editingPath) return;
  try {
    await request('/api/files/write', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: editingPath, content: document.getElementById('files-editor-textarea').value }),
    });
    uiModule.showToast('File saved');
  } catch (error) {
    uiModule.showToast(`Save failed: ${error.message}`);
  }
}

function closeFileEditor() {
  editingPath = '';
  document.getElementById('files-editor-container').style.display = 'none';
  document.getElementById('files-list').style.display = 'block';
}

async function uploadFile(input) {
  if (!input.files.length) return;
  const form = new FormData();
  form.append('file', input.files[0]);
  try {
    await request(`/api/files/upload?dir_path=${encodeURIComponent(currentPath)}`, { method: 'POST', body: form });
    await loadFiles(currentPath);
  } catch (error) {
    uiModule.showToast(`Upload failed: ${error.message}`);
  } finally {
    input.value = '';
  }
}

function initialize() {
  const modal = document.getElementById('files-modal');
  if (!modal) return;
  const closeFiles = () => {
    capability = '';
    modal.style.display = 'none';
    modal.classList.add('hidden');
  };
  const openFiles = () => {
    if (!modal.classList.contains('hidden')) return;
    modal.classList.remove('hidden', 'modal-minimized');
    modal.style.display = 'flex';
    lockExplorer();
    Modals.register('files-modal', {
      railBtnId: 'rail-files',
      sidebarBtnId: 'tool-files-btn',
      restoreFn: () => {},
      closeFn: closeFiles,
    });
  };
  for (const id of ['rail-files', 'tool-files-btn']) {
    document.getElementById(id)?.addEventListener('click', () => {
      if (!Modals.toggle('files-modal')) openFiles();
    });
  }
  document.getElementById('close-files-modal')?.addEventListener('click', () => {
    if (Modals.isRegistered('files-modal')) Modals.close('files-modal');
    else closeFiles();
  });
  document.getElementById('files-reauth-btn')?.addEventListener('click', reauthenticate);
  document.getElementById('files-go-btn')?.addEventListener('click', () => loadFiles(document.getElementById('files-path-input').value));
  document.getElementById('files-up-btn')?.addEventListener('click', () => loadFiles(`${currentPath}/..`));
  const upload = document.getElementById('files-upload-input');
  upload?.addEventListener('change', () => uploadFile(upload));
  document.getElementById('files-upload-btn')?.addEventListener('click', () => upload?.click());
  document.getElementById('files-path-input')?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') loadFiles(event.target.value);
  });
  document.getElementById('files-editor-save')?.addEventListener('click', saveFileEditor);
  document.getElementById('files-editor-close')?.addEventListener('click', closeFileEditor);
  document.documentElement.dataset.filesAdminReady = 'true';
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
else initialize();
