// Toast bildirimi — tasarım sistemine uyumlu (CSS değişkenleri, koyu/açık).
(function () {
  let container = null;
  function ensureContainer() {
    if (container) return container;
    container = document.createElement('div');
    container.setAttribute('data-testid', 'toast-container');
    Object.assign(container.style, {
      position: 'fixed', top: '16px', left: '50%', transform: 'translateX(-50%)',
      zIndex: '9999', display: 'flex', flexDirection: 'column', gap: '8px',
      pointerEvents: 'none', width: 'max-content', maxWidth: '92vw',
    });
    document.body.appendChild(container);
    return container;
  }

  const ICON = {
    info: '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>',
    success: '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2.6"><path d="M20 6L9 17l-5-5"/></svg>',
    error: '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>',
  };
  const ACCENT = { info: 'var(--accent)', success: 'var(--success)', error: 'var(--danger)' };

  function show(message, opts = {}) {
    const variant = opts.variant || 'info';
    const el = document.createElement('div');
    el.setAttribute('data-testid', `toast-${variant}`);
    Object.assign(el.style, {
      display: 'flex', alignItems: 'center', gap: '10px',
      background: 'var(--surface)', color: 'var(--text)',
      border: '1px solid var(--border)', borderLeft: `3px solid ${ACCENT[variant]}`,
      padding: '11px 16px', borderRadius: '11px', fontSize: '14px', fontWeight: '500',
      boxShadow: 'var(--shadow-lg)', pointerEvents: 'auto',
      transition: 'opacity .3s, transform .3s', opacity: '0', transform: 'translateY(-8px)',
    });
    el.innerHTML = `<span style="color:${ACCENT[variant]};display:flex;flex-shrink:0;">${ICON[variant]}</span><span>${message}</span>`;
    ensureContainer().appendChild(el);
    requestAnimationFrame(() => { el.style.opacity = '1'; el.style.transform = 'translateY(0)'; });
    setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateY(-8px)'; setTimeout(() => el.remove(), 320); }, opts.duration || 3500);
  }

  window.Toast = {
    info: (m, o) => show(m, { ...o, variant: 'info' }),
    success: (m, o) => show(m, { ...o, variant: 'success' }),
    error: (m, o) => show(m, { ...o, variant: 'error' }),
  };
})();
