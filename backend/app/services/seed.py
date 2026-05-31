"""Başlangıç verileri (sectors + TEST123 demo işletmesi). Idempotent."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.sector import Sector
from app.models.staff_user import StaffUser
from app.models.station import Station
from app.models.tenant import Tenant
from app.security.passwords import hash_password

logger = logging.getLogger(__name__)


SECTORS_SEED = [
    {
        "id": "barber",
        "label": "Berber",
        "icon": "content-cut",
        "default_services": {"items": ["Saç Kesimi", "Sakal Tıraşı", "Bakım Paketi"]},
    },
    {
        "id": "dentist",
        "label": "Diş Hekimi",
        "icon": "tooth-outline",
        "default_services": {"items": ["Muayene", "Diş Temizliği", "Kontrol"]},
    },
    {
        "id": "psychologist",
        "label": "Psikolog",
        "icon": "head-heart-outline",
        "default_services": {"items": ["Bireysel Görüşme", "Online Seans", "Ön Değerlendirme"]},
    },
    {
        "id": "physiotherapist",
        "label": "Fizyoterapist",
        "icon": "human-handsup",
        "default_services": {"items": ["Fizik Tedavi", "Manuel Terapi", "Egzersiz Planı"]},
    },
    {
        "id": "nutritionist",
        "label": "Beslenme Danışmanı",
        "icon": "food-apple-outline",
        "default_services": {"items": ["Beslenme Analizi", "Diyet Planı", "Takip Görüşmesi"]},
    },
    # Ölçeklenebilirlik örnekleri (admin sonradan ekleyebilir)
    # {"id": "auto", "label": "Oto Servis", "icon": "car-wrench", "default_services": {"items": ["Bakım", "Lastik", "Yağ Değişimi"]}},
    # {"id": "clinic", "label": "Klinik", "icon": "hospital-building", "default_services": {"items": ["Muayene", "Tahlil"]}},
]


async def _seed_sectors(db: AsyncSession) -> None:
    existing = {s for s in (await db.scalars(select(Sector.id))).all()}
    for spec in SECTORS_SEED:
        if spec["id"] in existing:
            continue
        db.add(Sector(**spec))
    await db.flush()


async def _seed_demo_tenant(db: AsyncSession) -> None:
    existing = await db.scalar(select(Tenant).where(Tenant.invite_code == "TEST123"))
    if existing:
        return

    business_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    tenant = Tenant(
        id=business_id,
        owner_id=owner_id,
        name="Test Berber",
        sector_id="barber",
        address="Test Mahallesi, Demo Sokak No:1",
        location="İstanbul",
        invite_code="TEST123",
        verification_status="test",
        verification_note="İlk kurulum test işletmesi.",
        kvkk_text=DEFAULT_KVKK_TEXT,
    )
    db.add(tenant)
    # FK dependent insert'lerden önce tenant'ı DB'ye yaz
    await db.flush()

    # Önce istasyonlar (staff.station_id FK'sı tatmin olsun diye)
    s1 = Station(id=uuid.uuid4(), business_id=business_id, label="Koltuk 1", position=0)
    s2 = Station(id=uuid.uuid4(), business_id=business_id, label="Koltuk 2", position=1)
    db.add_all([s1, s2])
    await db.flush()

    owner = StaffUser(
        id=owner_id,
        business_id=business_id,
        role="owner",
        name="Test Patron",
        first_name="Test",
        last_name="Patron",
        gmail="testpatron@gmail.com",
        title="İşletme Sahibi",
        station_label="Yönetim",
        password_hash=hash_password("1234"),
    )
    db.add(owner)

    # Bir test usta — her iki koltuğa da atanmış
    staff = StaffUser(
        id=uuid.uuid4(),
        business_id=business_id,
        role="staff",
        name="Test Usta",
        first_name="Test",
        last_name="Usta",
        gmail="testusta@gmail.com",
        title="Usta",
        station_id=s1.id,
        station_label="Koltuk 1",
        station_ids=[str(s1.id), str(s2.id)],
        password_hash=hash_password("1234"),
    )
    db.add(staff)

    # Demo hizmetler (manuel randevu formu test edilebilsin)
    from app.models.service import Service
    for name in ["Saç Kesimi", "Sakal Tıraşı", "Saç + Sakal"]:
        db.add(Service(id=uuid.uuid4(), business_id=business_id, name=name, duration_minutes=30))

    await db.flush()
    logger.info("Demo işletme TEST123 oluşturuldu (patron: testpatron@gmail.com / 1234)")


DEFAULT_KVKK_TEXT = """KİŞİSEL VERİLERİN KORUNMASI AYDINLATMA METNİ

İşbu metin, 6698 sayılı Kişisel Verilerin Korunması Kanunu ("KVKK") kapsamında, randevu hizmetinden yararlanan kullanıcıların kişisel verilerinin işlenmesine ilişkin olarak veri sorumlusu sıfatıyla sizi bilgilendirmek amacıyla hazırlanmıştır.

1) VERİ SORUMLUSU
Randevu hizmetini sunan işletme (berber, klinik, danışmanlık vb.) veri sorumlusudur. Turuncu Randevu, işletmeye bu hizmeti sağlayan teknik altyapı sağlayıcısı (veri işleyen) konumundadır.

2) İŞLENEN KİŞİSEL VERİLER
- Kimlik: ad, soyad
- İletişim: telefon numarası, e-posta (Gmail) adresi
- İşlem: aldığınız randevu tarih/saat bilgileri, seçtiğiniz hizmet ve işletme
- İşlem güvenliği: oturum ve giriş kayıtları

3) İŞLEME AMAÇLARI
Kişisel verileriniz; randevu oluşturma ve yönetimi, randevu onayı ile hatırlatma SMS'lerinin gönderilmesi, hizmetin sunulması, kimlik doğrulama (SMS OTP) ve sistem güvenliğinin sağlanması amaçlarıyla işlenir.

4) HUKUKİ SEBEP
Verileriniz; bir sözleşmenin kurulması veya ifası için işlenmesinin gerekli olması (KVKK m.5/2-c), veri sorumlusunun meşru menfaati (m.5/2-f) ve gerektiğinde açık rızanız (m.5/1) hukuki sebeplerine dayanılarak işlenir.

5) TOPLAMA YÖNTEMİ
Veriler; uygulama üzerindeki kayıt ve randevu formları aracılığıyla elektronik ortamda toplanır.

6) AKTARIM
Telefon numaranız, yalnızca randevu onayı ve hatırlatma mesajlarının iletilmesi amacıyla yetkili SMS hizmet sağlayıcısına aktarılır. Verileriniz, yasal yükümlülükler dışında üçüncü kişilerle paylaşılmaz ve yurt dışına aktarılmaz.

7) VERİ GÜVENLİĞİ
Telefon numaralarınız veritabanında açık metin olarak tutulmaz; AES-256 (GCM) algoritmasıyla şifrelenerek saklanır ve panellerde maskelenmiş biçimde (örn. 0532 *** 12 34) gösterilir. Şifreleriniz geri döndürülemez biçimde (PBKDF2-SHA256) saklanır.

8) SAKLAMA SÜRESİ
Verileriniz, işleme amacının gerektirdiği süre ve ilgili mevzuattaki zamanaşımı süreleri boyunca saklanır; sürenin sonunda veya talebiniz üzerine silinir, yok edilir veya anonim hâle getirilir.

9) HAKLARINIZ (KVKK m.11)
Kişisel verilerinizin işlenip işlenmediğini öğrenme, işlenmişse buna ilişkin bilgi talep etme, işleme amacını öğrenme, eksik/yanlış işlenmişse düzeltilmesini, şartları oluştuğunda silinmesini veya yok edilmesini isteme, işlemlerin aktarıldığı üçüncü kişilere bildirilmesini isteme, otomatik sistemlerle analiz sonucu aleyhinize bir sonuç çıkmasına itiraz etme ve zarara uğramanız hâlinde tazminat talep etme haklarına sahipsiniz.

10) BAŞVURU
Haklarınıza ilişkin taleplerinizi, hizmet aldığınız işletmeye yazılı olarak iletebilirsiniz. Talebiniz en geç 30 gün içinde sonuçlandırılır.

Bu metin genel bir bilgilendirme şablonudur. İşletmenizin gerçek unvanı, adresi ve iletişim bilgileriyle güncellenmeli ve yürürlüğe almadan önce bir hukuk danışmanına gözden geçirtilmelidir."""


async def run_seed() -> None:
    """Uygulama başlatıldığında idempotent şekilde başlangıç verilerini ekler."""
    async with AsyncSessionLocal() as db:
        try:
            await _seed_sectors(db)
            await _seed_demo_tenant(db)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
