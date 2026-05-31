// Tüm sayfalarda ortak Tailwind config.
// Renkler CSS değişkenlerine bağlı (theme.css), böylece dark mode tek yerden döner.
window.__tw = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand:        'var(--brand)',
        'brand-hover':'var(--brand-hover)',
        'brand-strong':'var(--brand-strong)',
        'brand-subtle':'var(--brand-subtle)',
        bg:           'var(--bg)',
        surface:      'var(--surface)',
        'surface-2':  'var(--surface-2)',
        sidebar:      'var(--sidebar)',
        border:       'var(--border)',
        'border-strong':'var(--border-strong)',
        ink:          'var(--text)',
        'ink-2':      'var(--text-2)',
        muted:        'var(--muted)',
        faint:        'var(--faint)',
        accent:       'var(--accent)',
        success:      'var(--success)',
        warning:      'var(--warning)',
        danger:       'var(--danger)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: 'var(--shadow)',
        pop:  'var(--shadow-pop)',
        lg:   'var(--shadow-lg)',
      },
      borderRadius: {
        DEFAULT: '12px',
      },
    },
  },
};
if (window.tailwind) window.tailwind.config = window.__tw;
