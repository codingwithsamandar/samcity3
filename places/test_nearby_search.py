"""«Yaqinimda» sahifasidagi qidiruv testlari.

    python manage.py test places.test_nearby_search
"""
from django.test import TestCase
from django.urls import reverse

from places.models import Place

# Test koordinatasi — Shofirkon markazi
LAT, LNG = 40.1156, 64.5036


class NearbySearchTests(TestCase):
    def setUp(self):
        # Yaqin (~0 km) va uzoq (~10 km) joylar — tartib masofa bo'yicha
        self.dorixona = Place.objects.create(
            name='Shifo dorixona', category='pharmacy',
            latitude=LAT, longitude=LNG, address='Markaziy ko\'cha 1')
        self.restoran = Place.objects.create(
            name='Registon Restoran', category='restaurant',
            latitude=LAT + 0.09, longitude=LNG, address='Bog\' yo\'li 5')

    def _get(self, **params):
        params.setdefault('lat', LAT)
        params.setdefault('lng', LNG)
        return self.client.get(reverse('places:nearby'), params)

    # ── Joylashuvsiz holat o'zgarmagan ──────────────────────────────────────
    def test_without_location_shows_prompt(self):
        resp = self.client.get(reverse('places:nearby'))
        self.assertContains(resp, 'Joylashuvni aniqlash')
        self.assertNotContains(resp, 'name="q"')

    def test_with_location_shows_search_box(self):
        resp = self._get()
        self.assertContains(resp, 'name="q"')
        self.assertContains(resp, 'Eng yaqin 10 ta')

    # ── Qidiruv ─────────────────────────────────────────────────────────────
    def test_search_by_name(self):
        resp = self._get(q='registon')
        self.assertContains(resp, 'Registon Restoran')
        self.assertNotContains(resp, 'Shifo dorixona')

    def test_search_is_case_insensitive(self):
        self.assertContains(self._get(q='REGISTON'), 'Registon Restoran')

    def test_search_by_address(self):
        resp = self._get(q="Bog'")
        self.assertContains(resp, 'Registon Restoran')

    def test_search_by_category_label(self):
        resp = self._get(q='Dorixona')
        self.assertContains(resp, 'Shifo dorixona')
        self.assertNotContains(resp, 'Registon Restoran')

    def test_results_keep_distance_order(self):
        """Qidiruvda ham natija masofa bo'yicha tartiblanadi."""
        Place.objects.create(name='Uzoq dorixona', category='pharmacy',
                             latitude=LAT + 0.09, longitude=LNG)
        html = self._get(q='dorixona').content.decode()
        self.assertLess(html.index('Shifo dorixona'), html.index('Uzoq dorixona'))

    def test_search_hides_category_groups(self):
        resp = self._get(q='registon')
        self.assertNotContains(resp, 'Eng yaqin 10 ta')
        self.assertNotContains(resp, 'Yaqin do&#x27;konlar')

    def test_no_results_message(self):
        resp = self._get(q='qandaydir-yoq-narsa')
        self.assertContains(resp, 'Hech narsa topilmadi')

    def test_inactive_place_not_found(self):
        Place.objects.create(name='Yopiq joy', category='restaurant',
                             latitude=LAT, longitude=LNG, is_active=False)
        self.assertNotContains(self._get(q='Yopiq'), 'Yopiq joy')

    def test_search_keeps_coordinates_in_form(self):
        """Qidirgandan keyin ham joylashuv yo'qolmasin."""
        resp = self._get(q='registon')
        self.assertContains(resp, f'value="{LAT}"')
        self.assertContains(resp, f'value="{LNG}"')
