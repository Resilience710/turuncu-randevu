// Patron/personel dashboard kabuğu: koyu sidebar + sticky topbar + mobil drawer.
// Kullanım: sayfa body'sinde <main class="shell-main">...içerik...</main>,
// sonra Shell.mount({ active:'dashboard', title:'Genel Bakış' }).

(function () {
  const ICONS = {
    dashboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>',
    occupancy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="6" height="16" rx="1.5"/><rect x="10.5" y="4" width="6" height="16" rx="1.5"/><rect x="18" y="4" width="3" height="16" rx="1.5"/></svg>',
    manual: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18M12 14v4M10 16h4"/></svg>',
    business: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18M5 21V7l8-4v18M19 21V11l-6-3"/><path d="M9 9v.01M9 12v.01M9 15v.01"/></svg>',
    staff: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    account: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/></svg>',
    kiosk: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 18h6"/></svg>',
    logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>',
    menu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>',
    chevrons: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 17l-5-5 5-5M18 17l-5-5 5-5"/></svg>',
    logo: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="3"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
  };

  const OWNER_NAV = [
    { key: 'dashboard', label: 'Genel Bakış',    href: '/owner/dashboard.html' },
    { key: 'occupancy', label: 'Doluluk',        href: '/owner/occupancy.html' },
    { key: 'manual',    label: 'Manuel Randevu', href: '/owner/appointments-manual.html' },
    { key: 'business',  label: 'İşletme',        href: '/owner/business-settings.html' },
    { key: 'staff',     label: 'Çalışanlar',     href: '/owner/employees.html' },
    { key: 'account',   label: 'Hesap',          href: '/owner/account.html' },
  ];
  const STAFF_NAV = [
    { key: 'dashboard', label: 'Randevular', href: '/owner/dashboard.html' },
    { key: 'kiosk',     label: 'Kiosk Modu', href: '/staff/kiosk.html' },
    { key: 'account',   label: 'Hesap',      href: '/owner/account.html' },
  ];

  const SB_KEY = 'turuncu-sidebar-collapsed';

  function injectStyles() {
    if (document.getElementById('shell-styles')) return;
    const s = document.createElement('style');
    s.id = 'shell-styles';
    s.textContent = `
      :root { --sb-w: 256px; --tb-h: 60px; }
      html.sb-collapsed { --sb-w: 72px; }
      .sidebar {
        position: fixed; left: 0; top: 0; bottom: 0; width: var(--sb-w); z-index: 50;
        background: var(--sidebar); color: var(--sidebar-text);
        display: flex; flex-direction: column; transition: width .2s ease, transform .22s ease;
        border-right: 1px solid rgba(255,255,255,.06);
      }
      .sb-head { display: flex; align-items: center; gap: 10px; padding: 16px; height: var(--tb-h); }
      .sb-logo { width: 34px; height: 34px; flex-shrink: 0; border-radius: 9px; background: var(--brand); color: #fff; display: flex; align-items: center; justify-content: center; }
      .sb-logo svg { width: 19px; height: 19px; }
      .sb-brand { font-weight: 700; font-size: 15px; color: #fff; white-space: nowrap; overflow: hidden; }
      html.sb-collapsed .sb-brand, html.sb-collapsed .sb-sub, html.sb-collapsed .nav-label, html.sb-collapsed .sb-user-text { display: none; }
      .sb-sub { font-size: 11px; color: var(--sidebar-muted); white-space: nowrap; overflow: hidden; }
      .sb-nav { flex: 1; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 2px; }
      .nav-item {
        display: flex; align-items: center; gap: 11px; padding: 10px 12px; border-radius: 9px;
        color: var(--sidebar-text); text-decoration: none; font-size: 14px; font-weight: 500;
        transition: background .12s, color .12s; white-space: nowrap;
      }
      .nav-item svg { width: 19px; height: 19px; flex-shrink: 0; opacity: .85; }
      .nav-item:hover { background: rgba(255,255,255,.06); color: #fff; }
      .nav-item.active { background: var(--sidebar-active); color: var(--brand-strong); }
      html.dark .nav-item.active { color: var(--brand); }
      .nav-item.active svg { opacity: 1; }
      html.sb-collapsed .nav-item { justify-content: center; padding: 10px; }
      .sb-foot { padding: 8px; border-top: 1px solid rgba(255,255,255,.06); display: flex; flex-direction: column; gap: 2px; }
      .sb-user { display: flex; align-items: center; gap: 10px; padding: 8px 10px; }
      .sb-avatar { width: 32px; height: 32px; border-radius: 999px; background: var(--brand); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; flex-shrink: 0; }
      .sb-user-text { overflow: hidden; }
      .sb-user-name { font-size: 13px; font-weight: 600; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .sb-user-role { font-size: 11px; color: var(--sidebar-muted); }

      .shell-main { margin-left: var(--sb-w); min-height: 100vh; transition: margin-left .2s ease; display: flex; flex-direction: column; }
      .topbar {
        position: sticky; top: 0; z-index: 40; height: var(--tb-h);
        display: flex; align-items: center; justify-content: space-between; gap: 12px;
        padding: 0 20px; background: color-mix(in srgb, var(--surface) 85%, transparent);
        backdrop-filter: blur(8px); border-bottom: 1px solid var(--border);
      }
      .topbar h1 { font-size: 18px; font-weight: 600; }
      .tb-left { display: flex; align-items: center; gap: 12px; min-width: 0; }
      .tb-right { display: flex; align-items: center; gap: 8px; }
      .icon-btn { width: 38px; height: 38px; border-radius: 9px; border: 1px solid transparent; background: transparent; color: var(--muted); display: inline-flex; align-items: center; justify-content: center; cursor: pointer; transition: background .12s, color .12s; }
      .icon-btn:hover { background: var(--surface-2); color: var(--text); }
      .icon-btn svg { width: 19px; height: 19px; }
      .shell-page { padding: 22px 20px 48px; max-width: 1200px; width: 100%; margin: 0 auto; flex: 1; }
      .hamburger { display: none; }
      .sb-backdrop { display: none; position: fixed; inset: 0; background: rgba(15,23,42,.5); z-index: 49; }
      .sb-collapse-btn { margin-left: auto; }

      @media (max-width: 1023px) {
        .sidebar { transform: translateX(-100%); width: 264px; }
        html.sb-open .sidebar { transform: translateX(0); }
        html.sb-open .sb-backdrop { display: block; }
        .shell-main { margin-left: 0; }
        .hamburger { display: inline-flex; }
        .sb-collapse-btn { display: none; }
        html.sb-collapsed .sb-brand, html.sb-collapsed .nav-label { display: inline; }
      }
    `;
    document.head.appendChild(s);
  }

  const Shell = {
    mount(opts) {
      opts = opts || {};
      injectStyles();
      const session = window.API.getSession();
      if (!session || !session.user) { location.href = '/index.html'; return; }
      const role = session.user.role;
      const nav = role === 'staff' ? STAFF_NAV : OWNER_NAV;
      const biz = session.business || {};
      const u = session.user;
      const initials = (u.name || '?').trim().charAt(0).toUpperCase();

      // Sidebar
      const aside = document.createElement('aside');
      aside.className = 'sidebar';
      aside.setAttribute('data-testid', 'sidebar');
      aside.innerHTML = `
        <div class="sb-head">
          <div class="sb-logo">${ICONS.logo}</div>
          <div style="min-width:0;">
            <div class="sb-brand">${biz.name || 'Turuncu Randevu'}</div>
            <div class="sb-sub">${role === 'owner' ? 'İşletme paneli' : 'Personel paneli'}</div>
          </div>
        </div>
        <nav class="sb-nav">
          ${nav.map(n => `
            <a class="nav-item ${n.key === opts.active ? 'active' : ''}" href="${n.href}" data-testid="nav-${n.key}" title="${n.label}">
              ${ICONS[n.key] || ICONS.dashboard}<span class="nav-label">${n.label}</span>
            </a>`).join('')}
        </nav>
        <div class="sb-foot">
          <div class="sb-user">
            <div class="sb-avatar">${initials}</div>
            <div class="sb-user-text">
              <div class="sb-user-name">${u.name || ''}</div>
              <div class="sb-user-role">${role === 'owner' ? 'İşletme sahibi' : (u.title || 'Personel')}</div>
            </div>
          </div>
          <a class="nav-item" href="#" data-testid="sidebar-logout" id="sb-logout">${ICONS.logout}<span class="nav-label">Çıkış yap</span></a>
        </div>`;
      document.body.insertBefore(aside, document.body.firstChild);

      const backdrop = document.createElement('div');
      backdrop.className = 'sb-backdrop';
      document.body.insertBefore(backdrop, document.body.firstChild);

      // Topbar — main'in başına
      const main = document.querySelector('.shell-main');
      const topbar = document.createElement('header');
      topbar.className = 'topbar';
      topbar.innerHTML = `
        <div class="tb-left">
          <button class="icon-btn hamburger" id="tb-hamburger" aria-label="Menü" data-testid="hamburger">${ICONS.menu}</button>
          <button class="icon-btn sb-collapse-btn" id="tb-collapse" aria-label="Menüyü daralt" title="Daralt">${ICONS.chevrons}</button>
          <h1>${opts.title || ''}</h1>
        </div>
        <div class="tb-right">
          <button class="icon-btn" id="tb-theme" aria-label="Tema" title="Tema değiştir">${window.Theme.isDark() ? window.Theme.iconSun : window.Theme.iconMoon}</button>
        </div>`;
      if (main) main.insertBefore(topbar, main.firstChild);

      // Collapsed state
      if (localStorage.getItem(SB_KEY) === '1') document.documentElement.classList.add('sb-collapsed');

      // Events
      document.getElementById('sb-logout').addEventListener('click', (e) => { e.preventDefault(); window.Auth.logout(); });
      document.getElementById('tb-hamburger').addEventListener('click', () => document.documentElement.classList.toggle('sb-open'));
      backdrop.addEventListener('click', () => document.documentElement.classList.remove('sb-open'));
      document.getElementById('tb-collapse').addEventListener('click', () => {
        const c = document.documentElement.classList.toggle('sb-collapsed');
        localStorage.setItem(SB_KEY, c ? '1' : '0');
      });
      const themeBtn = document.getElementById('tb-theme');
      themeBtn.addEventListener('click', () => {
        window.Theme.toggle();
        themeBtn.innerHTML = window.Theme.isDark() ? window.Theme.iconSun : window.Theme.iconMoon;
      });

      return session;
    },
  };

  window.Shell = Shell;
})();
