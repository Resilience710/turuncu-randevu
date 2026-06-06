/* Turuncu Randevu — "Uygulamayı yükle / Ana Ekrana Ekle" yardımcısı.
 *
 * Android / Chrome / Edge : beforeinstallprompt → tek tıkla yükleme.
 * iPhone Safari/Chrome     : Paylaş → "Ana Ekrana Ekle" talimatı + alt çubuğa
 *                            işaret eden aşağı ok.
 * iPad Safari              : sağ üstteki Paylaş'a işaret eden talimat.
 * In-app tarayıcı          : (Instagram/Facebook/WhatsApp...) "Safari'de aç"
 *                            uyarısı — bu tarayıcılarda ana ekrana ekleme YOK.
 *
 * Zaten yüklüyse (standalone) gizli. Otomatik banner kapatılınca 14 gün
 * görünmez; ama Hesap sayfasındaki "Yükle" butonu (window.PWAInstall.show())
 * her zaman tekrar açar.
 */
(function () {
  if (window.__pwaInstallInit) return;
  window.__pwaInstallInit = true;

  var DISMISS_KEY = 'turuncu-pwa-dismissed';
  var DISMISS_DAYS = 14;

  var ua = navigator.userAgent || '';
  var isIPad = /ipad/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var isIPhone = /iphone|ipod/i.test(ua) && !window.MSStream;
  var isIOS = isIPhone || isIPad;
  // In-app (gömülü) tarayıcılar — ana ekrana ekleme desteklenmez:
  var inApp = /FBAN|FBAV|FB_IAB|Instagram|Line|Twitter|MicroMessenger|WhatsApp|Snapchat|TikTok|Pinterest|; ?wv\)/i.test(ua);

  var deferredPrompt = null;
  var el = null;

  function isStandalone() {
    return (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) ||
      window.navigator.standalone === true;
  }
  function dismissedRecently() {
    try { return Date.now() - (+localStorage.getItem(DISMISS_KEY) || 0) < DISMISS_DAYS * 864e5; }
    catch (e) { return false; }
  }
  function setDismissed() { try { localStorage.setItem(DISMISS_KEY, String(Date.now())); } catch (e) {} }
  function clearDismissed() { try { localStorage.removeItem(DISMISS_KEY); } catch (e) {} }

  function remove() {
    if (el && el.parentNode) el.parentNode.removeChild(el);
    el = null;
    var ov = document.getElementById('pwa-ov');
    if (ov && ov.parentNode) ov.parentNode.removeChild(ov);
    var ar = document.getElementById('pwa-arrow');
    if (ar && ar.parentNode) ar.parentNode.removeChild(ar);
  }
  function close() { setDismissed(); remove(); }

  function injectStyles() {
    if (document.getElementById('pwa-install-style')) return;
    var css =
      '#pwa-ov{position:fixed;inset:0;z-index:99998;background:rgba(2,6,23,.45);' +
      'animation:pwaFade .2s ease;}' +
      '@keyframes pwaFade{from{opacity:0}to{opacity:1}}' +
      '@keyframes pwaUp{from{transform:translateY(24px);opacity:0}to{transform:none;opacity:1}}' +
      '@keyframes pwaBounce{0%,100%{transform:translateY(0)}50%{transform:translateY(7px)}}' +
      '#pwa-card{position:fixed;left:12px;right:12px;z-index:99999;max-width:430px;margin:0 auto;' +
      'background:var(--surface,#fff);color:var(--text,#0f172a);border:1px solid var(--border,#e2e8f0);' +
      'border-radius:18px;box-shadow:0 18px 50px -10px rgba(0,0,0,.45);padding:16px;' +
      "font-family:Inter,system-ui,'Segoe UI',sans-serif;animation:pwaUp .25s ease;}" +
      '#pwa-card.bottom{bottom:calc(env(safe-area-inset-bottom,0px) + 14px);}' +
      '#pwa-card.top{top:calc(env(safe-area-inset-top,0px) + 14px);}' +
      '#pwa-card .h{display:flex;align-items:center;gap:12px;}' +
      '#pwa-card .ic{width:46px;height:46px;border-radius:12px;flex-shrink:0;box-shadow:0 2px 8px rgba(0,0,0,.18);}' +
      '#pwa-card .t{font-size:15.5px;font-weight:700;line-height:1.2;}' +
      '#pwa-card .s{font-size:13px;color:var(--muted,#64748b);margin-top:2px;line-height:1.35;}' +
      '#pwa-card .x{margin-left:auto;background:transparent;border:none;color:var(--muted,#94a3b8);' +
      'font-size:24px;line-height:1;padding:2px 6px;cursor:pointer;border-radius:8px;align-self:flex-start;}' +
      '#pwa-card .go{display:block;width:100%;margin-top:14px;background:var(--brand,#f97316);color:#fff;' +
      'border:none;cursor:pointer;font-weight:700;font-size:15px;padding:13px;border-radius:12px;font-family:inherit;}' +
      '#pwa-card .steps{margin-top:14px;display:flex;flex-direction:column;gap:10px;}' +
      '#pwa-card .step{display:flex;align-items:center;gap:10px;font-size:13.5px;line-height:1.3;}' +
      '#pwa-card .step .n{flex-shrink:0;width:22px;height:22px;border-radius:50%;background:var(--brand-subtle,#fff7ed);' +
      'color:var(--brand-strong,#ea580c);font-weight:700;font-size:12px;display:flex;align-items:center;justify-content:center;}' +
      '#pwa-card .step b{color:var(--text,#0f172a);}' +
      '#pwa-card .glyph{display:inline-flex;vertical-align:-5px;margin:0 1px;}' +
      '#pwa-arrow{position:fixed;left:50%;transform:translateX(-50%);z-index:99999;color:var(--brand,#f97316);' +
      'animation:pwaBounce 1.1s ease-in-out infinite;filter:drop-shadow(0 2px 4px rgba(0,0,0,.25));}' +
      '#pwa-arrow.down{bottom:calc(env(safe-area-inset-bottom,0px) + 2px);}' +
      '#pwa-arrow.top{top:calc(env(safe-area-inset-top,0px) + 2px);}';
    var s = document.createElement('style');
    s.id = 'pwa-install-style';
    s.textContent = css;
    document.head.appendChild(s);
  }

  // iOS Safari "Paylaş" simgesi (kare + yukarı ok)
  var SHARE_SVG =
    '<svg class="glyph" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#0a84ff" ' +
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 15V4"/>' +
    '<path d="M8 8l4-4 4 4"/><path d="M20 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-6"/></svg>';

  function mountOverlay() {
    var ov = document.createElement('div'); ov.id = 'pwa-ov';
    ov.onclick = close; document.body.appendChild(ov); return ov;
  }

  // --- Android: tek tıkla yükleme ---
  function showAndroid() {
    if (el || isStandalone()) return;
    injectStyles();
    el = document.createElement('div'); el.id = 'pwa-card'; el.className = 'bottom';
    el.setAttribute('role', 'dialog');
    el.innerHTML =
      '<div class="h"><img class="ic" src="/icons/icon-192.png" alt=""/>' +
      '<div><div class="t">Uygulamayı yükle</div>' +
      '<div class="s">Ana ekranına ekle, tek dokunuşla aç.</div></div>' +
      '<button class="x" aria-label="Kapat">&times;</button></div>' +
      '<button class="go">Yükle</button>';
    document.body.appendChild(el);
    el.querySelector('.x').onclick = close;
    el.querySelector('.go').onclick = function () {
      if (!deferredPrompt) { close(); return; }
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () { deferredPrompt = null; remove(); });
    };
  }

  // --- iPhone / iPad: Paylaş → Ana Ekrana Ekle talimatı ---
  function showIOS() {
    if (el || isStandalone()) return;
    injectStyles();
    mountOverlay();
    el = document.createElement('div'); el.id = 'pwa-card';
    el.className = isIPad ? 'top' : 'bottom';
    el.setAttribute('role', 'dialog');
    var whereShare = isIPad ? 'sağ üstteki' : 'aşağıdaki';
    el.innerHTML =
      '<div class="h"><img class="ic" src="/icons/icon-192.png" alt=""/>' +
      '<div><div class="t">Ana ekrana ekle</div>' +
      '<div class="s">Uygulama gibi kullan, tek dokunuşla aç.</div></div>' +
      '<button class="x" aria-label="Kapat">&times;</button></div>' +
      '<div class="steps">' +
      '<div class="step"><span class="n">1</span><span>' + whereShare +
      ' <b>Paylaş</b> ' + SHARE_SVG + ' butonuna dokun</span></div>' +
      '<div class="step"><span class="n">2</span><span>Menüde <b>“Ana Ekrana Ekle”</b>yi seç</span></div>' +
      '<div class="step"><span class="n">3</span><span>Sağ üstte <b>Ekle</b>’ye dokun</span></div>' +
      '</div>';
    document.body.appendChild(el);
    el.querySelector('.x').onclick = close;
    // Safari paylaş butonuna işaret eden zıplayan ok
    var arrow = document.createElement('div');
    arrow.id = 'pwa-arrow';
    arrow.className = isIPad ? 'top' : 'down';
    var dir = isIPad ? 'M12 19V5 M6 11l6-6 6 6' : 'M12 5v14 M6 13l6 6 6-6';
    arrow.innerHTML = '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="' + dir + '"/></svg>';
    document.body.appendChild(arrow);
  }

  // --- In-app tarayıcı: Safari'de aç uyarısı ---
  function showOpenInSafari() {
    if (el || isStandalone()) return;
    injectStyles();
    mountOverlay();
    el = document.createElement('div'); el.id = 'pwa-card'; el.className = 'bottom';
    el.setAttribute('role', 'dialog');
    var howto = isIOS
      ? 'Sağ üstteki <b>•••</b> menüsünden <b>“Safari’de Aç”</b>ı seç, sonra tekrar dene.'
      : 'Sağ üstteki <b>⋮</b> menüsünden <b>“Tarayıcıda aç”</b>ı seç, sonra tekrar dene.';
    el.innerHTML =
      '<div class="h"><img class="ic" src="/icons/icon-192.png" alt=""/>' +
      '<div><div class="t">Önce tarayıcıda aç</div>' +
      '<div class="s">Uygulama içi tarayıcıda “ana ekrana ekleme” çalışmaz.</div></div>' +
      '<button class="x" aria-label="Kapat">&times;</button></div>' +
      '<div class="steps"><div class="step"><span class="n">!</span><span>' + howto + '</span></div></div>';
    document.body.appendChild(el);
    el.querySelector('.x').onclick = close;
  }

  function autoShow() {
    if (isStandalone() || dismissedRecently()) return;
    if (inApp) { setTimeout(showOpenInSafari, 1500); return; }
    if (isIOS) { setTimeout(showIOS, 1500); return; }
    // Android: beforeinstallprompt olayını bekle (aşağıda)
  }

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    if (!isStandalone() && !dismissedRecently()) setTimeout(showAndroid, 1200);
  });
  window.addEventListener('appinstalled', function () { remove(); });

  // Manuel tetik (Hesap sayfasındaki "Yükle" butonu) — her zaman açar
  window.PWAInstall = {
    show: function () {
      clearDismissed();
      remove();
      if (isStandalone()) return;
      if (inApp) showOpenInSafari();
      else if (deferredPrompt) showAndroid();
      else if (isIOS) showIOS();
      else showAndroid();
    },
    available: function () { return !isStandalone(); }
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', autoShow);
  else autoShow();
})();
