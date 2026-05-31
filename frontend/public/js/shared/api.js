// Ortak API çağrıları + token yönetimi. Modül scope.
// Üretimde config.js içinden API_BASE override edilir.

// Dev'de (frontend 5173, backend 8000) farklı origin. Hostname dinamik —
// LAN'daki başka bir cihazdan açıldığında da doğru backend'e gitsin.
const API_BASE = (
  window.__API_BASE
  || (typeof localStorage !== 'undefined' && localStorage.getItem('turuncu-api-base'))
  || (location.port === '5173' ? `${location.protocol}//${location.hostname}:8000/api` : '/api')
).replace(/\/$/, '');
const SESSION_KEY = 'turuncu-randevu-session';

function getSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function setSession(session) {
  if (session) localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  else localStorage.removeItem(SESSION_KEY);
}

function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

async function apiFetch(path, options = {}) {
  const session = getSession();
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (session?.token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${session.token}`);
  }

  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    // Oturum süresi dolmuş olabilir
    clearSession();
    if (!path.startsWith('/auth/') && !path.startsWith('/me')) {
      const next = encodeURIComponent(location.pathname + location.search);
      location.href = `/index.html?next=${next}`;
      throw new Error('Oturum sona erdi');
    }
  }

  const contentType = res.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await res.json() : await res.text();

  if (!res.ok) {
    let msg;
    if (Array.isArray(data?.detail)) {
      // FastAPI 422 doğrulama hataları: liste -> okunur metin
      msg = data.detail.map((d) => (d.msg || JSON.stringify(d)).replace(/^Value error,\s*/, '')).join(' ');
    } else {
      msg = (data && data.detail) || data?.message || `HTTP ${res.status}`;
    }
    throw new Error(msg);
  }
  return data;
}

// Şifre kuralı (kayıt/yeni şifre için): en az 8 karakter, harf + rakam.
window.validatePassword = function (pw) {
  if (!pw || pw.length < 8) return 'Şifre en az 8 karakter olmalı.';
  if (!/[A-Za-zğüşıöçĞÜŞİÖÇ]/.test(pw) || !/[0-9]/.test(pw)) return 'Şifre en az bir harf ve bir rakam içermeli.';
  return null;
};

// Tüm telefon (type=tel) alanlarına otomatik sınır: yalnız rakam/boşluk/+,
// en fazla 12 rakam (90 + 10 hane). "Sonsuza kadar giriliyor" sorununu çözer.
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input[type="tel"]').forEach((el) => {
    if (!el.getAttribute('maxlength')) el.setAttribute('maxlength', '18');
    el.addEventListener('input', () => {
      let v = el.value.replace(/[^\d+\s]/g, '');
      v = v.replace(/(?!^)\+/g, ''); // + sadece başta
      let count = 0, out = '';
      for (const ch of v) {
        if (/\d/.test(ch)) { if (count >= 12) continue; count++; }
        out += ch;
      }
      if (out !== el.value) el.value = out;
    });
  });
});

window.API = {
  base: API_BASE,
  getSession,
  setSession,
  clearSession,
  fetch: apiFetch,
  get: (p) => apiFetch(p),
  post: (p, body) => apiFetch(p, { method: 'POST', body: JSON.stringify(body) }),
  put: (p, body) => apiFetch(p, { method: 'PUT', body: JSON.stringify(body) }),
  patch: (p, body) => apiFetch(p, { method: 'PATCH', body: JSON.stringify(body || {}) }),
  delete: (p) => apiFetch(p, { method: 'DELETE' }),
};
