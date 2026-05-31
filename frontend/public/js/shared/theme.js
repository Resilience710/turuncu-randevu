// Dark/Light tema yönetimi. <head>'de erken yüklenmeli (FOUC önleme).
(function () {
  const KEY = 'turuncu-theme';

  function apply(mode) {
    const dark = mode === 'dark';
    document.documentElement.classList.toggle('dark', dark);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', dark ? '#020617' : '#F97316');
  }

  function current() {
    return localStorage.getItem(KEY)
      || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  }

  // Erken uygula (script <head>'de senkron çalışır)
  apply(current());

  window.Theme = {
    get: current,
    set(mode) { localStorage.setItem(KEY, mode); apply(mode); window.dispatchEvent(new CustomEvent('themechange', { detail: mode })); },
    toggle() { this.set(current() === 'dark' ? 'light' : 'dark'); },
    isDark() { return current() === 'dark'; },
    // İkon SVG'leri (sun/moon)
    iconSun: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    iconMoon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>',
  };
})();
