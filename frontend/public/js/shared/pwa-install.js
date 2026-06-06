/* Turuncu Randevu — "Uygulamayı yükle" (Ana Ekrana Ekle) yardımcısı.
 *
 * Android / Chrome / Edge: beforeinstallprompt yakalanır → tek tıkla yükleme.
 * iOS / Safari: beforeinstallprompt desteklenmez → "Paylaş → Ana Ekrana Ekle"
 *               talimatı gösterilir.
 * Zaten yüklüyse (standalone) veya yakın zamanda kapatıldıysa görünmez.
 *
 * Sayfaya sadece <script src="/js/shared/pwa-install.js"></script> eklemek yeter.
 * Manuel tetik: window.PWAInstall.show()
 */
(function () {
  if (window.__pwaInstallInit) return;
  window.__pwaInstallInit = true;

  var DISMISS_KEY = 'turuncu-pwa-dismissed';
  var DISMISS_DAYS = 14;

  function isStandalone() {
    return (
      (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) ||
      window.navigator.standalone === true
    );
  }
  function dismissedRecently() {
    try {
      var t = +localStorage.getItem(DISMISS_KEY) || 0;
      return Date.now() - t < DISMISS_DAYS * 864e5;
    } catch (e) { return false; }
  }
  function setDismissed() {
    try { localStorage.setItem(DISMISS_KEY, String(Date.now())); } catch (e) {}
  }

  var ua = navigator.userAgent || '';
  var isIOS = /iphone|ipad|ipod/i.test(ua) && !window.MSStream;
  // iPadOS 13+ masaüstü gibi görünür: dokunmatik + Mac
  if (!isIOS && navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1) isIOS = true;
  var isSafari = /safari/i.test(ua) && !/crios|fxios|edgios|chrome|android/i.test(ua);

  var deferredPrompt = null;
  var bannerEl = null;

  function injectStyles() {
    if (document.getElementById('pwa-install-style')) return;
    var css =
      '#pwa-install-banner{position:fixed;left:12px;right:12px;bottom:12px;z-index:9999;' +
      'max-width:440px;margin:0 auto;background:var(--surface,#fff);color:var(--text,#0f172a);' +
      'border:1px solid var(--border,#e2e8f0);border-radius:16px;' +
      'box-shadow:0 12px 40px -8px rgba(0,0,0,.35);padding:14px 14px 14px 16px;' +
      'display:flex;align-items:center;gap:12px;font-family:Inter,system-ui,sans-serif;' +
      'animation:pwaUp .25s ease;}' +
      '@keyframes pwaUp{from{transform:translateY(18px);opacity:0}to{transform:none;opacity:1}}' +
      '#pwa-install-banner .pwa-ic{width:44px;height:44px;border-radius:11px;flex-shrink:0;' +
      'box-shadow:0 2px 8px rgba(0,0,0,.18);}' +
      '#pwa-install-banner .pwa-tx{flex:1;min-width:0;}' +
      '#pwa-install-banner .pwa-t{font-size:14px;font-weight:700;line-height:1.2;}' +
      '#pwa-install-banner .pwa-s{font-size:12.5px;color:var(--muted,#64748b);margin-top:2px;line-height:1.35;}' +
      '#pwa-install-banner .pwa-go{background:var(--brand,#f97316);color:#fff;border:none;cursor:pointer;' +
      'font-weight:700;font-size:13.5px;padding:9px 16px;border-radius:10px;font-family:inherit;white-space:nowrap;}' +
      '#pwa-install-banner .pwa-go:hover{filter:brightness(1.05);}' +
      '#pwa-install-banner .pwa-x{background:transparent;border:none;color:var(--muted,#94a3b8);cursor:pointer;' +
      'font-size:20px;line-height:1;padding:4px 6px;flex-shrink:0;border-radius:8px;}' +
      '#pwa-install-banner .pwa-x:hover{background:var(--surface-2,#f1f5f9);}' +
      '#pwa-install-banner.pwa-ios{flex-direction:column;align-items:stretch;}' +
      '#pwa-install-banner .pwa-ios-row{display:flex;align-items:center;gap:12px;}' +
      '#pwa-install-banner .pwa-ios-steps{font-size:12.5px;color:var(--muted,#64748b);margin-top:8px;line-height:1.5;}' +
      '#pwa-install-banner .pwa-ios-steps b{color:var(--text,#0f172a);}';
    var s = document.createElement('style');
    s.id = 'pwa-install-style';
    s.textContent = css;
    document.head.appendChild(s);
  }

  function close() {
    setDismissed();
    if (bannerEl && bannerEl.parentNode) bannerEl.parentNode.removeChild(bannerEl);
    bannerEl = null;
  }

  function showAndroid() {
    if (bannerEl || isStandalone()) return;
    injectStyles();
    bannerEl = document.createElement('div');
    bannerEl.id = 'pwa-install-banner';
    bannerEl.setAttribute('role', 'dialog');
    bannerEl.innerHTML =
      '<img class="pwa-ic" src="/icons/icon-192.png" alt="" />' +
      '<div class="pwa-tx"><div class="pwa-t">Uygulamayı yükle</div>' +
      '<div class="pwa-s">Turuncu Randevu\'yu ana ekranına ekle, tek dokunuşla aç.</div></div>' +
      '<button class="pwa-go" type="button">Yükle</button>' +
      '<button class="pwa-x" type="button" aria-label="Kapat">&times;</button>';
    document.body.appendChild(bannerEl);
    bannerEl.querySelector('.pwa-x').onclick = close;
    bannerEl.querySelector('.pwa-go').onclick = function () {
      if (!deferredPrompt) { close(); return; }
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () {
        deferredPrompt = null;
        if (bannerEl && bannerEl.parentNode) bannerEl.parentNode.removeChild(bannerEl);
        bannerEl = null;
      });
    };
  }

  function showIOS() {
    if (bannerEl || isStandalone()) return;
    injectStyles();
    bannerEl = document.createElement('div');
    bannerEl.id = 'pwa-install-banner';
    bannerEl.className = 'pwa-ios';
    bannerEl.setAttribute('role', 'dialog');
    // iOS paylaş ikonu (kare + yukarı ok)
    var share =
      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0a84ff" stroke-width="2" ' +
      'stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-4px"><path d="M12 16V4"/>' +
      '<path d="M8 8l4-4 4 4"/><path d="M20 14v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-6"/></svg>';
    bannerEl.innerHTML =
      '<div class="pwa-ios-row"><img class="pwa-ic" src="/icons/icon-192.png" alt="" />' +
      '<div class="pwa-tx"><div class="pwa-t">Ana ekrana ekle</div>' +
      '<div class="pwa-s">Uygulama gibi kullan, tek dokunuşla aç.</div></div>' +
      '<button class="pwa-x" type="button" aria-label="Kapat">&times;</button></div>' +
      '<div class="pwa-ios-steps">1) Alttaki ' + share + ' <b>Paylaş</b> simgesine dokun &nbsp; ' +
      '2) <b>“Ana Ekrana Ekle”</b>yi seç &nbsp; 3) <b>Ekle</b>’ye dokun.</div>';
    document.body.appendChild(bannerEl);
    bannerEl.querySelector('.pwa-x').onclick = close;
  }

  // Android / Chrome / Edge
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    if (!dismissedRecently()) setTimeout(showAndroid, 1200);
  });

  window.addEventListener('appinstalled', function () {
    if (bannerEl && bannerEl.parentNode) bannerEl.parentNode.removeChild(bannerEl);
    bannerEl = null;
  });

  // iOS Safari: olay yok → talimat banner'ı
  if (isIOS && isSafari && !isStandalone() && !dismissedRecently()) {
    setTimeout(showIOS, 1500);
  }

  // Dışarıdan manuel tetik (örn. bir "Uygulamayı yükle" linki)
  window.PWAInstall = {
    show: function () {
      try { localStorage.removeItem(DISMISS_KEY); } catch (e) {}
      if (isStandalone()) return;
      if (deferredPrompt) showAndroid();
      else if (isIOS) showIOS();
      else showAndroid();
    },
    available: function () { return !!deferredPrompt || (isIOS && isSafari); }
  };
})();
