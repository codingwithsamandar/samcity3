"""Media (fayl) saqlash backendini uchidan-uchiga tekshiradigan diagnostika.

Nima uchun kerak: Render'da yuklangan rasmlar saqlanmasa — sabab deyarli har doim
storage sozlamasida bo'ladi (Supabase/S3 kaliti kiritilmagan, ACL bloklangan,
region noto'g'ri yoki bucket topilmadi). Bu buyruq real "yoz -> URL -> o'qi ->
public GET -> o'chir" tsiklini bajaradi va MUAMMONI ANIQ ko'rsatadi.

entrypoint.sh uni har deploy'da chaqiradi — natija Render loglarida chiqadi
(bepul tarifda interaktiv Shell yo'q). Qo'lda ham ishga tushirish mumkin:

    python manage.py check_media

Chiqish faqat ASCII — har qanday konsol kodlashida (Windows cp1251 ham) yiqilmaydi.
"""
from __future__ import annotations

import traceback

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand


def _mask(value: str) -> str:
    """Maxfiy kalitni loglarda ochiq ko'rsatmaslik uchun niqoblaydi."""
    if not value:
        return "(BO'SH)"
    if len(value) <= 6:
        return '*' * len(value)
    return f'{value[:3]}...{value[-3:]}'


class Command(BaseCommand):
    help = "Media storage backendini uchidan-uchiga tekshiradi (yoz/o'qi/o'chir)."

    def handle(self, *args, **options):
        w = self.stdout.write
        line = '-' * 64
        w(line)
        w('MEDIA STORAGE TEKSHIRUVI')
        w(line)

        backend = default_storage.__class__
        name = backend.__name__
        w(f'Backend      : {backend.__module__}.{name}')
        w(f'MEDIA_URL    : {settings.MEDIA_URL}')

        if 'S3' in name:
            w(f'Bucket       : {getattr(settings, "AWS_STORAGE_BUCKET_NAME", "?")}')
            w(f'Region       : {getattr(settings, "AWS_S3_REGION_NAME", "?")}')
            w(f'Endpoint     : {getattr(settings, "AWS_S3_ENDPOINT_URL", "?")}')
            w(f'Addressing   : {getattr(settings, "AWS_S3_ADDRESSING_STYLE", "?")}')
            w(f'Default ACL  : {getattr(settings, "AWS_DEFAULT_ACL", "?")!r}')
            w(f'Access key   : {_mask(getattr(settings, "AWS_ACCESS_KEY_ID", ""))}')
            w(f'Secret key   : {_mask(getattr(settings, "AWS_SECRET_ACCESS_KEY", ""))}')
        elif 'Cloudinary' in name:
            _cs = getattr(settings, 'CLOUDINARY_STORAGE', {})
            w(f'Cloud name   : {_cs.get("CLOUD_NAME", "?")}')
        else:
            w(self.style.WARNING(
                "DIQQAT: Local FileSystemStorage faol. Render disk EFEMER - "
                "yuklangan fayllar keyingi deploy/restart'da YO'QOLADI. "
                "Supabase/S3 yoki Cloudinary env'larini o'rnating."))

        w(line)
        test_name = 'healthcheck/media_check.txt'
        payload = b'samcity-media-ok'
        saved_name = None
        try:
            w('1) Yozish (save)...')
            saved_name = default_storage.save(test_name, ContentFile(payload))
            w(f'   [OK] saqlandi: {saved_name}')

            w('2) URL...')
            url = default_storage.url(saved_name)
            w(f'   [OK] {url}')

            w('3) Mavjudlik (exists)...')
            w(f'   [OK] exists={default_storage.exists(saved_name)}')

            w("4) Qayta o'qish (open/read)...")
            with default_storage.open(saved_name) as fh:
                got = fh.read()
            match = got == payload
            w(f'   [{"OK" if match else "XATO"}] {len(got)} bayt o\'qildi, mos={match}')

            # 5) Public HTTP kirish — bucket "public" ekanini va MEDIA_URL to'g'ri
            #    ekanini tasdiqlaydi (rasm brauzerda ko'rinishi uchun eng muhim).
            try:
                import requests
                w('5) Public HTTP GET...')
                resp = requests.get(url, timeout=10)
                w(f'   HTTP {resp.status_code} ({len(resp.content)} bayt)')
                if resp.status_code == 200 and resp.content == payload:
                    w("   [OK] fayl public URL orqali o'qildi")
                else:
                    w(self.style.WARNING(
                        "   [XATO] public URL faylni qaytarmadi — bucket "
                        "\"public\" emasligi yoki MEDIA_URL noto'g'ri bo'lishi mumkin"))
            except Exception as exc:  # noqa: BLE001
                w(f"   (HTTP tekshiruvi o'tkazib yuborildi: {exc})")

            self.stdout.write(self.style.SUCCESS(
                "\n[NATIJA] MEDIA STORAGE ISHLAYAPTI - yozish/o'qish muvaffaqiyatli."))
        except Exception:  # noqa: BLE001
            self.stdout.write(self.style.ERROR(
                '\n[NATIJA] MEDIA STORAGE XATOSI — upload bajarilmadi:'))
            self.stdout.write(traceback.format_exc())
            self.stdout.write(self.style.WARNING(
                "Tez-tez uchraydigan sabablar:\n"
                "  * AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY Render'da kiritilmagan yoki noto'g'ri\n"
                "  * AWS_S3_REGION_NAME Supabase loyiha regioniga mos emas (SignatureDoesNotMatch)\n"
                "  * AWS_STORAGE_BUCKET_NAME noto'g'ri yoki bucket mavjud emas\n"
                "  * AWS_DEFAULT_ACL='public-read' (Supabase ACL'ni qo'llamaydi — None bo'lishi kerak)"))
        finally:
            if saved_name:
                try:
                    default_storage.delete(saved_name)
                    w(f"\n(test fayl o'chirildi: {saved_name})")
                except Exception as exc:  # noqa: BLE001
                    w(f"\n(test faylni o'chirib bo'lmadi: {exc})")
