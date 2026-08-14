// static/js/filesExplorer.js

import uiModule from './ui.js';
import * as Modals from './modalManager.js';

let currentPath = '/home/amdy';

function formatSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function loadFiles(path) {
  try {
    const listContainer = document.getElementById('files-list');
    listContainer.innerHTML = '<div style="opacity:0.5;text-align:center;margin-top:20px;">Loading...</div>';
    
    const res = await fetch(`/api/files/browse?path=${encodeURIComponent(path)}`);
    if (!res.ok) throw new Error(await res.text());
    
    const data = await res.json();
    currentPath = data.path;
    document.getElementById('files-path-input').value = currentPath;
    
    listContainer.innerHTML = '';
    
    if (data.parent) {
      const upDiv = document.createElement('div');
      upDiv.className = 'memory-item';
      upDiv.style.cursor = 'pointer';
      upDiv.innerHTML = `<strong>..</strong>`;
      upDiv.onclick = () => loadFiles(data.parent);
      listContainer.appendChild(upDiv);
    }
    
    for (const item of data.items) {
      const div = document.createElement('div');
      div.className = 'memory-item';
      div.style.display = 'flex';
      div.style.alignItems = 'center';
      div.style.justifyContent = 'space-between';
      div.style.padding = '8px';
      div.style.borderBottom = '1px solid var(--border)';
      
      const leftDiv = document.createElement('div');
      leftDiv.style.display = 'flex';
      leftDiv.style.alignItems = 'center';
      leftDiv.style.gap = '8px';
      leftDiv.style.cursor = 'pointer';
      
      let icon = item.is_dir ? '📁' : '📄';
      if (item.name.endsWith('.zip') || item.name.endsWith('.tar.gz') || item.name.endsWith('.tgz')) {
        icon = '📦';
      }
      
      leftDiv.innerHTML = `<span>${icon}</span> <span>${item.name}</span>`;
      leftDiv.onclick = () => {
        if (item.is_dir) {
          loadFiles(item.path);
        } else {
          openFileEditor(item.path, item.name);
        }
      };
      
      const rightDiv = document.createElement('div');
      rightDiv.style.display = 'flex';
      rightDiv.style.gap = '8px';
      rightDiv.style.alignItems = 'center';
      
      if (!item.is_dir) {
        const sizeSpan = document.createElement('span');
        sizeSpan.style.opacity = '0.5';
        sizeSpan.style.fontSize = '12px';
        sizeSpan.textContent = formatSize(item.size);
        rightDiv.appendChild(sizeSpan);
      }
      
      if (icon === '📦') {
        const extractBtn = document.createElement('button');
        extractBtn.className = 'memory-toolbar-btn';
        extractBtn.textContent = 'Extract';
        extractBtn.onclick = async (e) => {
          e.stopPropagation();
          extractArchive(item.path);
        };
        rightDiv.appendChild(extractBtn);
      }
      
      if (!item.is_dir) {
        const downloadBtn = document.createElement('button');
        downloadBtn.className = 'memory-toolbar-btn';
        downloadBtn.textContent = 'Download';
        downloadBtn.onclick = (e) => {
          e.stopPropagation();
          window.open(`/api/files/download?path=${encodeURIComponent(item.path)}`, '_blank');
        };
        rightDiv.appendChild(downloadBtn);
      }
      
      const delBtn = document.createElement('button');
      delBtn.className = 'memory-toolbar-btn danger';
      delBtn.textContent = 'Del';
      delBtn.onclick = async (e) => {
        e.stopPropagation();
        if (confirm(`Delete ${item.name}?`)) {
          deletePath(item.path);
        }
      };
      rightDiv.appendChild(delBtn);
      
      div.appendChild(leftDiv);
      div.appendChild(rightDiv);
      listContainer.appendChild(div);
    }
  } catch (e) {
    uiModule.showToast('Error loading files: ' + e.message);
  }
}

async function extractArchive(path) {
  try {
    const res = await fetch('/api/files/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    });
    if (!res.ok) throw new Error(await res.text());
    uiModule.showToast('Extracted successfully');
    loadFiles(currentPath);
  } catch (e) {
    uiModule.showToast('Extract failed: ' + e.message);
  }
}

async function deletePath(path) {
  try {
    const res = await fetch('/api/files/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    });
    if (!res.ok) throw new Error(await res.text());
    uiModule.showToast('Deleted successfully');
    loadFiles(currentPath);
  } catch (e) {
    uiModule.showToast('Delete failed: ' + e.message);
  }
}

let editingPath = null;
async function openFileEditor(path, name) {
  try {
    const res = await fetch(`/api/files/read?path=${encodeURIComponent(path)}`);
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    
    editingPath = path;
    document.getElementById('files-list').style.display = 'none';
    document.getElementById('files-editor-container').style.display = 'flex';
    document.getElementById('files-editor-name').textContent = name;
    document.getElementById('files-editor-textarea').value = data.content;
  } catch (e) {
    uiModule.showToast('Read failed: ' + e.message);
  }
}

async function saveFileEditor() {
  if (!editingPath) return;
  try {
    const content = document.getElementById('files-editor-textarea').value;
    const res = await fetch('/api/files/write', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: editingPath, content })
    });
    if (!res.ok) throw new Error(await res.text());
    uiModule.showToast('File saved');
  } catch (e) {
    uiModule.showToast('Save failed: ' + e.message);
  }
}

function closeFileEditor() {
  editingPath = null;
  document.getElementById('files-editor-container').style.display = 'none';
  document.getElementById('files-list').style.display = 'block';
  loadFiles(currentPath);
}

document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('files-modal');
  if (!modal) return;
  
  Modals.register('files-modal', () => {
    modal.classList.remove('hidden');
    loadFiles(currentPath);
  }, () => {
    modal.classList.add('hidden');
  });

  const railBtn = document.getElementById('rail-files');
  if (railBtn) {
    railBtn.addEventListener('click', () => {
      Modals.open('files-modal');
    });
  }
  
  const sidebarBtn = document.getElementById('tool-files-btn');
  if (sidebarBtn) {
    sidebarBtn.addEventListener('click', () => {
      Modals.open('files-modal');
    });
  }
  
  document.getElementById('close-files-modal')?.addEventListener('click', () => {
    Modals.close('files-modal');
  });
  
  document.getElementById('files-go-btn')?.addEventListener('click', () => {
    const path = document.getElementById('files-path-input').value;
    loadFiles(path);
  });
  
  
  document.getElementById('files-up-btn')?.addEventListener('click', () => {
    loadFiles(currentPath + '/..');
  });
  
  const uploadInput = document.getElementById('files-upload-input');
  if (uploadInput) {
    uploadInput.addEventListener('change', async (e) => {
      if (!e.target.files.length) return;
      const file = e.target.files[0];
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        const res = await fetch(`/api/files/upload?dir_path=${encodeURIComponent(currentPath)}`, {
          method: 'POST',
          body: formData
        });
        if (!res.ok) throw new Error(await res.text());
        uiModule.showToast('Uploaded successfully');
        loadFiles(currentPath);
      } catch (err) {
        uiModule.showToast('Upload failed: ' + err.message);
      } finally {
        e.target.value = '';
      }
    });
  }
  
  document.getElementById('files-upload-btn')?.addEventListener('click', () => {
    uploadInput?.click();
  });
  
  document.getElementById('files-path-input')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') loadFiles(e.target.value);
  });
  
  document.getElementById('files-editor-save')?.addEventListener('click', saveFileEditor);
  document.getElementById('files-editor-close')?.addEventListener('click', closeFileEditor);
});
