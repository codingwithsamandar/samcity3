"""To'yxona/joy egasi bron boshqaruvi mobil API testlari."""
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import User
from booking.models import Venue, VenueBooking


def make_user(phone, name='Foydalanuvchi'):
    return User.objects.create_user(phone=phone, password='Test12345!',
                                    name=name, is_active=True)


class VenueOwnerAPITests(TestCase):
    def setUp(self):
        self.owner = make_user('+998914000001', 'Egasi')
        self.customer = make_user('+998914000002', 'Mijoz Ali')
        self.venue = Venue.objects.create(
            owner=self.owner, name='Nur To\'yxona', venue_type='wedding')
        self.tomorrow = date.today() + timedelta(days=10)
        self.booking = VenueBooking.objects.create(
            venue=self.venue, user=self.customer, status='pending',
            booking_date=self.tomorrow, guests=100, total_amount=5000000)
        self.c = APIClient()
        self.c.force_authenticate(self.owner)

    # ── Ro'yxat ──
    def test_owner_sees_pending_and_others(self):
        VenueBooking.objects.create(
            venue=self.venue, user=self.customer, status='confirmed',
            booking_date=self.tomorrow + timedelta(days=1), guests=50, total_amount=3000000)
        r = self.c.get(reverse('api:venue-owner-bookings'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['pending']), 1)
        self.assertEqual(len(r.data['others']), 1)

    def test_customer_info_visible_to_owner(self):
        r = self.c.get(reverse('api:venue-owner-bookings'))
        b = r.data['pending'][0]
        self.assertEqual(b['customer_name'], 'Mijoz Ali')
        self.assertEqual(b['customer_phone'], '+998914000002')

    def test_only_own_venue_bookings(self):
        other_owner = make_user('+998914000003')
        other_venue = Venue.objects.create(owner=other_owner, name='X', venue_type='wedding')
        VenueBooking.objects.create(
            venue=other_venue, user=self.customer, status='pending',
            booking_date=self.tomorrow, guests=10, total_amount=1000)
        r = self.c.get(reverse('api:venue-owner-bookings'))
        # Faqat o'z joyidagi 1 ta pending ko'rinadi
        self.assertEqual(len(r.data['pending']), 1)

    # ── Amallar ──
    def test_confirm(self):
        r = self.c.post(reverse('api:venue-owner-action',
                                args=[self.booking.id, 'confirm']))
        self.assertEqual(r.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'confirmed')

    def test_complete(self):
        r = self.c.post(reverse('api:venue-owner-action',
                                args=[self.booking.id, 'complete']))
        self.assertEqual(r.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'completed')

    def test_cancel(self):
        r = self.c.post(reverse('api:venue-owner-action',
                                args=[self.booking.id, 'cancel']))
        self.assertEqual(r.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'cancelled')

    def test_unknown_action_rejected(self):
        r = self.c.post(reverse('api:venue-owner-action',
                                args=[self.booking.id, 'explode']))
        self.assertEqual(r.status_code, 400)

    def test_finalized_booking_not_changeable(self):
        self.booking.status = 'completed'
        self.booking.save(update_fields=['status'])
        r = self.c.post(reverse('api:venue-owner-action',
                                args=[self.booking.id, 'cancel']))
        self.assertEqual(r.status_code, 400)

    def test_non_owner_forbidden(self):
        intruder = make_user('+998914000009')
        c = APIClient(); c.force_authenticate(intruder)
        r = c.post(reverse('api:venue-owner-action', args=[self.booking.id, 'confirm']))
        self.assertEqual(r.status_code, 403)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'pending')

    # ── Egasi joylari ──
    def test_my_venues(self):
        r = self.c.get(reverse('api:my-venues'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0]['name'], 'Nur To\'yxona')

    def test_requires_auth(self):
        c = APIClient()
        r = c.get(reverse('api:venue-owner-bookings'))
        self.assertIn(r.status_code, (401, 403))
