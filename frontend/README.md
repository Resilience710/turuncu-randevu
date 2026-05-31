# Turuncu Randevu — Frontend

HTML5 + Tailwind CSS (CDN) + Vanilla JS PWA. Build adımı **gerekmez**, statik dosyalar olduğu gibi servis edilir.

## Yapı

```
frontend/public/
├── index.html                  # Rol seçimi (landing)
├── manifest.webmanifest        # Ana PWA
├── manifest-kiosk.webmanifest  # Kiosk (display:fullscreen)
├── sw.js                       # Service worker (network-first + offline)
├── offline.html
├── icons/                      # SVG ikonlar
├── css/
│   └── tokens.css              # Renk/spacing/komponent CSS vars
├── js/
│   └── shared/
│       ├── api.js              # fetch wrapper + token storage + 401 redirect
│       ├── auth.js             # role guard
│       ├── toast.js, kvkk-modal.js, components.js, owner-nav.js
├── customer/
│   ├── register.html  login.html
│   ├── businesses.html  business-detail.html
│   ├── my-appointments.html  account.html
├── owner/
│   ├── login.html  register.html
│   ├── dashboard.html          # randevular listesi (8sn polling)
│   ├── occupancy.html          # istasyon kartları (5sn polling)
│   ├── business-settings.html  # işletme + hizmetler + istasyonlar
│   ├── employees.html          # personel ekle/sil
│   ├── appointments-manual.html
│   └── account.html
└── staff/
    ├── login.html
    └── kiosk.html              # Fullscreen + wake-lock + start/finish + PIN exit
```

## Lokal çalıştırma

```powershell
cd frontend\public
python -m http.server 5173
# → http://localhost:5173
```

Backend `http://localhost:8000`'de koşuyor olmalı; `js/shared/api.js` varsayılan olarak `/api` kullanır.
Render'da statik site + rewrite kuralıyla `/api/*` backend'e yönlenir (bkz: kök `render.yaml`).

## Üretim API base override

Render statik site'te `index.html` veya başka bir entry'e `<script>` ile `window.__API_BASE` set'lenebilir:

```html
<script>window.__API_BASE = "https://turuncu-api.onrender.com/api";</script>
```

veya rewrite kuralı yeterli (önerilen).

## Test hesabı

Seed'den gelir:

- **Müşteri:** `/customer/register.html` üzerinden taze hesap aç
- **Patron:** `/owner/login.html` → `testpatron@gmail.com` / `1234`
- **Personel:** `/staff/login.html` → davet kodu `TEST123` / şifre `1234`

## Kiosk modu

`/staff/kiosk.html`'i tablete (7"+) **PWA olarak install** et:

1. Chrome/Edge → menü → "Ana ekrana ekle"
2. Yüklü PWA açıldığında `manifest-kiosk.webmanifest` devreye girer (`display:fullscreen`)
3. İlk dokunuşta `requestFullscreen()` + `wakeLock.request('screen')` tetiklenir
4. Çıkış: sağ üst → 4 haneli PIN (şu an basit kontrol; üretim için backend endpoint'i eklenebilir)
5. Android için: Kiosk Browser app ile PWA pin'le; iOS için: Guided Access (Settings → Accessibility)

## Çerçeve seçimleri

- **Tailwind CDN** — MVP hızı için. Üretim performansı için `tailwindcss` CLI ile compile etmek istersen `frontend/`'e `package.json` ekleyip `npx tailwindcss -i input.css -o public/css/tailwind.css` build adımı kurarsın; CDN script tag'ini kaldırırsın.
- **MPA** (her major flow için ayrı HTML) — service worker shell cache'i basit, kiosk tek URL'e kilitlenebilir, SEO-friendly.
- **Vanilla JS** — framework yok, runtime indirme ~0 KB.
