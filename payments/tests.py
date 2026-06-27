"""Payme / Click to'lov shlyuzi testlari.

    python manage.py test payments
"""
import base64
import hashlib
import json

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import User
from delivery.models import Order
from .models import Transaction

PAYME_KEY = 'test_merchant_key'
CLICK_SECRET = 'test_secret'


def make_order(user, total=10000):
    return Order.objects.create(
        user=user, full_name='Test', phone='+998901234567', address='Samarqand',
        subtotal=total, delivery_fee=0, total=total,
        status='pending', payment_method='card', payment_status='unpaid',
    )


@override_settings(PAYME_MERCHANT_KEY=PAYME_KEY, PAYME_MERCHANT_ID='merchant1')
class PaymeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone='+998900000010', password='x', is_active=True)
        self.order = make_order(self.user, 10000)
        self.client = APIClient()
        self.url = reverse('payments:payme_callback')
        auth = base64.b64encode(f'Paycom:{PAYME_KEY}'.encode()).decode()
        self.auth = f'Basic {auth}'

    def _rpc(self, method, params, auth=None):
        return self.client.post(
            self.url, {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params},
            format='json', HTTP_AUTHORIZATION=self.auth if auth is None else auth)

    def test_auth_required(self):
        r = self._rpc('CheckPerformTransaction',
                      {'amount': 1000000, 'account': {'order_id': str(self.order.id)}},
                      auth='Basic xxx')
        self.assertEqual(r.json()['error']['code'], -32504)

    def test_check_perform_ok(self):
        r = self._rpc('CheckPerformTransaction',
                      {'amount': 1000000, 'account': {'order_id': str(self.order.id)}})
        self.assertEqual(r.json()['result'], {'allow': True})

    def test_check_perform_wrong_amount(self):
        r = self._rpc('CheckPerformTransaction',
                      {'amount': 999, 'account': {'order_id': str(self.order.id)}})
        self.assertEqual(r.json()['error']['code'], -31001)

    def test_check_perform_not_found(self):
        import uuid
        r = self._rpc('CheckPerformTransaction',
                      {'amount': 1000000, 'account': {'order_id': str(uuid.uuid4())}})
        self.assertEqual(r.json()['error']['code'], -31050)

    def test_create_perform_marks_paid(self):
        acc = {'order_id': str(self.order.id)}
        c = self._rpc('CreateTransaction',
                      {'id': 'tx1', 'time': 1700000000000, 'amount': 1000000, 'account': acc})
        self.assertEqual(c.json()['result']['state'], 1)
        p = self._rpc('PerformTransaction', {'id': 'tx1'})
        self.assertEqual(p.json()['result']['state'], 2)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'paid')

    def test_cancel_after_perform_reverts(self):
        acc = {'order_id': str(self.order.id)}
        self._rpc('CreateTransaction',
                  {'id': 'tx2', 'time': 1700000000000, 'amount': 1000000, 'account': acc})
        self._rpc('PerformTransaction', {'id': 'tx2'})
        r = self._rpc('CancelTransaction', {'id': 'tx2', 'reason': 5})
        self.assertEqual(r.json()['result']['state'], -2)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'unpaid')

    def test_create_is_idempotent(self):
        acc = {'order_id': str(self.order.id)}
        params = {'id': 'tx3', 'time': 1700000000000, 'amount': 1000000, 'account': acc}
        a = self._rpc('CreateTransaction', params)
        b = self._rpc('CreateTransaction', params)
        self.assertEqual(a.json()['result']['transaction'], b.json()['result']['transaction'])
        self.assertEqual(Transaction.objects.filter(provider='payme').count(), 1)


@override_settings(CLICK_SECRET_KEY=CLICK_SECRET, CLICK_SERVICE_ID='1', CLICK_MERCHANT_ID='1')
class ClickTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone='+998900000011', password='x', is_active=True)
        self.order = make_order(self.user, 10000)
        self.client = APIClient()
        self.mti = f'order~{self.order.id}'

    def _prep_sign(self, p):
        raw = (p['click_trans_id'] + p['service_id'] + CLICK_SECRET + p['merchant_trans_id']
               + p['amount'] + p['action'] + p['sign_time'])
        return hashlib.md5(raw.encode()).hexdigest()

    def _comp_sign(self, p):
        raw = (p['click_trans_id'] + p['service_id'] + CLICK_SECRET + p['merchant_trans_id']
               + p['merchant_prepare_id'] + p['amount'] + p['action'] + p['sign_time'])
        return hashlib.md5(raw.encode()).hexdigest()

    def test_full_prepare_complete_flow(self):
        prep = {
            'click_trans_id': '555', 'service_id': '1', 'click_paydoc_id': '9',
            'merchant_trans_id': self.mti, 'amount': '10000', 'action': '0',
            'sign_time': '2024-01-01 00:00:00',
        }
        prep['sign_string'] = self._prep_sign(prep)
        r1 = self.client.post(reverse('payments:click_prepare'), prep)
        body1 = r1.json()
        self.assertEqual(body1['error'], 0)
        prepare_id = body1['merchant_prepare_id']

        comp = {
            'click_trans_id': '555', 'service_id': '1',
            'merchant_trans_id': self.mti, 'merchant_prepare_id': prepare_id,
            'amount': '10000', 'action': '1', 'sign_time': '2024-01-01 00:00:00',
            'error': '0',
        }
        comp['sign_string'] = self._comp_sign(comp)
        r2 = self.client.post(reverse('payments:click_complete'), comp)
        self.assertEqual(r2.json()['error'], 0)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'paid')

    def test_bad_sign_rejected(self):
        prep = {
            'click_trans_id': '556', 'service_id': '1',
            'merchant_trans_id': self.mti, 'amount': '10000', 'action': '0',
            'sign_time': '2024-01-01 00:00:00', 'sign_string': 'wrong',
        }
        r = self.client.post(reverse('payments:click_prepare'), prep)
        self.assertEqual(r.json()['error'], -1)


class InitiatePaymentAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone='+998900000012', password='x', is_active=True)
        self.other = User.objects.create_user(phone='+998900000013', password='x', is_active=True)
        self.order = make_order(self.user, 25000)
        self.client = APIClient()

    @override_settings(PAYME_MERCHANT_ID='m1', CLICK_SERVICE_ID='1', CLICK_MERCHANT_ID='1')
    def test_initiate_returns_urls(self):
        self.client.force_authenticate(self.user)
        r = self.client.post(reverse('api:payments-initiate'),
                             {'target_type': 'order', 'target_id': str(self.order.id)},
                             format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['amount'], 25000)
        self.assertIn('payme_url', r.data)
        self.assertIn('click_url', r.data)

    def test_cannot_pay_others_order(self):
        self.client.force_authenticate(self.other)
        r = self.client.post(reverse('api:payments-initiate'),
                             {'target_type': 'order', 'target_id': str(self.order.id)},
                             format='json')
        self.assertEqual(r.status_code, 403)
