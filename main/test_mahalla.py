"""Mahalla bo'limi + /delivery/ 'barcha do'konlar' tekshiruvi."""
from django.test import TestCase
from django.urls import reverse

from main.models import (
    User, Neighborhood, ChatAdmin, NeighborhoodAnnouncement, CitizenRequest,
)
from delivery.models import Store

# Kvadrat chegara: lat 40.10–40.13, lng 64.49–64.52
BOUNDARY = [[40.10, 64.49], [40.10, 64.52], [40.13, 64.52], [40.13, 64.49]]


def make_user(phone, **extra):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True, **extra)


class DeliveryShowsAllStoresTests(TestCase):
    """/delivery/ mahallaga bog'liqlikdan qat'i nazar BARCHA faol do'konlarni ko'rsatadi."""

    def setUp(self):
        self.owner = make_user('+998960000001')
        self.inside = Store.objects.create(owner=self.owner, name='InsideShop',
                                           latitude=40.115, longitude=64.505, is_active=True)
        self.outside = Store.objects.create(owner=self.owner, name='OutsideShop',
                                            latitude=41.0, longitude=65.0, is_active=True)
        self.no_coords = Store.objects.create(owner=self.owner, name='NoCoordShop', is_active=True)

    def test_delivery_list_shows_every_active_store(self):
        html = self.client.get(reverse('delivery:store_list'), HTTP_HOST='127.0.0.1').content.decode()
        self.assertIn('InsideShop', html)
        self.assertIn('OutsideShop', html)
        self.assertIn('NoCoordShop', html)


class MahallaPolygonTests(TestCase):
    """Mahalla sahifasi faqat chegara ichidagi do'konlarni ko'rsatadi (poligon)."""

    def setUp(self):
        self.owner = make_user('+998960000010')
        self.nb = Neighborhood.objects.create(name='PolyMahalla', boundary=BOUNDARY,
                                               population=1234, head_name='Rais')
        self.inside = Store.objects.create(owner=self.owner, name='PolyInside',
                                           latitude=40.115, longitude=64.505, is_active=True)
        self.outside = Store.objects.create(owner=self.owner, name='PolyOutside',
                                            latitude=41.0, longitude=65.0, is_active=True)

    def test_contains_point(self):
        self.assertTrue(self.nb.contains_point(40.115, 64.505))
        self.assertFalse(self.nb.contains_point(41.0, 65.0))

    def test_mahalla_page_only_inside_store(self):
        html = self.client.get(reverse('mahalla_detail', args=[self.nb.pk]),
                               HTTP_HOST='127.0.0.1').content.decode()
        self.assertIn('PolyInside', html)
        self.assertNotIn('PolyOutside', html)
        self.assertIn('1234', html)  # aholi soni

    def test_geojson_includes_inside_store(self):
        r = self.client.get(reverse('places:neighborhood_places_geojson', args=[self.nb.pk]),
                            HTTP_HOST='127.0.0.1')
        names = [p['name'] for p in r.json()['places']]
        self.assertIn('PolyInside', names)
        self.assertNotIn('PolyOutside', names)


class CitizenRequestFlowTests(TestCase):
    """Murojaat: yaratish, admin holatni o'zgartiradi, oddiy foydalanuvchi yo'q."""

    def setUp(self):
        self.nb = Neighborhood.objects.create(name='ReqMahalla', boundary=BOUNDARY)
        self.resident = make_user('+998960000020')
        self.other = make_user('+998960000021')
        self.admin_user = make_user('+998960000022')
        ChatAdmin.objects.create(neighborhood=self.nb, user=self.admin_user)

    def _make_request(self):
        return CitizenRequest.objects.create(
            neighborhood=self.nb, user=self.resident, category='road',
            title='Yo\'l buzuq', text='Tuzatib bering')

    def test_resident_creates_complaint(self):
        self.client.force_login(self.resident)
        self.client.post(reverse('mahalla_complaint', args=[self.nb.pk]),
                         {'category': 'water', 'title': 'Suv yo\'q', 'text': 'Ikki kundan beri'},
                         HTTP_HOST='127.0.0.1')
        self.assertTrue(CitizenRequest.objects.filter(neighborhood=self.nb, user=self.resident).exists())

    def test_non_admin_cannot_change_status(self):
        req = self._make_request()
        self.client.force_login(self.other)
        self.client.post(reverse('mahalla_complaint_status', args=[req.id]),
                         {'status': 'resolved'}, HTTP_HOST='127.0.0.1')
        req.refresh_from_db()
        self.assertEqual(req.status, 'submitted')

    def test_admin_changes_status_and_notifies(self):
        from notifications.models import Notification
        req = self._make_request()
        self.client.force_login(self.admin_user)
        self.client.post(reverse('mahalla_complaint_status', args=[req.id]),
                         {'status': 'reviewing', 'response': 'Ko\'rib chiqyapmiz'},
                         HTTP_HOST='127.0.0.1')
        req.refresh_from_db()
        self.assertEqual(req.status, 'reviewing')
        self.assertEqual(req.response, "Ko'rib chiqyapmiz")
        self.assertTrue(Notification.objects.filter(recipient=self.resident).exists())

    def test_invalid_transition_blocked(self):
        req = self._make_request()
        req.status = 'resolved'
        req.save(update_fields=['status'])
        self.client.force_login(self.admin_user)
        self.client.post(reverse('mahalla_complaint_status', args=[req.id]),
                         {'status': 'reviewing'}, HTTP_HOST='127.0.0.1')
        req.refresh_from_db()
        self.assertEqual(req.status, 'resolved')  # yakuniy holatdan orqaga qaytmaydi


class MahallaApiTests(TestCase):
    """Mobil API: mahalla detali + murojaat yaratish/holat."""

    def setUp(self):
        self.nb = Neighborhood.objects.create(name='ApiMahalla', boundary=BOUNDARY, population=999)
        self.owner = make_user('+998960000030')
        self.store = Store.objects.create(owner=self.owner, name='ApiInside',
                                          latitude=40.115, longitude=64.505, is_active=True)
        self.admin_user = make_user('+998960000031')
        ChatAdmin.objects.create(neighborhood=self.nb, user=self.admin_user)

    def test_api_detail_includes_inside_store(self):
        from rest_framework.test import APIClient
        api = APIClient()
        api.force_authenticate(self.admin_user)
        r = api.get(reverse('api:mahalla-detail', args=[self.nb.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['is_admin'])
        self.assertEqual(r.data['neighborhood']['population'], 999)
        store_names = [s['name'] for s in r.data['stores']]
        self.assertIn('ApiInside', store_names)

    def test_api_complaint_create_and_status(self):
        from rest_framework.test import APIClient
        resident = make_user('+998960000032')
        api = APIClient()
        api.force_authenticate(resident)
        c = api.post(reverse('api:mahalla-complaints', args=[self.nb.pk]),
                     {'category': 'road', 'title': 'T', 'text': 'X'}, format='json')
        self.assertEqual(c.status_code, 201)
        req_id = c.data['id']
        # oddiy foydalanuvchi holatni o'zgartira olmaydi
        r1 = api.post(reverse('api:mahalla-complaint-status', args=[req_id]),
                      {'status': 'resolved'}, format='json')
        self.assertEqual(r1.status_code, 403)
        # admin o'zgartiradi
        api.force_authenticate(self.admin_user)
        r2 = api.post(reverse('api:mahalla-complaint-status', args=[req_id]),
                      {'status': 'reviewing'}, format='json')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data['status'], 'reviewing')
