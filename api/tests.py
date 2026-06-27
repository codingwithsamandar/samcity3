"""SamCity mobil API uchun testlar.

Ishga tushirish:
    python manage.py test api

Qamrab olingan: notifications, auth (OTP/login/throttle), delivery (savat,
checkout, multi-store split, stock), taxi (trip), booking (bron, to'qnashuv).
"""
from datetime import date, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import User, OTPCode
from notifications.models import Notification, notify
from delivery.models import Store, Product, Cart
from taxi.models import Taxist, Route
from booking.models import Venue, VenueBooking


def make_user(phone, **kw):
    kw.setdefault('name', 'User')
    kw.setdefault('is_active', True)
    return User.objects.create_user(phone=phone, password='Test12345!', **kw)


# ─────────────────────────── Notifications ───────────────────────────
class NotificationAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user('+998900000001')
        self.other = make_user('+998900000002')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_returns_only_own_notifications(self):
        notify(self.user, 'Sizga xabar', '/x/', 'system')
        notify(self.other, 'Boshqaga xabar', '/y/', 'system')
        resp = self.client.get(reverse('api:notifications'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['unread'], 1)
        self.assertEqual(resp.data['results'][0]['text'], 'Sizga xabar')

    def test_unread_count_endpoint(self):
        notify(self.user, 'A', '', 'order')
        notify(self.user, 'B', '', 'chat')
        resp = self.client.get(reverse('api:notifications-unread-count'))
        self.assertEqual(resp.data['unread'], 2)

    def test_unread_filter(self):
        n1 = notify(self.user, 'A', '', 'order')
        notify(self.user, 'B', '', 'chat')
        Notification.objects.filter(pk=n1.pk).update(is_read=True)
        resp = self.client.get(reverse('api:notifications'), {'unread': '1'})
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['results'][0]['text'], 'B')

    def test_mark_specific_read(self):
        n1 = notify(self.user, 'A', '', 'order')
        notify(self.user, 'B', '', 'chat')
        resp = self.client.post(
            reverse('api:notifications-read'), {'ids': [n1.pk]}, format='json')
        self.assertEqual(resp.data['updated'], 1)
        self.assertEqual(resp.data['unread'], 1)
        self.assertTrue(Notification.objects.get(pk=n1.pk).is_read)

    def test_mark_all_read_when_no_ids(self):
        notify(self.user, 'A', '', 'order')
        notify(self.user, 'B', '', 'chat')
        resp = self.client.post(reverse('api:notifications-read'), {}, format='json')
        self.assertEqual(resp.data['updated'], 2)
        self.assertEqual(resp.data['unread'], 0)

    def test_requires_authentication(self):
        resp = APIClient().get(reverse('api:notifications'))
        self.assertIn(resp.status_code, (401, 403))

    def test_cannot_mark_others_notifications(self):
        other_n = notify(self.other, 'Boshqaga', '', 'system')
        resp = self.client.post(
            reverse('api:notifications-read'), {'ids': [other_n.pk]}, format='json')
        self.assertEqual(resp.data['updated'], 0)
        self.assertFalse(Notification.objects.get(pk=other_n.pk).is_read)


# ─────────────────────────── Auth (OTP / login) ───────────────────────────
class AuthAPITests(TestCase):
    def setUp(self):
        cache.clear()  # throttle hisoblagichlari testlar orasida sizib o'tmasin
        self.client = APIClient()

    def test_register_creates_inactive_user_and_otp(self):
        resp = self.client.post(reverse('api:register'),
                                {'phone': '+998901112233', 'password': 'Test12345!'},
                                format='json')
        self.assertEqual(resp.status_code, 201)
        u = User.objects.get(phone='+998901112233')
        self.assertFalse(u.is_active)
        self.assertTrue(OTPCode.objects.filter(phone='+998901112233').exists())

    def test_full_otp_verification_activates_and_returns_tokens(self):
        phone = '+998901112244'
        self.client.post(reverse('api:register'),
                         {'phone': phone, 'password': 'Test12345!'}, format='json')
        code = OTPCode.objects.filter(phone=phone).latest('created_at').code
        resp = self.client.post(reverse('api:verify-otp'),
                                {'phone': phone, 'code': code}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)
        self.assertTrue(User.objects.get(phone=phone).is_active)

    def test_wrong_otp_rejected(self):
        phone = '+998901112255'
        self.client.post(reverse('api:register'),
                         {'phone': phone, 'password': 'Test12345!'}, format='json')
        resp = self.client.post(reverse('api:verify-otp'),
                                {'phone': phone, 'code': '000000'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(User.objects.get(phone=phone).is_active)

    def test_login_success_and_failure(self):
        make_user('+998901112266')
        ok = self.client.post(reverse('api:login'),
                              {'phone': '+998901112266', 'password': 'Test12345!'},
                              format='json')
        self.assertEqual(ok.status_code, 200)
        self.assertIn('access', ok.data)
        bad = self.client.post(reverse('api:login'),
                               {'phone': '+998901112266', 'password': 'wrong'},
                               format='json')
        self.assertEqual(bad.status_code, 401)

    def test_otp_send_is_throttled(self):
        # register (1-yuborish) + resend'lar; otp_send=5/min — bir necha urinishdan
        # so'ng 429 kelishi shart.
        phone = '+998901112277'
        self.client.post(reverse('api:register'),
                         {'phone': phone, 'password': 'Test12345!'}, format='json')
        statuses = []
        for _ in range(8):
            r = self.client.post(reverse('api:resend-otp'), {'phone': phone}, format='json')
            statuses.append(r.status_code)
        self.assertIn(429, statuses)


# ─────────────────────────── Delivery (savat / checkout) ───────────────────────────
class DeliveryAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user('+998902000001')
        self.seller = make_user('+998902000002')
        self.seller2 = make_user('+998902000003')
        self.store = Store.objects.create(owner=self.seller, name="Do'kon 1")
        self.store2 = Store.objects.create(owner=self.seller2, name="Do'kon 2")
        self.p1 = Product.objects.create(store=self.store, name='Olma',
                                         price=Decimal('5000'), stock=10)
        self.p2 = Product.objects.create(store=self.store2, name='Non',
                                         price=Decimal('3000'), stock=10)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _add(self, product, qty=1):
        return self.client.post(reverse('api:cart-add'),
                                {'product_id': product.id, 'quantity': qty}, format='json')

    def test_cart_add_and_subtotal(self):
        resp = self._add(self.p1, 2)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['subtotal'], 10000)

    def test_cart_add_over_stock_rejected(self):
        resp = self._add(self.p1, 999)
        self.assertEqual(resp.status_code, 409)

    def test_checkout_creates_order_and_decrements_stock(self):
        self._add(self.p1, 2)
        resp = self.client.post(reverse('api:checkout'),
                                {'phone': '+998901234567', 'address': 'Samarqand',
                                 'payment_method': 'cash'}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['count'], 1)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 8)

    def test_checkout_splits_by_store(self):
        self._add(self.p1, 1)
        self._add(self.p2, 1)
        resp = self.client.post(reverse('api:checkout'),
                                {'phone': '+998901234567', 'address': 'Samarqand',
                                 'payment_method': 'cash'}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['count'], 2)  # har do'kon — alohida buyurtma
        # Har bir do'kon egasiga bildirishnoma keldi
        self.assertTrue(Notification.objects.filter(recipient=self.seller).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.seller2).exists())

    def test_checkout_empty_cart_rejected(self):
        resp = self.client.post(reverse('api:checkout'),
                                {'phone': '+998901234567', 'address': 'X',
                                 'payment_method': 'cash'}, format='json')
        self.assertEqual(resp.status_code, 400)


# ─────────────────────────── Taxi ───────────────────────────
class TaxiAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.passenger = make_user('+998903000001')
        self.driver_user = make_user('+998903000002')
        self.taxist = Taxist.objects.create(
            user=self.driver_user, full_name='Ali', phone='+998903000002')
        self.route = Route.objects.create(
            taxist=self.taxist, point_a='Samarqand', point_b='Toshkent',
            passenger_price=100000, delivery_price=50000)
        self.client = APIClient()
        self.client.force_authenticate(user=self.passenger)

    def test_create_trip_and_notify_taxist(self):
        resp = self.client.post(reverse('api:trip-list'),
                                {'route_id': str(self.route.id), 'is_delivery': False},
                                format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['price'], 100000)
        self.assertTrue(Notification.objects.filter(recipient=self.driver_user).exists())

    def test_create_trip_invalid_route(self):
        import uuid
        resp = self.client.post(reverse('api:trip-list'),
                                {'route_id': str(uuid.uuid4())}, format='json')
        self.assertEqual(resp.status_code, 404)


# ─────────────────────────── Booking ───────────────────────────
class BookingAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user('+998904000001')
        self.owner = make_user('+998904000002')
        self.venue = Venue.objects.create(
            owner=self.owner, name='To\'yxona', venue_type='wedding',
            price_per_day=5000000)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.day = (date.today() + timedelta(days=7)).isoformat()

    def test_book_venue_and_notify_owner(self):
        resp = self.client.post(reverse('api:venue-book', args=[self.venue.id]),
                                {'booking_date': self.day, 'guests': 50}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(VenueBooking.objects.filter(venue=self.venue).count(), 1)
        self.assertTrue(Notification.objects.filter(recipient=self.owner).exists())

    def test_double_booking_conflict(self):
        self.client.post(reverse('api:venue-book', args=[self.venue.id]),
                         {'booking_date': self.day}, format='json')
        resp = self.client.post(reverse('api:venue-book', args=[self.venue.id]),
                                {'booking_date': self.day}, format='json')
        self.assertEqual(resp.status_code, 409)  # to'y — kun band

    def test_cancel_booking(self):
        b = self.client.post(reverse('api:venue-book', args=[self.venue.id]),
                             {'booking_date': self.day}, format='json')
        bid = b.data['id']
        resp = self.client.post(reverse('api:venue-booking-cancel', args=[bid]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(VenueBooking.objects.get(pk=bid).status, 'cancelled')
