"""To'yxona/joy egasi setup (venue create/edit + xizmat/usta) API testlari."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import User
from booking.models import Venue, VenueService, VenueStaff


def make_user(phone):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True)


class VenueSetupTests(TestCase):
    def setUp(self):
        self.owner = make_user('+998936300001')
        self.venue = Venue.objects.create(
            owner=self.owner, name='Baht to\'yxonasi', venue_type='wedding',
            is_active=True)
        self.c = APIClient()
        self.c.force_authenticate(self.owner)

    # ── Joy yaratish ──
    def test_create_venue_sets_role_business(self):
        u = make_user('+998936300010')
        c = APIClient(); c.force_authenticate(u)
        r = c.post(reverse('api:my-venues'), {
            'name': 'Yangi restoran', 'venue_type': 'restaurant',
            'price_per_hour': 50000}, format='json')
        self.assertEqual(r.status_code, 201)
        u.refresh_from_db()
        self.assertEqual(u.role, 'business')
        self.assertTrue(Venue.objects.filter(owner=u, name='Yangi restoran').exists())

    def test_create_requires_name(self):
        r = self.c.post(reverse('api:my-venues'), {'venue_type': 'cafe'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_my_venues_lists_owned(self):
        r = self.c.get(reverse('api:my-venues'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0]['name'], 'Baht to\'yxonasi')

    # ── Egasi to'liq detali ──
    def test_owner_detail_has_editable_fields(self):
        VenueService.objects.create(venue=self.venue, name='Zal', price=1000000)
        VenueStaff.objects.create(venue=self.venue, name='Oshpaz')
        r = self.c.get(reverse('api:my-venue-detail', args=[self.venue.id]))
        self.assertEqual(r.status_code, 200)
        # Tahrir uchun kerakli maydonlar
        for f in ('cancel_penalty_percent', 'grace_minutes', 'is_active',
                  'working_hours_start', 'prepay_required'):
            self.assertIn(f, r.data)
        self.assertEqual(len(r.data['services']), 1)
        self.assertEqual(len(r.data['staff']), 1)

    def test_owner_detail_others_venue_404(self):
        other = make_user('+998936300011')
        c = APIClient(); c.force_authenticate(other)
        r = c.get(reverse('api:my-venue-detail', args=[self.venue.id]))
        self.assertEqual(r.status_code, 404)

    # ── Tahrir ──
    def test_patch_venue(self):
        r = self.c.patch(reverse('api:my-venue-detail', args=[self.venue.id]),
                         {'name': 'Yangi nom', 'capacity': 300, 'is_active': False},
                         format='json')
        self.assertEqual(r.status_code, 200)
        self.venue.refresh_from_db()
        self.assertEqual(self.venue.name, 'Yangi nom')
        self.assertEqual(self.venue.capacity, 300)
        self.assertFalse(self.venue.is_active)

    def test_patch_penalty_over_max_rejected(self):
        r = self.c.patch(reverse('api:my-venue-detail', args=[self.venue.id]),
                         {'cancel_penalty_percent': 50}, format='json')
        self.assertEqual(r.status_code, 400)

    # ── O'chirish ──
    def test_delete_venue(self):
        r = self.c.delete(reverse('api:my-venue-detail', args=[self.venue.id]))
        self.assertEqual(r.status_code, 204)
        self.assertFalse(Venue.objects.filter(pk=self.venue.id).exists())

    def test_delete_others_venue_404(self):
        other = make_user('+998936300012')
        c = APIClient(); c.force_authenticate(other)
        r = c.delete(reverse('api:my-venue-detail', args=[self.venue.id]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Venue.objects.filter(pk=self.venue.id).exists())

    # ── Xizmatlar ──
    def test_add_service(self):
        r = self.c.post(reverse('api:my-venue-service-add', args=[self.venue.id]),
                        {'name': 'Soch olish', 'price': 30000, 'duration_minutes': 30},
                        format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.venue.services.count(), 1)

    def test_add_service_requires_valid_price(self):
        r = self.c.post(reverse('api:my-venue-service-add', args=[self.venue.id]),
                        {'name': 'X', 'price': 0}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_delete_service(self):
        svc = VenueService.objects.create(venue=self.venue, name='X', price=1000)
        r = self.c.delete(reverse('api:my-venue-service-delete', args=[svc.id]))
        self.assertEqual(r.status_code, 204)
        self.assertFalse(VenueService.objects.filter(pk=svc.id).exists())

    def test_delete_others_service_404(self):
        other = make_user('+998936300013')
        v2 = Venue.objects.create(owner=other, name='O\'zga', venue_type='cafe')
        svc = VenueService.objects.create(venue=v2, name='X', price=1000)
        r = self.c.delete(reverse('api:my-venue-service-delete', args=[svc.id]))
        self.assertEqual(r.status_code, 404)

    # ── Ustalar ──
    def test_add_staff(self):
        r = self.c.post(reverse('api:my-venue-staff-add', args=[self.venue.id]),
                        {'name': 'Aziz', 'specialty': 'Sartarosh'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.venue.staff.count(), 1)

    def test_add_staff_requires_name(self):
        r = self.c.post(reverse('api:my-venue-staff-add', args=[self.venue.id]),
                        {'specialty': 'X'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_delete_staff(self):
        st = VenueStaff.objects.create(venue=self.venue, name='Aziz')
        r = self.c.delete(reverse('api:my-venue-staff-delete', args=[st.id]))
        self.assertEqual(r.status_code, 204)
        self.assertFalse(VenueStaff.objects.filter(pk=st.id).exists())

    # ── Ruxsat ──
    def test_requires_auth(self):
        c = APIClient()
        r = c.get(reverse('api:my-venues'))
        self.assertIn(r.status_code, (401, 403))

    def test_add_service_to_others_venue_404(self):
        other = make_user('+998936300014')
        c = APIClient(); c.force_authenticate(other)
        r = c.post(reverse('api:my-venue-service-add', args=[self.venue.id]),
                   {'name': 'X', 'price': 1000}, format='json')
        self.assertEqual(r.status_code, 404)
