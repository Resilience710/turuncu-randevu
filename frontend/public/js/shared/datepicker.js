// Tema uyumlu tarih seçici. Geçmiş günler kapalı (min varsayılan: bugün).
// Kullanım:
//   const dp = Datepicker.attach(inputEl, { value:'2026-06-20', onChange:(v)=>{} });
//   dp.getValue() -> 'YYYY-MM-DD'
(function () {
  const MONTHS = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];
  const DOW = ['Pt','Sa','Ça','Pe','Cu','Ct','Pz'];

  function injectStyles() {
    if (document.getElementById('dp-styles')) return;
    const s = document.createElement('style');
    s.id = 'dp-styles';
    s.textContent = `
      .dp-pop { position:absolute; z-index:120; width:280px; background:var(--surface); border:1px solid var(--border);
        border-radius:14px; box-shadow:var(--shadow-lg); padding:12px; display:none; }
      .dp-pop.open { display:block; }
      .dp-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; }
      .dp-title { font-weight:600; font-size:14px; }
      .dp-nav { width:30px; height:30px; border-radius:8px; border:none; background:var(--surface-2); color:var(--text);
        cursor:pointer; display:flex; align-items:center; justify-content:center; }
      .dp-nav:hover { background:var(--border); }
      .dp-nav:disabled { opacity:.35; cursor:not-allowed; }
      .dp-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:2px; }
      .dp-dow { text-align:center; font-size:11px; font-weight:600; color:var(--muted); padding:4px 0; }
      .dp-day { aspect-ratio:1; border:none; background:transparent; color:var(--text); border-radius:8px; cursor:pointer;
        font-size:13px; font-family:inherit; display:flex; align-items:center; justify-content:center; }
      .dp-day:hover:not(:disabled) { background:var(--surface-2); }
      .dp-day.today { font-weight:700; color:var(--brand-strong); }
      .dp-day.selected { background:var(--brand); color:var(--on-brand); }
      .dp-day:disabled { color:var(--faint); opacity:.4; cursor:not-allowed; }
      .dp-day.empty { visibility:hidden; }
      .dp-input { cursor:pointer; }
    `;
    document.head.appendChild(s);
  }

  function fmt(d) { return `${String(d.getDate()).padStart(2,'0')} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`; }
  function iso(d) { return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
  function startOfDay(d) { const x = new Date(d); x.setHours(0,0,0,0); return x; }

  const Datepicker = {
    attach(input, opts = {}) {
      injectStyles();
      input.readOnly = true;
      input.classList.add('dp-input');

      const min = startOfDay(opts.min ? new Date(opts.min) : new Date());
      let selected = opts.value ? startOfDay(new Date(opts.value)) : null;
      let view = new Date(selected || min);
      view.setDate(1);

      const pop = document.createElement('div');
      pop.className = 'dp-pop';
      // input'un konteynerine ekle (relative)
      const wrap = input.parentElement;
      if (getComputedStyle(wrap).position === 'static') wrap.style.position = 'relative';
      wrap.appendChild(pop);

      function setValue(d) {
        selected = startOfDay(d);
        input.value = fmt(selected);
        input.dataset.value = iso(selected);
        if (opts.onChange) opts.onChange(iso(selected));
      }
      if (selected) setValue(selected); else { input.value = ''; input.placeholder = opts.placeholder || 'Tarih seç'; }

      function render() {
        const y = view.getFullYear(), m = view.getMonth();
        const first = new Date(y, m, 1);
        let startDow = (first.getDay() + 6) % 7; // Pazartesi=0
        const days = new Date(y, m+1, 0).getDate();
        const prevDisabled = (y < min.getFullYear()) || (y === min.getFullYear() && m <= min.getMonth());

        let html = `<div class="dp-head">
          <button type="button" class="dp-nav" data-nav="-1" ${prevDisabled?'disabled':''} aria-label="Önceki ay">‹</button>
          <span class="dp-title">${MONTHS[m]} ${y}</span>
          <button type="button" class="dp-nav" data-nav="1" aria-label="Sonraki ay">›</button>
        </div><div class="dp-grid">`;
        DOW.forEach(d => html += `<div class="dp-dow">${d}</div>`);
        for (let i=0;i<startDow;i++) html += `<button type="button" class="dp-day empty" disabled></button>`;
        const today = startOfDay(new Date());
        for (let d=1; d<=days; d++) {
          const cur = startOfDay(new Date(y, m, d));
          const disabled = cur < min;
          const cls = ['dp-day'];
          if (+cur === +today) cls.push('today');
          if (selected && +cur === +selected) cls.push('selected');
          html += `<button type="button" class="${cls.join(' ')}" data-d="${d}" ${disabled?'disabled':''}>${d}</button>`;
        }
        html += `</div>`;
        pop.innerHTML = html;
        pop.querySelectorAll('[data-nav]').forEach(b => b.addEventListener('click', (e) => {
          e.stopPropagation(); view.setMonth(view.getMonth() + parseInt(b.dataset.nav)); render();
        }));
        pop.querySelectorAll('[data-d]').forEach(b => b.addEventListener('click', (e) => {
          e.stopPropagation(); setValue(new Date(view.getFullYear(), view.getMonth(), parseInt(b.dataset.d))); close();
        }));
      }

      function open() { render(); pop.style.top = (input.offsetTop + input.offsetHeight + 6) + 'px'; pop.style.left = input.offsetLeft + 'px'; pop.classList.add('open'); }
      function close() { pop.classList.remove('open'); }
      function toggle() { pop.classList.contains('open') ? close() : open(); }

      input.addEventListener('click', (e) => { e.stopPropagation(); toggle(); });
      document.addEventListener('click', (e) => { if (!pop.contains(e.target) && e.target !== input) close(); });

      return {
        getValue: () => input.dataset.value || '',
        setMin: (d) => { /* future use */ },
        open, close,
      };
    },
  };

  window.Datepicker = Datepicker;
})();
