"""STT interfeys + /ai/stt/ endpoint — muloyim degradatsiya (204).

⚠️ Bu bo'lakda server STT o'chiq (Mohir kalit yo'q). Endpoint har doim 204
qaytaradi va widget brauzer Web Speech'ga qaytadi. Mohir ulangach FAQAT
stt.transcribe() o'zgaradi, bu testlar ham (mock bilan) kutilgan xatti-harakatni
ushlab turadi.
"""

from unittest import mock

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from .. import stt


class TranscribeInterfaceTests(TestCase):
    def test_returns_none_when_disabled(self):
        with mock.patch.dict('os.environ', {'STT_PROVIDER': '', 'STT_API_KEY': ''}):
            self.assertIsNone(stt.transcribe(b'audio', lang='uz'))
            self.assertFalse(stt.is_enabled())

    def test_returns_none_for_empty_audio(self):
        self.assertIsNone(stt.transcribe(b'', lang='uz'))

    def test_enabled_needs_provider_and_key(self):
        with mock.patch.dict('os.environ', {'STT_PROVIDER': 'mohir', 'STT_API_KEY': ''}):
            self.assertFalse(stt.is_enabled())
        with mock.patch.dict('os.environ', {'STT_PROVIDER': 'mohir', 'STT_API_KEY': 'k'}):
            self.assertTrue(stt.is_enabled())

    def test_unknown_provider_still_none(self):
        with mock.patch.dict('os.environ', {'STT_PROVIDER': 'foo', 'STT_API_KEY': 'k'}):
            self.assertIsNone(stt.transcribe(b'audio', lang='uz'))


class WebSTTEndpointTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_unconfigured_returns_204(self):
        c = Client()
        resp = c.post(reverse('assistant:stt'), data=b'\x00\x01',
                      content_type='audio/webm')
        self.assertEqual(resp.status_code, 204)

    def test_multipart_audio_also_204(self):
        c = Client()
        from django.core.files.uploadedfile import SimpleUploadedFile
        audio = SimpleUploadedFile('a.webm', b'\x00\x01', content_type='audio/webm')
        resp = c.post(reverse('assistant:stt'), data={'audio': audio})
        self.assertEqual(resp.status_code, 204)

    def test_returns_text_when_server_stt_available(self):
        """Mohir ulangач (mock) — endpoint matn qaytaradi, widget o'zgarmaydi."""
        c = Client()
        with mock.patch('assistant.stt.transcribe', return_value='eng yaqin dorixona'):
            resp = c.post(reverse('assistant:stt'), data=b'\x00\x01',
                          content_type='audio/webm')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['text'], 'eng yaqin dorixona')

    def test_get_not_allowed(self):
        self.assertEqual(Client().get(reverse('assistant:stt')).status_code, 405)


class ApiSTTEndpointTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_api_unconfigured_returns_204(self):
        c = Client()
        resp = c.post(reverse('api:assistant-stt'), data=b'\x00\x01',
                      content_type='audio/webm')
        self.assertEqual(resp.status_code, 204)

    def test_api_returns_text_when_available(self):
        c = Client()
        with mock.patch('assistant.stt.transcribe', return_value='salom'):
            resp = c.post(reverse('api:assistant-stt'), data=b'\x00\x01',
                          content_type='audio/webm')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['text'], 'salom')
