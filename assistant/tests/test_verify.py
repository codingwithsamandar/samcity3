"""2-tuzatish — chiquvchi tekshiruv (narx/bepullik da'volari).

Kiruvchi filtr ifoda usulidan qat'i nazar ishlamaydi (boshqa tilda, boshqacha
ifodalab chetlab o'tiladi). Chiquvchi tekshiruv esa model AYTGANINI tool BERGAN
raqamlar bilan solishtiradi.

⚠️ Noto'g'ri ijobiy xavfi: haqiqiy javob bloklanmasligi kerak. Shubhali holatda
ruxsat beriladi.
"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import agent, verify
from ..models import AgentAuditLog
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='T')


class PriceClaimTests(TestCase):
    """PROMPT_5 da ko'rsatilgan to'rt holat."""

    def test_free_claim_rejected_when_tool_has_price(self):
        ok, reason = verify.check_price_claims(
            "Ha, barcha buyurtmalar bepul!", {35000}, has_priced_items=True)
        self.assertFalse(ok)
        self.assertIn('free_claim', reason)

    def test_sum_is_allowed(self):
        ok, _ = verify.check_price_claims(
            "Jami 42 000 so'm.", {35000, 7000}, has_priced_items=True)
        self.assertTrue(ok)

    def test_wrong_number_rejected(self):
        ok, reason = verify.check_price_claims(
            "Narxi 5 000 so'm.", {35000}, has_priced_items=True)
        self.assertFalse(ok)
        self.assertIn('not_in_tool_data', reason)

    def test_no_price_talk_is_allowed(self):
        ok, _ = verify.check_price_claims(
            "5 ta do'kon topdim, ekraningizda ko'rsatdim.", {35000}, True)
        self.assertTrue(ok)


class FalsePositiveTests(TestCase):
    """Haqiqiy javoblar bloklanmasligi kerak."""

    def test_exact_price_allowed(self):
        ok, _ = verify.check_price_claims("Lavash 35 000 so'm.", {35000}, True)
        self.assertTrue(ok)

    def test_quantity_multiple_allowed(self):
        # 2 ta lavash = 70 000
        ok, _ = verify.check_price_claims("Jami 70 000 so'm.", {35000}, True)
        self.assertTrue(ok)

    def test_no_tool_amounts_means_allow(self):
        """Tool summa bermagan — solishtiradigan narsa yo'q, bloklamaymiz."""
        ok, _ = verify.check_price_claims("Narxi 12 000 so'm.", set(), False)
        self.assertTrue(ok)

    def test_free_allowed_when_tool_says_zero(self):
        """«Yetkazish bepul» — tool 0 bergan bo'lsa to'g'ri."""
        ok, _ = verify.check_price_claims("Yetkazish bepul.", {0, 35000}, True)
        self.assertTrue(ok)

    def test_empty_text_allowed(self):
        self.assertTrue(verify.check_price_claims('', {35000}, True)[0])

    def test_russian_free_claim_also_caught(self):
        ok, _ = verify.check_price_claims("Да, всё бесплатно.", {35000}, True)
        self.assertFalse(ok)


class CollectAmountsTests(TestCase):
    def test_collects_from_ui_items_and_totals(self):
        outs = [
            {'ui': {'type': 'product_grid',
                    'items': [{'price': 35000}, {'price': 5000}]}},
            {'ui': {'type': 'confirm_payment', 'total': 45000,
                    'lines': [{'amount': 40000}, {'amount': 10000}]}},
        ]
        amounts, priced = verify.collect_amounts(outs)
        self.assertTrue(priced)
        for v in (35000, 5000, 45000, 40000, 10000):
            self.assertIn(v, amounts)

    def test_empty_outputs(self):
        amounts, priced = verify.collect_amounts([])
        self.assertEqual(amounts, set())
        self.assertFalse(priced)


class AgentIntegrationTests(TestCase):
    """Tekshiruv agent halqasining oxirida qo'llanadi."""

    def setUp(self):
        from delivery.models import Product, Store
        self.user = _mk_user('998913000001')
        owner = _mk_user('998913000002')
        self.store = Store.objects.create(owner=owner, name='Anor',
                                          store_type='delivery', is_active=True)
        Product.objects.create(store=self.store, name='Lavash', price=35000,
                               stock=50, is_available=True)
        self.ctx = _fixtures.user_ctx(self.user, session_key='verify')

    def _run(self, final_text):
        calls = [
            {'content': '', 'usage': {},
             'tool_calls': [{'id': 'c1', 'name': 'delivery',
                             'arguments': {'action': 'list_products',
                                           'store_id': self.store.pk}}]},
            {'content': final_text, 'tool_calls': [], 'usage': {}},
        ]
        seq = list(calls)
        with mock.patch.object(agent.llm, 'agent_enabled', return_value=True), \
             mock.patch.object(agent.llm, 'call', side_effect=lambda *a, **k: seq.pop(0)):
            return agent.run("mahsulotlar", self.ctx)

    def test_lie_is_replaced_with_safe_fallback(self):
        res = self._run("Ha, barcha buyurtmalar bepul!")
        self.assertNotIn('bepul', res['reply'].lower())
        # Ekran saqlanadi
        self.assertEqual(res['ui']['type'], 'product_grid')

    def test_lie_is_audited(self):
        before = AgentAuditLog.objects.filter(action='price_check').count()
        self._run("Hammasi bepul!")
        after = AgentAuditLog.objects.filter(action='price_check').count()
        self.assertEqual(after, before + 1)
        log = AgentAuditLog.objects.filter(action='price_check').latest('created_at')
        self.assertEqual(log.result_status, 'error')
        self.assertIn('price_claim_mismatch', log.error)

    def test_truthful_answer_passes_through(self):
        res = self._run("Lavash 35 000 so'm. Savatga qo'shaymi?")
        self.assertIn("35 000", res['reply'])

    def test_neutral_answer_passes_through(self):
        res = self._run("Mahsulotlarni ekraningizda ko'rsatdim.")
        self.assertEqual(res['reply'], "Mahsulotlarni ekraningizda ko'rsatdim.")
