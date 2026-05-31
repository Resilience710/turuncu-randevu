// KVKK Aydınlatma Metni modalı. window.openKvkkModal() ile çağrılır.
(function () {
  let overlay = null, cachedText = null;

  async function fetchText() {
    if (cachedText) return cachedText;
    try { const data = await window.API.get('/kvkk-text'); cachedText = data.text || ''; }
    catch { cachedText = 'KVKK metni yüklenemedi.'; }
    return cachedText;
  }

  function build() {
    overlay = document.createElement('div');
    overlay.className = 'overlay';
    overlay.setAttribute('data-testid', 'kvkk-modal');
    overlay.innerHTML = `
      <div class="modal" style="max-width:560px;">
        <div style="padding:18px 22px;border-bottom:1px solid var(--border);">
          <h2 style="font-size:18px;font-weight:600;">KVKK Aydınlatma Metni</h2>
        </div>
        <div data-testid="kvkk-modal-body" style="padding:20px 22px;overflow-y:auto;flex:1;font-size:13.5px;line-height:1.7;color:var(--text-2);white-space:pre-line;">Yükleniyor…</div>
        <div style="padding:14px 22px;border-top:1px solid var(--border);display:flex;justify-content:flex-end;">
          <button class="btn btn-brand" data-testid="kvkk-modal-close">Kapat</button>
        </div>
      </div>`;
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.classList.remove('open'); });
    overlay.querySelector('[data-testid="kvkk-modal-close"]').addEventListener('click', () => overlay.classList.remove('open'));
    document.body.appendChild(overlay);
    return overlay.querySelector('[data-testid="kvkk-modal-body"]');
  }

  window.openKvkkModal = async function () {
    const body = overlay ? overlay.querySelector('[data-testid="kvkk-modal-body"]') : build();
    overlay.classList.add('open');
    body.textContent = await fetchText();
  };
})();
