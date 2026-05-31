# Turuncu Randevu PRD

## Problem Statement
Berber, diş hekimi, psikolog, fizyoterapist ve beslenme danışmanları için mobil randevu sistemi. Müşteriler işletme/çalışan/saat seçerek randevu alabilmeli; işletme sahipleri yönetim panelinden çalışan, hizmet, konum ve manuel telefon randevusu yönetebilmeli; çalışanlar davet koduyla işletmeye katılabilmeli; randevular JSON API ile dışarı aktarılabilmeli. Tasarım turuncu-beyaz olmalı ve kullanıcı/işletme arayüzleri ayrılmalı.

## Architecture
- Frontend: Expo React Native, Expo Router, React Native components, turuncu-beyaz mobil UI.
- Backend: FastAPI, `/api` prefix, MongoDB via Motor.
- Database: MongoDB collections: `users`, `businesses`, `appointments`, `sessions`.
- PWA: `frontend/public/manifest.webmanifest`, `sw.js`, `offline.html`, SVG icons; `app/+html.tsx` manifest and service worker registration.

## User Personas
- Customer: Telefon/e-posta ile kayıt olur, işletme arar, konum/sektör filtreler, randevu alır/iptal eder.
- Business Owner: İşletme oluşturur, davet kodu üretir, çalışan/hizmet/adres yönetir, manuel randevu ekler, randevuları liste/grid görür.
- Staff: Davet koduyla katılır, işletme randevularını görür ve yönetir.

## Core Requirements
- Role-based auth: customer, owner, staff.
- Business marketplace with search, sector filters and location selector.
- Business detail page with address, services, staff and 30-minute slots.
- Taken appointment slots shown red and double booking prevented server-side.
- Owner dashboard with manual appointment creation and list/grid view toggles.
- Employee add/remove and invite code flow.
- Appointment cancellation.
- JSON appointment export endpoint.
- PWA add-to-home-screen assets.

## Implemented
- 2026-05-21: FastAPI booking backend implemented with auth, businesses, employees, availability, appointments, cancellation and export endpoints.
- 2026-05-21: Expo mobile UI implemented for auth, customer discovery/detail/appointments/account and owner/staff dashboard/business/account flows.
- 2026-05-21: PWA manifest, service worker, offline page and SVG icons added; web HTML links/registers PWA assets.
- 2026-05-21: Project consolidated into `/app/turuncu-randevu-tek-klasor` with backend, frontend and PWA files.
- 2026-05-21: Customer/staff separation rebuilt: customer auth without invite code, KVKK + OTP registration, AES-256 encrypted phone storage, tenants collection, staff invite-code login, Netgsm env-ready SMS functions, masked phone display.
- 2026-05-21: Secured `/api/appointments/export` with auth and business scoping after testing agent reported public access risk.

## Testing Notes
- Python lint passed for backend.
- JavaScript lint passed for `frontend/app/index.tsx` and `frontend/app/+html.tsx`.
- Backend health endpoint verified: `GET /api/` returns API ready message.
- PWA manifest verified through preview URL.
- Expo preview loaded successfully and showed the Turuncu Randevu login screen.
- Testing agent validated customer auth split, KVKK UI, OTP fallback, owner/staff modes, business browse/detail, booking conflict prevention and PWA manifest.
- Self-test verified unauthenticated appointment export now returns 401 and authenticated owner export returns scoped data.

## Prioritized Backlog
### P0
- Add formal validation for appointment date format and business hours.
- Add pagination/filtering for large appointment lists.
- Set production `PHONE_ENCRYPTION_KEY` and Netgsm credentials in backend environment.

### P1
- Replace staff invite code placeholder flow with real QR generation/scanning.
- Replace Netgsm config-missing development fallback with live SMS once credentials are available.
- Add owner business verification document upload/review flow.

### P2
- Add ratings/reviews and business gallery.
- Add calendar sync and push reminders.
- Optimize `/api/businesses` employee count using aggregation for high scale.

## Next Tasks
- Create seed/test users only if requested.
- Add full end-to-end browser tests for owner/customer booking conflict scenarios.
- Improve PWA icon set with PNG sizes for broader iOS compatibility.
