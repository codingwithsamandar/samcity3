"""Do'kon turlari testlari: 'delivery' (admin) vs 'mahalla' (ariza→tasdiq).

Tekshiriladi:
  • /delivery/ (web + API) faqat yetkazib beruvchi do'konlarni ko'rsatadi.
  • Oddiy user yetkazib beruvchi do'kon YARATA OLMAYDI.
  • Mahalla do'kon arizasi → tasdiqlangach 'mahalla' turidagi do'kon yaratiladi.
  • Faqat mahalla admini/staff arizani tasdiqlaydi.
  • Mahalla sahifasi faqat o'sha mahallaning mahalla do'konlarini ko'rsatadi.
"""
from django.test import TestCase
from django.urls import reverse

from main.models import User, Neighborhood, ChatAdmin
from delivery.models import Store, StoreRequest


def make_user(phone, **extra):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True, **extra)


class StoreTypeSeparationTests(TestCase):
    def setUp(self):
        self.admin = make_user('+998939000001', is_staff=True)
        self.owner = make_user('+998939000002')
        self.nb = Neighborhood.objects.create(name='Test mahalla')
        # Yetkazib beruvchi do'kon (admin yaratgan) + mahalla do'koni
        self.delivery_store = Store.objects.create(
            owner=self.admin, name='Katta market', store_type='delivery', is_active=True)
        self.mahalla_store = Store.objects.create(
            owner=self.owner, name='Mahalla do\'kon', store_type='mahalla',
            neighborhood=self.nb, pickup_enabled=True, is_active=True)

    def test_delivery_list_excludes_mahalla(self):
        """/delivery/ — mahalla do'koni CHIQMAYDI, yetkazib beruvchi bor."""
        html = self.client.get(reverse('delivery:store_list'), HTTP_HOST='127.0.0.1').content.decode()
        self.assertIn('Katta market', html)
        self.assertNotIn("Mahalla do'kon", html)

    def test_api_store_list_excludes_mahalla(self):
        from rest_framework.test import APIClient
        data = APIClient().get('/api/stores/').data
        names = [s['name'] for s in (data.get('results') or data)]
        self.assertIn('Katta market', names)
        self.assertNotIn("Mahalla do'kon", names)

    def test_mahalla_store_detail_still_reachable(self):
        """Mahalla do'koni sahifasi to'g'ridan-to'g'ri ochiladi (retrieve)."""
        r = self.client.get(reverse('delivery:store_detail', args=[self.mahalla_store.pk]),
                             HTTP_HOST='127.0.0.1')
        self.assertEqual(r.status_code, 200)


class DeliveryCreateRestrictedTests(TestCase):
    def setUp(self):
        self.user = make_user('+998939000010')

    def test_regular_user_cannot_create_delivery_store_web(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse('delivery:store_create'), HTTP_HOST='127.0.0.1')
        # Ariza sahifasiga yo'naltiriladi
        self.assertRedirects(r, reverse('delivery:store_request_create'),
                             target_status_code=200, fetch_redirect_response=False)

    def test_regular_user_cannot_create_delivery_store_api(self):
        from rest_framework.test import APIClient
        c = APIClient()
        c.force_authenticate(self.user)
        r = c.post('/api/my/stores/', {'name': 'X'}, format='json')
        self.assertEqual(r.status_code, 403)


class StoreRequestFlowTests(TestCase):
    def setUp(self):
        self.applicant = make_user('+998939000020')
        self.rais = make_user('+998939000021')          # mahalla admini
        self.outsider = make_user('+998939000022')      # begona
        self.nb = Neighborhood.objects.create(name='Arizali mahalla')
        ChatAdmin.objects.create(neighborhood=self.nb, user=self.rais)

    def _make_request(self):
        return StoreRequest.objects.create(
            user=self.applicant, neighborhood=self.nb, name='Yangi mahalla do\'kon',
            address='Ko\'cha 1', phone='+998901112233')

    def test_approve_creates_mahalla_store(self):
        req = self._make_request()
        store = req.approve(reviewer=self.rais)
        self.assertEqual(store.store_type, 'mahalla')
        self.assertEqual(store.owner, self.applicant)
        self.assertEqual(store.neighborhood, self.nb)
        self.assertTrue(store.pickup_enabled)
        req.refresh_from_db()
        self.assertEqual(req.status, 'approved')
        self.assertEqual(req.created_store_id, store.pk)
        # Arizachi 'business' roliga o'tadi
        self.applicant.refresh_from_db()
        self.assertEqual(self.applicant.role, 'business')

    def test_outsider_cannot_review(self):
        req = self._make_request()
        self.client.force_login(self.outsider)
        self.client.post(reverse('delivery:store_request_review', args=[req.pk]),
                         {'action': 'approve'}, HTTP_HOST='127.0.0.1')
        req.refresh_from_db()
        self.assertEqual(req.status, 'pending')  # o'zgarmadi
        self.assertFalse(Store.objects.filter(store_type='mahalla', owner=self.applicant).exists())

    def test_rais_can_approve_web(self):
        req = self._make_request()
        self.client.force_login(self.rais)
        self.client.post(reverse('delivery:store_request_review', args=[req.pk]),
                         {'action': 'approve'}, HTTP_HOST='127.0.0.1')
        req.refresh_from_db()
        self.assertEqual(req.status, 'approved')
        self.assertTrue(Store.objects.filter(
            store_type='mahalla', owner=self.applicant, neighborhood=self.nb).exists())

    def test_reject_notifies_and_no_store(self):
        req = self._make_request()
        req.reject(reviewer=self.rais, note='Ma\'lumot yetarli emas')
        req.refresh_from_db()
        self.assertEqual(req.status, 'rejected')
        self.assertEqual(req.admin_note, 'Ma\'lumot yetarli emas')
        self.assertFalse(Store.objects.filter(store_type='mahalla').exists())
