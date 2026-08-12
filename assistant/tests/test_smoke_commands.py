"""seed_smoke va smoke_agent buyruqlari — test bazasida tekshiriladi.

Haqiqiy LLM chaqirilmaydi (kalit yo'q). Bu yerda faqat buyruqlar to'g'ri
ishlashi, idempotentligi va kalitsiz muloyim to'xtashi tekshiriladi.
"""

from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class SeedSmokeTests(TestCase):
    def test_seed_creates_data(self):
        call_command('seed_smoke', quiet=True)
        from delivery.models import Product, Store
        from main.models import District, Neighborhood
        from places.models import Place
        from assistant.management.commands.seed_smoke import SMOKE_PHONE

        self.assertEqual(District.objects.filter(name='Shofirkon tumani').count(), 1)
        self.assertEqual(Neighborhood.objects.count(), 2)
        self.assertEqual(Store.objects.count(), 3)
        self.assertTrue(Product.objects.count() >= 14)
        self.assertEqual(Place.objects.count(), 2)

        user = get_user_model().objects.get(phone=SMOKE_PHONE)
        # Tuman aniqlanishi SHART — guard tuman filtri shunga tayanadi
        self.assertIsNotNone(user.neighborhood)
        self.assertIsNotNone(user.neighborhood.district)

    def test_seed_is_idempotent(self):
        call_command('seed_smoke', quiet=True)
        from delivery.models import Product, Store
        first = (Store.objects.count(), Product.objects.count())
        call_command('seed_smoke', quiet=True)   # ikkinchi marta
        second = (Store.objects.count(), Product.objects.count())
        self.assertEqual(first, second)

    def test_injection_trap_exists_in_product_name(self):
        """Injection tuzog'i NOMDA bo'lishi shart — LLM ga faqat nom yetadi."""
        call_command('seed_smoke', quiet=True)
        from delivery.models import Product
        trap = Product.objects.filter(name__contains='SYSTEM').first()
        self.assertIsNotNone(trap)
        self.assertIn('bepul', trap.name.lower())

    def test_seeded_store_is_orderable(self):
        """Do'konlar chatdan buyurtma qilinadigan turda bo'lsin (delivery, pickup emas)."""
        call_command('seed_smoke', quiet=True)
        from delivery.models import Store
        for s in Store.objects.all():
            self.assertEqual(s.store_type, 'delivery')
            self.assertFalse(s.pickup_enabled)


class SmokeAgentGuardTests(TestCase):
    def test_without_api_key_fails_with_instructions(self):
        with mock.patch.dict('os.environ', {'AI_API_KEY': ''}):
            with self.assertRaises(CommandError) as cm:
                call_command('smoke_agent', stdout=StringIO())
        msg = str(cm.exception)
        self.assertIn('AI_API_KEY', msg)
        self.assertIn('.env', msg)

    def test_without_seed_fails_clearly(self):
        with mock.patch.dict('os.environ', {'AI_API_KEY': 'sk-test', 'AI_MODEL': 'x'}):
            with self.assertRaises(CommandError) as cm:
                call_command('smoke_agent', stdout=StringIO())
        self.assertIn('seed_smoke', str(cm.exception))

    def test_all_20_cases_defined(self):
        from assistant.management.commands.smoke_agent import CASES
        self.assertEqual(len(CASES), 20)
        self.assertEqual([c['n'] for c in CASES], list(range(1, 21)))
        # Har bir holatda so'rov matni va guruh bo'lishi shart
        for c in CASES:
            self.assertTrue(c['msg'])
            self.assertIn(c['group'], set('ABCDEF'))
