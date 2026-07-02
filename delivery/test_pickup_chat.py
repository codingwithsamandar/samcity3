"""3-bosqich testlari: pickup (olib ketish) ish oqimi + do'kon chat."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from main.models import User
from delivery.models import (
    Store, Product, DeliveryDriver, Order, OrderItem, StoreChatThread,
    can_transition,
)


def make_user(phone):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True)


class PickupCheckoutTests(TestCase):
    """Pickup buyurtma: to'lov MAJBURIY oldindan (naqd rad etiladi)."""

    def setUp(self):
        self.owner = make_user('+998932000010')
        self.customer = make_user('+998932000011')
        self.store = Store.objects.create(
            owner=self.owner, name="Pickup do'kon", pickup_enabled=True)
        self.product = Product.objects.create(
            store=self.store, name='Non', price=Decimal('5000'), stock=10, is_available=True)

    def _add_to_cart(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('delivery:cart_add', args=[self.product.pk]))

    def test_cash_pickup_rejected_web(self):
        self._add_to_cart()
        resp = self.client.post(
            reverse('delivery:checkout'),
            {'phone': '+998932000011', 'payment_method': 'cash'}, follow=True)
        self.assertEqual(Order.objects.filter(user=self.customer).count(), 0)
        self.assertContains(resp, 'faqat karta orqali')

    def test_card_pickup_creates_paid_accepted_order_web(self):
        self._add_to_cart()
        self.client.post(reverse('delivery:checkout'), {
            'phone': '+998932000011', 'payment_method': 'card',
            'card_number': '8600123412341234', 'cvv': '123', 'expiry': '12/27',
        }, follow=True)
        order = Order.objects.filter(user=self.customer, fulfillment_type='pickup').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.delivery_fee, 0)
        self.assertTrue(order.is_paid)
        self.assertEqual(order.status, 'accepted')

    def test_cash_pickup_rejected_api(self):
        from rest_framework.test import APIClient
        self._add_to_cart()
        api = APIClient()
        api.force_authenticate(self.customer)
        resp = api.post(reverse('api:checkout'),
                        {'phone': '+998932000011', 'payment_method': 'cash'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Order.objects.filter(user=self.customer).count(), 0)


class PickupPaymentGatewayTests(TestCase):
    """To'lov shlyuzi pickup buyurtmani 'accepted' holatiga o'tkazadi."""

    def setUp(self):
        self.owner = make_user('+998932000020')
        self.customer = make_user('+998932000021')
        self.store = Store.objects.create(owner=self.owner, name='PG shop', pickup_enabled=True)
        self.order = Order.objects.create(
            user=self.customer, address='', status='pending', total=5000,
            fulfillment_type='pickup', payment_status='unpaid')
        OrderItem.objects.create(
            order=self.order, product_name='Non', store_name=self.store.name,
            price=Decimal('5000'), quantity=1,
            product=Product.objects.create(store=self.store, name='Non', price=5000, stock=5))

    def test_mark_paid_advances_pickup_to_accepted(self):
        from payments.gateways import PAYABLES
        PAYABLES['order']['mark_paid'](self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'paid')
        self.assertEqual(self.order.status, 'accepted')


class PickupConfirmTests(TestCase):
    """Mijoz 'qabul qildim' — faqat egasi (mijoz), faqat 'ready' holatida."""

    def setUp(self):
        self.owner = make_user('+998932000030')
        self.customer = make_user('+998932000031')
        self.other = make_user('+998932000032')
        self.store = Store.objects.create(owner=self.owner, name='Conf shop', pickup_enabled=True)
        self.order = Order.objects.create(
            user=self.customer, address='', status='ready', total=5000,
            fulfillment_type='pickup', payment_status='paid')

    def test_other_user_cannot_confirm(self):
        self.client.force_login(self.other)
        self.client.post(reverse('delivery:order_confirm_pickup', args=[self.order.id]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'ready')
        self.assertIsNone(self.order.customer_confirmed_at)

    def test_owner_cannot_confirm_on_behalf(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('delivery:order_confirm_pickup', args=[self.order.id]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'ready')

    def test_customer_confirms_to_delivered(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('delivery:order_confirm_pickup', args=[self.order.id]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'delivered')
        self.assertIsNotNone(self.order.customer_confirmed_at)

    def test_cannot_confirm_before_ready(self):
        self.order.status = 'preparing'
        self.order.save(update_fields=['status'])
        self.client.force_login(self.customer)
        self.client.post(reverse('delivery:order_confirm_pickup', args=[self.order.id]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'preparing')


class PickupTransitionTests(TestCase):
    """Pickup uchun can_transition zanjiri (haydovchisiz)."""

    def test_pickup_chain(self):
        self.assertTrue(can_transition('accepted', 'preparing', 'pickup'))
        self.assertTrue(can_transition('preparing', 'ready', 'pickup'))
        self.assertTrue(can_transition('ready', 'delivered', 'pickup'))
        self.assertFalse(can_transition('ready', 'assigned', 'pickup'))

    def test_pickup_order_not_in_driver_available(self):
        owner = make_user('+998932000040')
        customer = make_user('+998932000041')
        driver_user = make_user('+998932000042')
        DeliveryDriver.objects.create(
            user=driver_user, full_name='D', phone='+998932000042', is_available=True)
        pickup_order = Order.objects.create(
            user=customer, address='', status='ready', total=5000,
            fulfillment_type='pickup', payment_status='paid')
        self.client.force_login(driver_user)
        self.client.get(reverse('delivery:driver_dashboard'))
        # Haydovchi to'g'ridan-to'g'ri accept qilishga urinsa — muvaffaqiyatsiz.
        self.client.post(reverse('delivery:order_accept', args=[pickup_order.id]))
        pickup_order.refresh_from_db()
        self.assertIsNone(pickup_order.driver_id)
        self.assertEqual(pickup_order.status, 'ready')


class StoreChatTests(TestCase):
    """Do'kon bilan chat: thread yaratish, ruxsat, xabar, API."""

    def setUp(self):
        self.owner = make_user('+998932000050')
        self.customer = make_user('+998932000051')
        self.stranger = make_user('+998932000052')
        self.store = Store.objects.create(owner=self.owner, name='Chat shop')

    def test_customer_starts_thread(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('delivery:store_chat_start', args=[self.store.pk]))
        self.assertTrue(
            StoreChatThread.objects.filter(store=self.store, customer=self.customer).exists())

    def test_stranger_cannot_view_thread(self):
        thread = StoreChatThread.objects.create(store=self.store, customer=self.customer)
        self.client.force_login(self.stranger)
        resp = self.client.get(reverse('delivery:store_chat_thread', args=[thread.id]))
        self.assertEqual(resp.status_code, 302)  # ruxsat yo'q — redirect

    def test_message_send_notifies_owner(self):
        from delivery.chat import get_or_create_thread, create_message
        from notifications.models import Notification
        thread = get_or_create_thread(self.store, self.customer)
        create_message(thread, self.customer, 'Salom')
        self.assertTrue(Notification.objects.filter(recipient=self.owner).exists())

    def test_chat_api_send_and_history(self):
        from rest_framework.test import APIClient
        api = APIClient()
        api.force_authenticate(self.customer)
        start = api.post(reverse('api:store-chat-start', args=[self.store.pk]))
        self.assertEqual(start.status_code, 201)
        tid = start.data['id']
        send = api.post(reverse('api:store-chat-thread', args=[tid]),
                        {'text': 'Bormi?'}, format='json')
        self.assertEqual(send.status_code, 201)
        hist = api.get(reverse('api:store-chat-thread', args=[tid]))
        self.assertEqual(hist.status_code, 200)
        self.assertEqual(len(hist.data['messages']), 1)
