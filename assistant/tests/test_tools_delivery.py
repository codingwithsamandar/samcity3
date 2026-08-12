"""tools/delivery.py — to'liq oqim (section 9 qabul mezoni).

find_store → list_products → cart_add → propose_order (tasdiq) → confirm → order.
Buyurtma FAQAT tasdiqdan keyin yaratiladi va ikki marta tasdiq → bitta buyurtma.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import confirm, guard, registry
from ..models import PendingAction
from . import _fixtures


# Kuryerga bo'sh manzil tushmasligi uchun propose_order manzilni TALAB qiladi.
ADDR = "Navoiy ko'chasi 12-uy, maktab yonida"


def _mk_user(phone, name='Mijoz'):
    return get_user_model().objects.create_user(phone=phone, password='x', name=name)


class DeliveryFlowTests(TestCase):
    def setUp(self):
        from delivery.models import Store, Product
        self.user = _mk_user('998903000001')
        self.owner = _mk_user('998903000002', name='Egasi')
        self.store = Store.objects.create(owner=self.owner, name='Anor Fast Food',
                                          store_type='delivery', is_active=True)
        self.lavash = Product.objects.create(store=self.store, name='Lavash',
                                             price=35000, stock=10, is_available=True)
        self.ctx = _fixtures.user_ctx(self.user)

    def test_find_store_by_product(self):
        res = registry.dispatch('delivery', 'find_store', {'query': 'lavash'}, self.ctx)
        self.assertTrue(res['ok'])
        self.assertEqual(res['ui']['type'], 'card_list')
        titles = [it['title'] for it in res['ui']['items']]
        self.assertIn('Anor Fast Food', titles)

    def test_list_products(self):
        res = registry.dispatch('delivery', 'list_products',
                                {'store_id': self.store.pk}, self.ctx)
        self.assertEqual(res['ui']['type'], 'product_grid')
        self.assertEqual(res['ui']['items'][0]['product_id'], self.lavash.pk)

    def test_cart_add(self):
        res = registry.dispatch('delivery', 'cart_add',
                                {'product_id': self.lavash.pk, 'qty': 2}, self.ctx)
        self.assertTrue(res['ok'])
        from delivery.models import get_active_cart
        cart = get_active_cart(self.user)
        self.assertEqual(cart.get_total_quantity(), 2)

    def test_cart_add_requires_auth(self):
        res = registry.dispatch('delivery', 'cart_add',
                                {'product_id': self.lavash.pk}, _fixtures.anon_ctx())
        self.assertFalse(res['ok'])
        self.assertEqual(res['result_status'], 'denied')

    def test_propose_then_confirm_creates_order(self):
        from delivery.models import Order
        registry.dispatch('delivery', 'cart_add',
                          {'product_id': self.lavash.pk, 'qty': 2}, self.ctx)
        res = registry.dispatch('delivery', 'propose_order',
                                 {'address': ADDR, 'note': 'eshik oldiga'}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')
        self.assertEqual(res['ui']['type'], 'confirm_payment')
        self.assertEqual(res['ui']['total'], 35000 * 2 + 10000)
        # BUYURTMA hali yaratilmagan
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(PendingAction.objects.get(id=res['pending_id']).status, 'pending')

        out = confirm.execute(res['pending_id'], self.user)
        self.assertTrue(out['ok'])
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.total, 35000 * 2 + 10000)
        self.assertEqual(order.payment_method, 'cash')
        self.assertEqual(order.note, 'eshik oldiga')
        # Stock kamaydi, savat tozalandi
        self.lavash.refresh_from_db()
        self.assertEqual(self.lavash.stock, 8)

    def test_double_confirm_one_order(self):
        from delivery.models import Order
        registry.dispatch('delivery', 'cart_add',
                          {'product_id': self.lavash.pk, 'qty': 1}, self.ctx)
        res = registry.dispatch('delivery', 'propose_order', {'address': ADDR}, self.ctx)
        pid = res['pending_id']
        confirm.execute(pid, self.user)
        confirm.execute(pid, self.user)
        self.assertEqual(Order.objects.count(), 1)  # idempotent

    def test_order_carries_address_to_courier(self):
        """Kuryer panelida manzil bo'sh chiqmasligi — regressiya testi."""
        from delivery.models import Order
        registry.dispatch('delivery', 'cart_add',
                          {'product_id': self.lavash.pk, 'qty': 1}, self.ctx)
        res = registry.dispatch('delivery', 'propose_order', {'address': ADDR}, self.ctx)
        self.assertIn(ADDR, str(res['ui']))          # tasdiq kartasida ko'rinadi
        confirm.execute(res['pending_id'], self.user)
        order = Order.objects.first()
        self.assertEqual(order.address, ADDR)
        self.assertEqual(order.fulfillment_type, 'delivery')

    def test_propose_without_address_refused(self):
        from delivery.models import Order
        registry.dispatch('delivery', 'cart_add',
                          {'product_id': self.lavash.pk, 'qty': 1}, self.ctx)
        for bad in ({}, {'address': ''}, {'address': 'uyim'}):
            res = registry.dispatch('delivery', 'propose_order', bad, self.ctx)
            self.assertFalse(res.get('ok'), bad)
            self.assertEqual(PendingAction.objects.count(), 0, bad)
            self.assertEqual(Order.objects.count(), 0, bad)

    def test_propose_empty_cart(self):
        res = registry.dispatch('delivery', 'propose_order', {'address': ADDR}, self.ctx)
        self.assertFalse(res['ok'])
        self.assertEqual(PendingAction.objects.count(), 0)


class AmountLimitFlowTests(TestCase):
    def setUp(self):
        from delivery.models import Store, Product
        self.user = _mk_user('998903000010')
        owner = _mk_user('998903000011')
        self.store = Store.objects.create(owner=owner, name='Qimmat do\'kon',
                                          store_type='delivery', is_active=True)
        # Bitta amal chegarasidan oshadigan narx
        self.pricey = Product.objects.create(
            store=self.store, name='Qimmat mahsulot',
            price=guard.LIMITS['single_amount'] + 1000, stock=5, is_available=True)
        self.ctx = _fixtures.user_ctx(self.user)

    def test_over_single_amount_blocked_no_pending(self):
        registry.dispatch('delivery', 'cart_add',
                          {'product_id': self.pricey.pk, 'qty': 1}, self.ctx)
        res = registry.dispatch('delivery', 'propose_order', {'address': ADDR}, self.ctx)
        self.assertFalse(res['ok'])
        self.assertEqual(res['result_status'], 'limited')
        self.assertEqual(PendingAction.objects.count(), 0)
