// Tema uyumlu onay modalı. Native confirm() yerine.
// Kullanım:  if (await window.confirmModal({ title:'...', message:'...', danger:true })) { ... }
(function () {
  let overlay = null;

  function build() {
    overlay = document.createElement('div');
    overlay.className = 'overlay';
    overlay.setAttribute('data-testid', 'confirm-modal');
    overlay.innerHTML = `
      <div class="modal" style="max-width:400px;">
        <div style="padding:22px 22px 8px;">
          <h3 data-cm="title" style="font-size:17px;font-weight:600;margin-bottom:6px;"></h3>
          <p data-cm="message" class="muted" style="font-size:14px;line-height:1.55;"></p>
        </div>
        <div style="padding:16px 22px 18px;display:flex;gap:10px;justify-content:flex-end;">
          <button class="btn btn-ghost" data-cm="cancel">Vazgeç</button>
          <button class="btn" data-cm="ok" data-testid="confirm-ok">Onayla</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    return overlay;
  }

  window.confirmModal = function (opts = {}) {
    if (!overlay) build();
    const titleEl = overlay.querySelector('[data-cm="title"]');
    const msgEl = overlay.querySelector('[data-cm="message"]');
    const okBtn = overlay.querySelector('[data-cm="ok"]');
    const cancelBtn = overlay.querySelector('[data-cm="cancel"]');

    titleEl.textContent = opts.title || 'Emin misin?';
    msgEl.textContent = opts.message || '';
    msgEl.style.display = opts.message ? 'block' : 'none';
    okBtn.textContent = opts.confirmText || 'Onayla';
    cancelBtn.textContent = opts.cancelText || 'Vazgeç';
    okBtn.className = 'btn ' + (opts.danger ? 'btn-danger' : 'btn-brand');

    overlay.classList.add('open');
    setTimeout(() => okBtn.focus(), 60);

    return new Promise((resolve) => {
      function cleanup(result) {
        overlay.classList.remove('open');
        okBtn.removeEventListener('click', onOk);
        cancelBtn.removeEventListener('click', onCancel);
        overlay.removeEventListener('click', onBackdrop);
        document.removeEventListener('keydown', onKey);
        resolve(result);
      }
      function onOk() { cleanup(true); }
      function onCancel() { cleanup(false); }
      function onBackdrop(e) { if (e.target === overlay) cleanup(false); }
      function onKey(e) { if (e.key === 'Escape') cleanup(false); if (e.key === 'Enter') cleanup(true); }
      okBtn.addEventListener('click', onOk);
      cancelBtn.addEventListener('click', onCancel);
      overlay.addEventListener('click', onBackdrop);
      document.addEventListener('keydown', onKey);
    });
  };
})();
