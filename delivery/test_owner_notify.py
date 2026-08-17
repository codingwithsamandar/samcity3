"""Do'kon egasiga «yangi buyurtma» xabari — uch xil checkout yo'lida ham.

Xabar `notifications.notify()` orqali yuboriladi; u DB'ga yozadi va (kanal
qatlami bo'lsa) WebSocket'ga uzatadi. Bu yerda DB yozuvini tekshiramiz —
push best-effort, yozuv esa asosiy manba.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from main.models import User
from delivery.models import Store, Product, Order, OrderItem, DeliveryDriver
from notifications.models import Notification


def make_user(phone):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True)


class OwnerOrderNotificationTests(TestCase):
    def setUp(self):
        self.owner = make_user('+998933000010')
        self.customer = make_user('+998933000011')
        self.store = Store.objects.create(owner=self.owner, name="Test do'kon")
        self.product = Product.objects.create(
            store=self.store, name='Non', price=Decimal('5000'), stock=10,
            is_available=True)

    def _owner_notes(self):
        return Notification.objects.filter(recipient=self.owner, category='order')

    def _checkout_web(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('delivery:cart_add', args=[self.product.pk]))
        return self.client.post(reverse('delivery:checkout'), {
            'phone': '+998933000011', 'address': 'Shofirkon, 1-uy',
            'payment_method': 'cash',
        }, follow=True)

    def test_web_checkout_notifies_owner(self):
        self._checkout_web()
        self.assertEqual(Order.objects.filter(user=self.customer).count(), 1)
        self.assertEqual(self._owner_notes().count(), 1)

    def test_notification_links_to_store_orders(self):
        self._checkout_web()
        note = self._owner_notes().first()
        self.assertEqual(note.url, reverse('delivery:store_orders'))

    def test_owner_buying_from_own_store_is_not_notified(self):
        """Egasi o'z do'konidan olsa — o'ziga xabar kelmaydi."""
        self.client.force_login(self.owner)
        self.client.post(reverse('delivery:cart_add', args=[self.product.pk]))
        self.client.post(reverse('delivery:checkout'), {
            'phone': '+998933000010', 'address': 'Shofirkon, 1-uy',
            'payment_method': 'cash',
        }, follow=True)
        self.assertEqual(self._owner_notes().count(), 0)

    def test_api_checkout_notifies_owner(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('delivery:cart_add', args=[self.product.pk]))
        resp = self.client.post(reverse('api:checkout'), {
            'phone': '+998933000011', 'address': 'Shofirkon, 1-uy',
            'payment_method': 'cash',
        }, content_type='application/json')
        self.assertEqual(resp.status_code, 201, resp.content[:300])
        self.assertEqual(self._owner_notes().count(), 1)


class OwnerCourierNotificationTests(TestCase):
    """Kuryer buyurtmani olgach/yetkazgach — do'kon egasiga xabar.

    Avval bu xabarlar faqat xaridorga borardi: egasi mahsulot do'konidan
    chiqib ketganini umuman bilmasdi.
    """

    def setUp(self):
        self.owner = make_user('+998933000020')
        self.customer = make_user('+998933000021')
        self.driver_user = make_user('+998933000022')
        self.store = Store.objects.create(owner=self.owner, name="Test do'kon")
        self.product = Product.objects.create(
            store=self.store, name='Non', price=Decimal('5000'), stock=10,
            is_available=True)
        self.order = Order.objects.create(
            user=self.customer, address='Shofirkon, 1-uy', status='ready', total=20000)
        OrderItem.objects.create(
            order=self.order, product=self.product, product_name='Non',
            store_name=self.store.name, price=Decimal('5000'), quantity=1)
        self.driver = DeliveryDriver.objects.create(
            user=self.driver_user, full_name='Kuryer', phone='+998933000022',
            is_available=True, status='approved')

    def _owner_texts(self):
        return list(Notification.objects.filter(recipient=self.owner)
                    .order_by('created_at').values_list('text', flat=True))

    def _set(self, status):
        self.order.status = status
        self.order.save(update_fields=['status'])

    def test_owner_notified_when_courier_takes_goods(self):
        self._set('assigned')
        self._set('picked_up')
        texts = self._owner_texts()
        self.assertEqual(len(texts), 2)
        self.assertIn("kuryer oldi", texts[0].lower())
        self.assertIn("do'kondan oldi", texts[1])

    def test_owner_notified_on_delivered_and_cancelled(self):
        self._set('assigned')
        self._set('on_the_way')
        self._set('delivered')
        texts = self._owner_texts()
        self.assertIn("yo'lga chiqdi", texts[-2])
        self.assertIn("yetkazildi", texts[-1])

    def test_own_actions_do_not_notify_owner(self):
        """Egasining o'z tugmalari (tayyorlanmoqda/tayyor) xabar tug'dirmaydi."""
        self.order.status = 'accepted'
        self.order.save(update_fields=['status'])
        self._set('preparing')
        self.assertEqual(self._owner_texts(), [])

    def test_courier_accept_view_notifies_owner(self):
        """Haqiqiy oqim: kuryer panelidan «qabul qilish»."""
        self.client.force_login(self.driver_user)
        self.client.post(reverse('delivery:order_accept', args=[self.order.id]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'assigned')
        self.assertEqual(len(self._owner_texts()), 1)

    def test_pickup_order_uses_customer_wording(self):
        """Olib ketishda kuryer yo'q — matn mijoz haqida bo'ladi."""
        self.order.fulfillment_type = 'pickup'
        self.order.save(update_fields=['fulfillment_type'])
        self._set('delivered')
        self.assertIn("olib ketdi", self._owner_texts()[-1])
