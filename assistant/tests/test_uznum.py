"""uznum.py — son → o'zbekcha so'z (ovoz uchun). FAZA C.

⚠️ Faqat ovoz (speech) matnida qo'llanadi; ui (ekran) raqamni saqlaydi.
"""

from django.test import TestCase

from ..uznum import numbers_to_words, uznum


class UznumTests(TestCase):
    def test_basic(self):
        cases = {
            0: 'nol', 1: 'bir', 5: 'besh', 10: "o'n", 15: "o'n besh",
            20: 'yigirma', 30: "o'ttiz", 35: "o'ttiz besh", 40: 'qirq',
            45: 'qirq besh', 99: "to'qson to'qqiz", 100: 'yuz',
            101: 'yuz bir', 200: 'ikki yuz', 250: 'ikki yuz ellik',
        }
        for n, word in cases.items():
            self.assertEqual(uznum(n), word, f'{n} → {word}')

    def test_thousands(self):
        self.assertEqual(uznum(1000), 'ming')
        self.assertEqual(uznum(5000), 'besh ming')
        self.assertEqual(uznum(30000), "o'ttiz ming")
        self.assertEqual(uznum(35000), "o'ttiz besh ming")
        self.assertEqual(uznum(45000), 'qirq besh ming')
        self.assertEqual(uznum(42000), 'qirq ikki ming')
        self.assertEqual(uznum(100000), 'yuz ming')

    def test_thousands_with_remainder(self):
        self.assertEqual(uznum(35500), "o'ttiz besh ming besh yuz")
        self.assertEqual(uznum(1200), 'ming ikki yuz')
        self.assertEqual(uznum(7000), 'yetti ming')

    def test_millions(self):
        self.assertEqual(uznum(1000000), 'bir million')
        self.assertEqual(uznum(2000000), 'ikki million')
        self.assertEqual(uznum(3010000), "uch million o'n ming")

    def test_negative(self):
        self.assertEqual(uznum(-5), 'minus besh')


class NumbersToWordsTests(TestCase):
    def test_spaced_number_in_sentence(self):
        self.assertEqual(numbers_to_words("45 000 so'm"), "qirq besh ming so'm")

    def test_unspaced_number(self):
        self.assertEqual(numbers_to_words("35000 so'm"), "o'ttiz besh ming so'm")

    def test_full_confirm_line(self):
        out = numbers_to_words("Jami 80 000 so'm")
        self.assertEqual(out, "Jami sakson ming so'm")

    def test_decimal_untouched(self):
        # O'nlik (8.5) tegilmaydi
        self.assertEqual(numbers_to_words("Masofa 8.5 km"), "Masofa 8.5 km")

    def test_time_untouched(self):
        self.assertEqual(numbers_to_words("soat 14:30 da"), "soat 14:30 da")

    def test_phone_like_long_number_untouched(self):
        # 7 xonadan katta — telefon/uzun raqam o'z holicha
        self.assertIn("998901234567", numbers_to_words("998901234567"))

    def test_no_number_unchanged(self):
        self.assertEqual(numbers_to_words("Salom, qandaysiz?"), "Salom, qandaysiz?")

    def test_two_numbers(self):
        out = numbers_to_words("30 000 va 45 000")
        self.assertEqual(out, "o'ttiz ming va qirq besh ming")


class TTSIntegrationTests(TestCase):
    """synthesize() ovoz oldidan sonlarni so'zga aylantiradi (ui'ga tegmaydi)."""

    def test_synthesize_converts_numbers_before_provider(self):
        from unittest import mock
        from .. import tts
        captured = {}

        def fake_provider(text, voice):
            captured['text'] = text
            return b'AUDIO'

        with mock.patch.dict('os.environ', {'TTS_PROVIDER': 'aisha', 'AISHA_API_KEY': 'k'}), \
             mock.patch.dict(tts._PROVIDERS, {'aisha': fake_provider}):
            from django.core.cache import cache
            cache.clear()
            tts.synthesize("Jami 35 000 so'm")
        self.assertIn("o'ttiz besh ming", captured.get('text', ''))
        self.assertNotIn('35', captured.get('text', ''))
