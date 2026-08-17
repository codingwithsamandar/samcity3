"""Restoran menyusi testlari — joy sahifasi, bron sahifasi, xarita, ruxsatlar.

    python manage.py test places.test_menu
"""
import io
import json
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from main.models import User
from booking.models import Venue
from places.models import Place, PlaceMenuItem


def make_image(name='taom.jpg'):
    buf = io.BytesIO()
    Image.new('RGB', (80, 80), (200, 120, 40)).save(buf, format='JPEG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/jpeg')


_TEST_MEDIA = tempfile.mkdtemp(prefix='place-menu-')


@override_settings(MEDIA_ROOT=_TEST_MEDIA)
class PlaceMenuTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEST_MEDIA, ignore_errors=True)

    def setUp(self):
        self.owner = User.objects.create_user(phone='+998910000301', password='x', is_active=True)
        self.other = User.objects.create_user(phone='+998910000302', password='x', is_active=True)
        self.place = Place.objects.create(
            owner=self.owner, name='Registon Restoran', category='restaurant',
            latitude=40.115, longitude=64.503)

    def _add(self, **extra):
        data = {'name': 'Osh', 'price': '35000', 'section': 'main'}
        data.update(extra)
        return self.client.post(
            reverse('places:menu_item_add', args=[self.place.pk]), data, follow=True)

    # ── Egasi menyuni boshqaradi ────────────────────────────────────────────
    def test_owner_adds_menu_item(self):
        self.client.force_login(self.owner)
        self._add(description='Qora osh', image=make_image())
        item = PlaceMenuItem.objects.get(place=self.place)
        self.assertEqual(item.name, 'Osh')
        self.assertEqual(item.price, 35000)
        self.assertEqual(item.section, 'main')
        self.assertEqual(item.description, 'Qora osh')
        self.assertTrue(item.image.name)

    def test_name_and_price_required(self):
        self.client.force_login(self.owner)
        self._add(name='')
        self._add(price='')
        self.assertEqual(PlaceMenuItem.objects.count(), 0)

    def test_unknown_section_falls_back_to_main(self):
        self.client.force_login(self.owner)
        self._add(section='qandaydir-yolgon')
        self.assertEqual(PlaceMenuItem.objects.get().section, 'main')

    def test_stranger_cannot_add_or_delete(self):
        item = PlaceMenuItem.objects.create(place=self.place, name='Somsa', price=8000)
        self.client.force_login(self.other)
        self._add(name='Begona taom')
        self.client.post(reverse('places:menu_item_delete', args=[item.pk]), follow=True)
        self.assertEqual(PlaceMenuItem.objects.count(), 1)
        self.assertTrue(PlaceMenuItem.objects.filter(pk=item.pk).exists())

    def test_owner_deletes_item(self):
        item = PlaceMenuItem.objects.create(place=self.place, name='Somsa', price=8000)
        self.client.force_login(self.owner)
        self.client.post(reverse('places:menu_item_delete', args=[item.pk]), follow=True)
        self.assertFalse(PlaceMenuItem.objects.filter(pk=item.pk).exists())

    def test_menu_page_needs_permission(self):
        self.client.force_login(self.other)
        resp = self.client.get(reverse('places:place_menu', args=[self.place.pk]), follow=True)
        self.assertContains(resp, "huquqingiz yo&#x27;q")

    # ── Ko'rinishi ──────────────────────────────────────────────────────────
    def test_menu_shown_on_place_page_grouped(self):
        PlaceMenuItem.objects.create(place=self.place, name='Osh', price=35000, section='main')
        PlaceMenuItem.objects.create(place=self.place, name='Achchiq-chuchuk',
                                     price=12000, section='salad')
        PlaceMenuItem.objects.create(place=self.place, name='Yashirin taom',
                                     price=1000, is_active=False)
        resp = self.client.get(reverse('places:place_detail', args=[self.place.pk]))
        self.assertContains(resp, 'Osh')
        self.assertContains(resp, 'Achchiq-chuchuk')
        self.assertContains(resp, 'Salatlar')          # bo'lim sarlavhasi
        self.assertContains(resp, 'Asosiy taomlar')
        self.assertNotContains(resp, 'Yashirin taom')  # is_active=False

    def test_menu_visible_on_booking_page_via_link(self):
        """Bron joyi xaritadagi joyga bog'lansa — menyu bron sahifasida ham."""
        PlaceMenuItem.objects.create(place=self.place, name='Osh', price=35000)
        venue = Venue.objects.create(
            owner=self.owner, name='Registon', venue_type='restaurant', place=self.place)
        resp = self.client.get(reverse('venue_detail', args=[venue.pk]))
        self.assertContains(resp, 'Osh')
        self.assertContains(resp, 'Menyu')

    def test_unlinked_venue_has_no_menu(self):
        PlaceMenuItem.objects.create(place=self.place, name='Osh', price=35000)
        venue = Venue.objects.create(
            owner=self.owner, name='Bog`langan emas', venue_type='restaurant')
        resp = self.client.get(reverse('venue_detail', args=[venue.pk]))
        self.assertNotContains(resp, 'Osh')

    def test_geojson_flags_places_with_menu(self):
        empty = Place.objects.create(owner=self.owner, name='Menyusiz',
                                     category='restaurant', latitude=40.1, longitude=64.5)
        PlaceMenuItem.objects.create(place=self.place, name='Osh', price=35000)
        data = json.loads(self.client.get(reverse('places:geojson')).content)
        flags = {p['id']: p['has_menu'] for p in data['places'] if 'has_menu' in p}
        self.assertTrue(flags[self.place.pk])
        self.assertFalse(flags[empty.pk])

    def test_hidden_item_does_not_flag_geojson(self):
        PlaceMenuItem.objects.create(place=self.place, name='Yashirin',
                                     price=1000, is_active=False)
        data = json.loads(self.client.get(reverse('places:geojson')).content)
        flags = {p['id']: p['has_menu'] for p in data['places'] if 'has_menu' in p}
        self.assertFalse(flags[self.place.pk])
