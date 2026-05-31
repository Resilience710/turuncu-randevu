// Müşteri (consumer) navigasyonu: üstte nav bar (desktop) + altta tab bar (mobil).
// Kullanım: body'de <main class="consumer-main">...</main>, sonra TopNav.mount('home').

(function () {
  const ICONS = {
    home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>',
    appts: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
    account: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/></svg>',
    logo: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="3"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
  };
  const TABS = [
    { key: 'home',    label: 'Keşfet',      href: '/customer/businesses.html' },
    { key: 'appts',   label: 'Randevularım', href: '/customer/my-appointments.html' },
    { key: 'account', label: 'Hesabım',     href: '/customer/account.html' },
  ];

  function injectStyles() {
    if (document.getElementById('topnav-styles')) return;
    const s = document.createElement('style');
    s.id = 'topnav-styles';
    s.textContent = `
      .topnav {
        position: sticky; top: 0; z-index: 40; height: 60px;
        background: color-mix(in srgb, var(--surface) 88%, transparent); backdrop-filter: blur(8px);
        border-bottom: 1px solid var(--border);
        display: flex; align-items: center; justify-content: space-between; gap: 16px;
        padding: 0 20px;
      }
      .tn-brand { display: flex; align-items: center; gap: 10px; text-decoration: none; color: var(--text); font-weight: 700; font-size: 15px; }
      .tn-logo { width: 32px; height: 32px; border-radius: 9px; background: var(--brand); color: #fff; display: flex; align-items: center; justify-content: center; }
      .tn-logo svg { width: 18px; height: 18px; }
      .tn-links { display: flex; align-items: center; gap: 4px; }
      .tn-link { padding: 8px 14px; border-radius: 9px; text-decoration: none; color: var(--muted); font-size: 14px; font-weight: 500; transition: background .12s, color .12s; }
      .tn-link:hover { background: var(--surface-2); color: var(--text); }
      .tn-link.active { color: var(--brand-strong); background: var(--brand-subtle); }
      html.dark .tn-link.active { color: var(--brand); }
      .tn-right { display: flex; align-items: center; gap: 8px; }
      .tn-icon { width: 38px; height: 38px; border-radius: 9px; border: none; background: transparent; color: var(--muted); display: inline-flex; align-items: center; justify-content: center; cursor: pointer; transition: background .12s, color .12s; }
      .tn-icon:hover { background: var(--surface-2); color: var(--text); }
      .tn-icon svg { width: 19px; height: 19px; }
      .tn-avatar { width: 34px; height: 34px; border-radius: 999px; background: var(--brand); color: #fff; font-weight: 700; font-size: 13px; display: flex; align-items: center; justify-content: center; cursor: pointer; text-decoration: none; }

      .consumer-main { min-height: 100vh; }
      .consumer-page { max-width: 920px; margin: 0 auto; padding: 24px 20px 96px; }

      .tabbar { display: none; }
      @media (max-width: 767px) {
        .tn-links { display: none; }
        .tabbar {
          display: flex; position: fixed; left: 0; right: 0; bottom: 0; z-index: 40;
          background: var(--surface); border-top: 1px solid var(--border);
          padding: 6px 4px calc(6px + env(safe-area-inset-bottom));
        }
        .tab {
          flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px;
          text-decoration: none; color: var(--muted); font-size: 11px; font-weight: 600; padding: 4px 0; border-radius: 10px;
        }
        .tab svg { width: 22px; height: 22px; }
        .tab.active { color: var(--brand); }
      }
    `;
    document.head.appendChild(s);
  }

  const TopNav = {
    mount(active) {
      injectStyles();
      const session = window.API.getSession();
      const initials = (session?.user?.name || '?').trim().charAt(0).toUpperCase();

      const nav = document.createElement('nav');
      nav.className = 'topnav';
      nav.setAttribute('data-testid', 'topnav');
      nav.innerHTML = `
        <a class="tn-brand" href="/customer/businesses.html">
          <span class="tn-logo">${ICONS.logo}</span><span>Turuncu Randevu</span>
        </a>
        <div class="tn-links">
          ${TABS.map(t => `<a class="tn-link ${t.key === active ? 'active' : ''}" href="${t.href}" data-testid="nav-${t.key}">${t.label}</a>`).join('')}
        </div>
        <div class="tn-right">
          <button class="tn-icon" id="tn-theme" aria-label="Tema" title="Tema değiştir">${window.Theme.isDark() ? window.Theme.iconSun : window.Theme.iconMoon}</button>
          <a class="tn-avatar" href="/customer/account.html" data-testid="nav-avatar" title="Hesabım">${initials}</a>
        </div>`;
      document.body.insertBefore(nav, document.body.firstChild);

      // Mobil alt tab bar
      const bar = document.createElement('nav');
      bar.className = 'tabbar';
      bar.setAttribute('data-testid', 'tabbar');
      bar.innerHTML = TABS.map(t => `
        <a class="tab ${t.key === active ? 'active' : ''}" href="${t.href}" data-testid="tab-${t.key}">
          ${ICONS[t.key]}<span>${t.label}</span>
        </a>`).join('');
      document.body.appendChild(bar);

      const tb = document.getElementById('tn-theme');
      tb.addEventListener('click', () => { window.Theme.toggle(); tb.innerHTML = window.Theme.isDark() ? window.Theme.iconSun : window.Theme.iconMoon; });

      return session;
    },
  };

  window.TopNav = TopNav;
})();
