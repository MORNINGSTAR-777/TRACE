// ─── TRACE Main JS ─────────────────────────────────────────────────────────

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
  const sidebar = document.getElementById('sidebar');
  const toggle = document.querySelector('.menu-toggle');
  if (sidebar && toggle && !sidebar.contains(e.target) && !toggle.contains(e.target)) {
    sidebar.classList.remove('open');
  }
});

// ─── Toast Notifications ───────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle' };
  toast.innerHTML = `<i class="fas ${icons[type] || icons.info}"></i><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transform = 'translateX(100%)'; toast.style.transition = '0.3s'; setTimeout(() => toast.remove(), 300); }, duration);
}

// ─── API Helpers ───────────────────────────────────────────────────────────
async function apiGet(url) {
  const r = await fetch(url);
  return r.json();
}

async function apiPost(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return r.json();
}

async function apiDelete(url) {
  const r = await fetch(url, { method: 'DELETE' });
  return r.json();
}

// ─── Modal Helpers ─────────────────────────────────────────────────────────
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

// ─── Spinner ───────────────────────────────────────────────────────────────
function showSpinner(msg = 'Processing...') {
  let el = document.getElementById('globalSpinner');
  if (!el) {
    el = document.createElement('div');
    el.id = 'globalSpinner';
    el.className = 'spinner-overlay';
    el.innerHTML = `<div class="spinner-big"></div><p style="font-weight:600;color:#1a202c;">${msg}</p>`;
    document.body.appendChild(el);
  } else {
    el.querySelector('p').textContent = msg;
    el.classList.remove('hidden');
  }
}

function hideSpinner() {
  const el = document.getElementById('globalSpinner');
  if (el) el.classList.add('hidden');
}

// ─── Format Helpers ────────────────────────────────────────────────────────
function formatDate(dt) {
  if (!dt) return '—';
  const d = new Date(dt);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) +
    ' ' + d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

function severityBadge(sev) {
  return `<span class="badge badge-${sev}"><span class="severity-dot ${sev}"></span>${sev.toUpperCase()}</span>`;
}

function statusBadge(status) {
  return `<span class="badge badge-${status}">${status.charAt(0).toUpperCase() + status.slice(1)}</span>`;
}

// ─── Confirm Dialog ────────────────────────────────────────────────────────
function confirmAction(message, onConfirm) {
  if (confirm(message)) onConfirm();
}
