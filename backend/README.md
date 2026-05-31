# Turuncu Randevu — Backend

FastAPI + SQLAlchemy 2 (async) + Supabase Postgres ile yazılmış multi-tenant randevu API'ı.

## Gereksinimler

- Python 3.11+
- Bir Postgres veritabanı (Supabase önerilir, lokal Postgres da çalışır)

## Hızlı başlangıç

```powershell
cd backend

# 1) Sanal ortam
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2) Bağımlılıklar
pip install -e .

# 3) Çevre değişkenleri
copy .env.example .env
# .env dosyasını düzenle (DATABASE_URL, PHONE_ENCRYPTION_KEY, vb.)

# 4) Migration'ları koş
alembic upgrade head

# 5) Sunucu
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Açılınca:
- API root: <http://localhost:8000/api/>
- Swagger: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

## Klasör yapısı

```
backend/
├── app/
│   ├── api/              # FastAPI route'ları (auth, sectors, me)
│   ├── db/               # Async engine, Base, Alembic migrations
│   ├── models/           # SQLAlchemy ORM modelleri (12 tablo)
│   ├── schemas/          # Pydantic v2 request/response
│   ├── security/         # Şifre, telefon (AES-256), OTP, token
│   ├── services/         # Seed, slots
│   ├── sms/              # Netgsm entegrasyonu, reminder worker (Faz 6)
│   ├── config.py         # pydantic-settings ile env yönetimi
│   ├── deps.py           # FastAPI dependency'leri (auth, RLS context)
│   └── main.py           # Uygulama girişi
├── alembic.ini
├── pyproject.toml
└── .env.example
```

## Test kullanıcısı

Seed otomatik bir demo işletmesi oluşturur:

- **Davet kodu:** `TEST123`
- **Patron:** `testpatron@gmail.com` / şifre `1234`
- **Personel:** `TEST123` + şifre `1234`

## Güvenlik

- **AES-256-GCM** ile telefon numarası şifreleme (`app/security/phones.py`)
- **PBKDF2-SHA256** (120k iter) ile şifre hash'leme (`app/security/passwords.py`)
- **Hash'li OTP** doğrulama (`app/security/otp.py`)
- **Multi-tenant izolasyon**: PostgreSQL Row Level Security (Faz 2'de açılır)
- KVKK uyumu için telefon panelde maskelenerek gösterilir (örn: `0532 *** 12 34`)

## Faz durumu

- ✅ **Faz 1:** Şema + Auth (request-otp/verify/login, owner register/login, staff join/login, /me, /sectors, /kvkk-text)
- ⏳ Faz 2: İşletmeler + çalışanlar + RLS politikaları
- ⏳ Faz 3: İstasyonlar + occupancy
- ⏳ Faz 4: Randevu çekirdek
- ⏳ Faz 5: Start/finish + appointment_events
- ⏳ Faz 6: SMS reminder worker
- ⏳ Faz 7-9: Frontend (HTML/Tailwind/Vanilla JS PWA)
- ⏳ Faz 10: Render deploy
