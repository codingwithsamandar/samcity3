"""Biznes panel testlari — do'kon, bron joyi va xaritadagi joy egalari uchun.

    python manage.py test main.test_business_panel
"""
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse

from main.models import User
from booking.models import Venue, VenueService, VenueStaff, VenueBooking
from places.models import Place, PlaceMenuItem


class BusinessPanelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone='+998910000501', password='x', is_active=True)
        self.other = User.objects.create_user(phone='+998910000502', password='x', is_active=True)
        self.client.force_login(self.owner)

    def _get(self):
        return self.client.get(reverse('business_panel'))

    # ── Bo'sh holat ─────────────────────────────────────────────────────────
    def test_empty_state_when_no_business(self):
        resp = self._get()
        self.assertContains(resp, 'Hali biznesingiz')
        self.assertNotContains(resp, "Do&#x27;konlarim")

    def test_login_required(self):
        self.client.logout()
        resp = self.client.get(reverse('business_panel'))
        self.assertEqual(resp.status_code, 302)

    # ── Sartaroshxona (usta + xizmat) ───────────────────────────────────────
    def test_barber_section_shows_staff_stats(self):
        v = Venue.objects.create(owner=self.owner, name='Soch Usta', venue_type='barber',
                                 working_hours_start=time(9), working_hours_end=time(18))
        VenueService.objects.create(venue=v, name='Soch olish', price=30000)
        VenueStaff.objects.create(venue=v, name='Ali')
        resp = self._get()
        self.assertContains(resp, 'Soch Usta')
        self.assertContains(resp, 'Usta')             # ustali blok
        self.assertContains(resp, 'Xizmat va ustalar')
        self.assertNotContains(resp, '🍽️ Menyu')      # sartaroshda menyu yo'q

    def test_pending_booking_counted(self):
        v = Venue.objects.create(owner=self.owner, name='Soch Usta', venue_type='barber')
        VenueBooking.objects.create(venue=v, user=self.other, status='pending',
                                    booking_date=date.today())
        VenueBooking.objects.create(venue=v, user=self.other, status='confirmed',
                                    booking_date=date.today())
        resp = self._get()
        self.assertContains(resp, 'tasdiq kutayotgan bron')
        self.assertEqual(resp.context['venues'][0]['yangi'], 1)
        self.assertEqual(resp.context['venues'][0]['bugun'], 2)

    def test_week_count_excludes_far_bookings(self):
        v = Venue.objects.create(owner=self.owner, name='Soch Usta', venue_type='barber')
        VenueBooking.objects.create(venue=v, user=self.other, status='confirmed',
                                    booking_date=date.today() + timedelta(days=2))
        VenueBooking.objects.create(venue=v, user=self.other, status='confirmed',
                                    booking_date=date.today() + timedelta(days=30))
        self.assertEqual(self._get().context['venues'][0]['hafta'], 1)

    # ── Restoran (menyu) ────────────────────────────────────────────────────
    def test_restaurant_shows_menu_link_when_linked(self):
        place = Place.objects.create(owner=self.owner, name='Anor', category='restaurant',
                                     latitude=40.1, longitude=64.5)
        PlaceMenuItem.objects.create(place=place, name='Osh', price=35000)
        Venue.objects.create(owner=self.owner, name='Anor Restoran',
                             venue_type='restaurant', place=place)
        resp = self._get()
        self.assertContains(resp, reverse('places:place_menu', args=[place.pk]))

    def test_restaurant_without_place_offers_to_link(self):
        Venue.objects.create(owner=self.owner, name='Anor Restoran', venue_type='restaurant')
        resp = self._get()
        self.assertContains(resp, 'Menyu ulash')

    # ── Xaritadagi joy (shifoxona) ──────────────────────────────────────────
    def test_hospital_section_has_no_menu(self):
        Place.objects.create(owner=self.owner, name='Shifo klinika', category='hospital',
                             latitude=40.1, longitude=64.5)
        resp = self._get()
        self.assertContains(resp, 'Shifo klinika')
        self.assertContains(resp, 'Xaritadagi joylarim')
        self.assertFalse(resp.context['places'][0]['menyuli'])

    def test_place_menu_shown_for_restaurant_place(self):
        p = Place.objects.create(owner=self.owner, name='Anor', category='restaurant',
                                 latitude=40.1, longitude=64.5)
        PlaceMenuItem.objects.create(place=p, name='Osh', price=35000)
        resp = self._get()
        self.assertTrue(resp.context['places'][0]['menyuli'])
        self.assertEqual(resp.context['places'][0]['menyu'], 1)

    # ── Egalik chegarasi ────────────────────────────────────────────────────
    def test_other_users_business_not_shown(self):
        Venue.objects.create(owner=self.other, name='Begona joy', venue_type='barber')
        Place.objects.create(owner=self.other, name='Begona klinika', category='hospital',
                             latitude=40.1, longitude=64.5)
        resp = self._get()
        self.assertNotContains(resp, 'Begona joy')
        self.assertNotContains(resp, 'Begona klinika')
        self.assertContains(resp, 'Hali biznesingiz')

    # ── Profil havolasi ─────────────────────────────────────────────────────
    def test_profile_link_hidden_without_business(self):
        resp = self.client.get(reverse('profile'))
        self.assertNotContains(resp, reverse('business_panel'))

    def test_profile_link_shown_with_business(self):
        Venue.objects.create(owner=self.owner, name='Soch Usta', venue_type='barber')
        resp = self.client.get(reverse('profile'))
        self.assertContains(resp, reverse('business_panel'))

    def test_profile_badge_counts_pending(self):
        v = Venue.objects.create(owner=self.owner, name='Soch Usta', venue_type='barber')
        VenueBooking.objects.create(venue=v, user=self.other, status='pending',
                                    booking_date=date.today())
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.context['business_alerts'], 1)

    # ── Asosiy navigatsiyada ko'rinishi (kuryer paneli kabi) ────────────────
    def test_nav_hidden_without_business(self):
        html = self.client.get(reverse('home')).content.decode()
        self.assertNotIn(reverse('business_panel'), html)

    def test_nav_shown_with_business(self):
        Venue.objects.create(owner=self.owner, name='Soch Usta', venue_type='barber')
        html = self.client.get(reverse('home')).content.decode()
        # Yuqori nav (chip), dropdown, mobil menyu va pastki nav — 4 joy
        self.assertGreaterEqual(html.count(reverse('business_panel')), 4)
        self.assertIn('nav-biz', html)

    def test_nav_badge_shows_pending_count(self):
        v = Venue.objects.create(owner=self.owner, name='Soch Usta', venue_type='barber')
        for _ in range(3):
            VenueBooking.objects.create(venue=v, user=self.other, status='pending',
                                        booking_date=date.today())
        html = self.client.get(reverse('home')).content.decode()
        self.assertIn('bn-cnt', html)          # pastki navdagi belgi
        self.assertIn('>3</span>', html)

    def test_place_owner_also_gets_nav(self):
        """Xaritada joyi bor odam ham biznes egasi — roli 'user' bo'lsa ham."""
        Place.objects.create(owner=self.owner, name='Shifo', category='hospital',
                             latitude=40.1, longitude=64.5)
        self.assertEqual(self.owner.role, 'user')
        html = self.client.get(reverse('home')).content.decode()
        self.assertIn(reverse('business_panel'), html)


class PickupStoreTests(TestCase):
    """Pickup (olib ketish) yoqilgan do'konlar panelda ajratilishi."""

    def setUp(self):
        from delivery.models import DeliveryCategory, Store, Product
        self.owner = User.objects.create_user(phone='+998910001101', password='x', is_active=True)
        self.mijoz = User.objects.create_user(phone='+998910001102', password='x', is_active=True)
        cat = DeliveryCategory.objects.create(name='Oziq-ovqat')
        self.store = Store.objects.create(owner=self.owner, name='Anor', category=cat,
                                          pickup_enabled=True)
        self.product = Product.objects.create(store=self.store, name='Non', price=5000)
        self.client.force_login(self.owner)

    def _order(self, fulfillment, status):
        from delivery.models import Order, OrderItem
        o = Order.objects.create(user=self.mijoz, address='M', phone='+998910001102',
                                 fulfillment_type=fulfillment, status=status)
        OrderItem.objects.create(order=o, product=self.product, product_name='Non',
                                 price=5000, quantity=1)
        return o

    def _card(self):
        return self.client.get(reverse('business_panel')).context['stores'][0]

    def test_pickup_store_appears_with_badge(self):
        resp = self.client.get(reverse('business_panel'))
        self.assertTrue(resp.context['stores'][0]['pickup_yoqilgan'])
        self.assertContains(resp, 'Olib ketish')

    def test_ready_pickup_counted_as_waiting(self):
        self._order('pickup', 'ready')
        self.assertEqual(self._card()['pickup_kutmoqda'], 1)

    def test_delivery_order_not_counted_as_pickup(self):
        self._order('delivery', 'ready')
        card = self._card()
        self.assertEqual(card['pickup_kutmoqda'], 0)
        self.assertEqual(card['pickup_jami'], 0)

    def test_pickup_not_ready_is_not_waiting(self):
        self._order('pickup', 'preparing')
        card = self._card()
        self.assertEqual(card['pickup_kutmoqda'], 0)
        self.assertEqual(card['pickup_jami'], 1)

    def test_waiting_banner_shown(self):
        self._order('pickup', 'ready')
        resp = self.client.get(reverse('business_panel'))
        self.assertContains(resp, 'kelib olishini kutmoqda')
        self.assertContains(resp, 'olib ketishga tayyor')

    def test_no_pickup_stats_when_disabled(self):
        self.store.pickup_enabled = False
        self.store.save(update_fields=['pickup_enabled'])
        resp = self.client.get(reverse('business_panel'))
        self.assertFalse(resp.context['stores'][0]['pickup_yoqilgan'])
        self.assertNotContains(resp, 'Mijoz kutmoqda')
