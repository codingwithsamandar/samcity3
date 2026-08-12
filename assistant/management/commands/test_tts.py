"""TTS (ovozli javob) ulanishini tekshirish.

Ishlatish:
    python manage.py test_tts
    python manage.py test_tts "Menga eng yaqin dorixonani ko'rsat"

Nima qiladi:
  1) Joriy sozlamani ko'rsatadi (provayder, kalit bor-yo'qligi — maskalangan).
  2) Provayder endpointiga bevosita so'rov yuborib, HTTP holati va javobni chiqaradi.
  3) tts.synthesize() ni chaqiradi; audio kelsa faylga saqlaydi.
"""

import os

from django.core.management.base import BaseCommand

from assistant import tts as tts_mod


class Command(BaseCommand):
    help = "AI yordamchi ovozi (TTS) ulanishini tekshiradi."

    def add_arguments(self, parser):
        parser.add_argument('text', nargs='?',
                            default="Assalomu alaykum. Bu ovoz sinovi.")

    def handle(self, *args, **opts):
        text = opts['text']
        prov = tts_mod.provider()
        self.stdout.write('─' * 60)
        self.stdout.write(f"Provayder : {prov or '(bosh — ochiq emas)'}")

        if prov == 'aisha':
            key = os.environ.get('AISHA_API_KEY', '').strip()
        elif prov == 'azure':
            key = os.environ.get('AZURE_TTS_KEY', '').strip()
        else:
            key = ''
        self.stdout.write(f"Kalit     : {(key[:6] + '…' + key[-4:]) if key else 'YO`Q'}")
        self.stdout.write(f"Matn      : {text}")
        self.stdout.write('─' * 60)

        if prov == 'aisha' and key:
            self._probe_aisha(key, text)

        self.stdout.write('─' * 60)
        audio = tts_mod.synthesize(text)
        if audio:
            ext = 'wav' if tts_mod.content_type() == 'audio/wav' else 'mp3'
            fname = f'tts_test.{ext}'
            try:
                with open(fname, 'wb') as f:
                    f.write(audio)
                self.stdout.write(self.style.SUCCESS(
                    f'✅ Audio olindi: {len(audio)} bayt → {fname} (ochib eshiting)'))
            except OSError as e:
                self.stdout.write(self.style.WARNING(f'Audio olindi, saqlanmadi: {e}'))
        else:
            self.stdout.write(self.style.WARNING(
                "⚠️  Audio olinmadi. Yuqoridagi diagnostikani yuboring."))

    def _probe_aisha(self, key, text):
        """Aisha TTS endpointini bevosita sinaydi (multipart/form-data)."""
        try:
            import requests
        except ImportError:
            self.stdout.write(self.style.ERROR("`requests` o'rnatilmagan"))
            return
        url = os.environ.get('AISHA_TTS_URL', f'{tts_mod.AISHA_BASE}/api/v1/tts/post/').strip()
        fields = {
            'transcript': (None, text[:tts_mod.AISHA_MAX_CHARS]),
            'language': (None, 'uz'),
            'model': (None, os.environ.get('AISHA_TTS_MODEL', 'Gulnoza')),
            'mood': (None, os.environ.get('AISHA_TTS_MOOD', 'Neutral')),
            'speed': (None, os.environ.get('AISHA_TTS_SPEED', '1.0')),
        }
        self.stdout.write(f'URL       : {url}')
        try:
            r = requests.post(url, headers={'X-Api-Key': key}, files=fields, timeout=30)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ulanish xatosi: {e}'))
            return
        self.stdout.write(f'HTTP      : {r.status_code}')
        body = (r.text or '')[:600]
        self.stdout.write(f'Javob     : {body}')
        if r.status_code in (200, 201):
            try:
                path = r.json().get('audio_path')
                if path:
                    self.stdout.write(self.style.SUCCESS(
                        f'→ audio_path: {path}  (to`liq: {tts_mod.AISHA_BASE}{path})'))
            except Exception:
                pass
        elif r.status_code == 402:
            self.stdout.write(self.style.WARNING('→ Balans yetarli emas (402).'))
        elif r.status_code in (401, 403):
            self.stdout.write(self.style.WARNING('→ Kalit noto`g`ri yoki ruxsat yo`q.'))
