# Turuncu Randevu

Multi-tenant, KVKK uyumlu, sektör-bağımsız (berber, klinik, oto servis vb.) randevu sistemi.

- **Backend:** FastAPI + SQLAlchemy 2 (async) + Supabase Postgres + Alembic
- **Frontend:** HTML5 + Tailwind CSS + Vanilla JS PWA (build adımı gerekmez)
- **Deploy:** Render.com (Docker web service + statik site) + Supabase DB
- **SMS:** Netgsm (OTP, randevu onayı, 15 dk hatırlatma)

## Repo yapısı

```
.
├── backend/        # FastAPI uygulaması (bkz: backend/README.md)
├── frontend/       # Statik PWA (bkz: frontend/README.md)
├── scripts/
│   └── smoke.sh    # Deploy sonrası smoke test
├── legacy/         # Eski MVP (MongoDB + Expo React Native) — referans için saklandı
├── memory/         # Geliştirme notları
├── design_guidelines.json
├── render.yaml     # Render blueprint
└── README.md
```

## Hızlı başlangıç (lokal)

### 1) Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env
# .env'i düzenle: DATABASE_URL (Supabase pooler URI), PHONE_ENCRYPTION_KEY, vs.

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

→ <http://localhost:8000/docs>

### 2) Frontend

```powershell
cd frontend\public
python -m http.server 5173
```

→ <http://localhost:5173>

### 3) Test hesapları (seed'den gelir)

| Rol | URL | Bilgi |
|---|---|---|
| Müşteri | /customer/register.html | yeni hesap aç |
| Patron | /owner/login.html | `testpatron@gmail.com` / `1234` |
| Personel | /staff/login.html | davet kodu `TEST123` + şifre `1234` |
| Kiosk | /staff/kiosk.html | (personel girişi sonrası) |

## Üretim deploy (Render.com)

1. Supabase'de proje aç → Connection string'i kopyala (port **6543**, pooler)
2. Render dashboard → New → Blueprint → bu repo'yu seç (`render.yaml`'ı otomatik bulur)
3. `turuncu-api` env vars'larını set'le:
   - `DATABASE_URL` — Supabase pooler URI (`postgresql+asyncpg://...?ssl=require`)
   - `PHONE_ENCRYPTION_KEY` — `python -c "import os,base64;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"`
   - `PHONE_HASH_PEPPER`, `OTP_SECRET` — uzun rastgele stringler
   - `NETGSM_USERCODE`, `NETGSM_PASSWORD`, `NETGSM_MSGHEADER` — opsiyonel (eksikse OTP dev fallback'e düşer)
4. Apply → ilk deploy'da Alembic `upgrade head` otomatik koşar, seed çalışır
5. `API_BASE=https://turuncu-api.onrender.com ./scripts/smoke.sh` ile smoke test

## Güvenlik

- **AES-256-GCM** telefon şifreleme — DB'de açık metin telefon yok
- **PBKDF2-SHA256** (120k iter) şifre hash
- **Postgres Row Level Security** — `staff_users`, `services`, `stations`, `appointments`, `appointment_events`, `sms_reminders` üzerinde tenant isolation
- **Partial unique index** — slot çakışması DB seviyesinde imkânsız (`uq_appt_active_slot`)
- **OTP**: peppered SHA-256 hash + 5 dk TTL (pg_cron temizliği için index hazır)
- **Sessions**: opaque token (URL-safe 32 byte)
- KVKK aydınlatma metni `/api/kvkk-text` endpoint'inden gelir, müşteri kayıtta onaylar

## Faz durumu

- ✅ Faz 1: Şema + Auth
- ✅ Faz 2: İşletmeler + çalışanlar + RLS
- ✅ Faz 3: İstasyonlar + occupancy
- ✅ Faz 4: Randevu CRUD + slot çakışma
- ✅ Faz 5: Status geçişleri + appointment_events
- ✅ Faz 6: SMS reminder worker
- ✅ Faz 7: Frontend müşteri akışı
- ✅ Faz 8: Patron dashboard + occupancy
- ✅ Faz 9: Kiosk modu
- ✅ Faz 10: Render deploy konfigürasyonu

Sıradaki adım: Supabase'e bağlanıp end-to-end smoke test.
