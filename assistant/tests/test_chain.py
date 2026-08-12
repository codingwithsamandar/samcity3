"""Ko'p navbatli zanjir — model ID'larni navbatlar orasida BILADIMI.

Bu testlar aynan o'sha kamchilikni qoplaydi: `agent.py` dagi «erta qaytish»
optimizatsiyasi tufayli tool natijasi suhbatga kirmaydi, shuning uchun oxirgi
ro'yxat `AgentTask.last_ui_ref` orqali dinamik kontekstga qo'shiladi.

Bu yerda LLM mock qilinadi, lekin MODEL KO'RADIGAN MATN tekshiriladi — ya'ni
haqiqiy model ham aynan shu ma'lumotni oladi.
"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import agent, prompts, registry
from ..models import AgentTask, SelectionSet
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='Test')


def _tool_call(action, **params):
    return {'content': '', 'usage': {},
            'tool_calls': [{'id': 'c1', 'name': 'delivery',
                            'arguments': {'action': action, **params}}]}


class SelectionRememberedTests(TestCase):
    """Ro'yxat chiqarilganda faol vazifaga bog'lanadi."""

    def setUp(self):
        from delivery.models import Product, Store
        self.user = _mk_user('998908000001')
        owner = _mk_user('998908000002')
        self.store = Store.objects.create(owner=owner, name='Anor Fast Food',
                                          store_type='delivery', is_active=True)
        self.lavash = Product.objects.create(store=self.store, name='Lavash',
                                             price=35000, stock=10, is_available=True)
        self.ctx = _fixtures.user_ctx(self.user, session_key='chain')

    def test_find_store_creates_task_and_remembers_ref(self):
        res = registry.dispatch('delivery', 'find_store', {'query': 'lavash'}, self.ctx)
        ref = res['ui']['ref']
        task = AgentTask.objects.get(user=self.user, status='active')
        self.assertEqual(task.last_ui_ref, ref)
        self.assertEqual(SelectionSet.objects.get(ref=ref).task_id, task.id)

    def test_second_list_replaces_ref(self):
        registry.dispatch('delivery', 'find_store', {'query': 'lavash'}, self.ctx)
        res2 = registry.dispatch('delivery', 'list_products',
                                 {'store_id': self.store.pk}, self.ctx)
        task = AgentTask.objects.filter(user=self.user, status='active').first()
        self.assertEqual(task.last_ui_ref, res2['ui']['ref'])


class ModelSeesIdsTests(TestCase):
    """⛔→✅ Model keyingi navbatda store_id/product_id ni KO'RADI."""

    def setUp(self):
        from delivery.models import Product, Store
        self.user = _mk_user('998908000010')
        owner = _mk_user('998908000011')
        self.store = Store.objects.create(owner=owner, name='Anor Fast Food',
                                          store_type='delivery', is_active=True)
        self.milano = Store.objects.create(owner=owner, name='Milano Pizza',
                                           store_type='delivery', is_active=True)
        Product.objects.create(store=self.store, name='Lavash', price=35000,
                               stock=10, is_available=True)
        Product.objects.create(store=self.milano, name='Pizza', price=55000,
                               stock=5, is_available=True)
        self.ctx = _fixtures.user_ctx(self.user, session_key='chain2')

    def _next_turn_prompt(self, message):
        """Keyingi navbatda modelga beriladigan DINAMIK kontekst.

        Ataylab faqat dinamik qism tekshiriladi: STATIC_PROMPT ning o'zida
        `[OXIRGI RO'YXAT]` va `[TANLOV]` belgilari qoida sifatida tilga olingan,
        shuning uchun butun promptdan qidirish yolg'on natija berardi.
        """
        from .. import task as task_mod
        task = task_mod.active_task(self.ctx)
        return prompts.build_dynamic_context(self.ctx, task, message=message)

    def test_store_ids_visible_next_turn(self):
        registry.dispatch('delivery', 'find_store', {'query': 'lavash'}, self.ctx)
        blob = self._next_turn_prompt("ikkinchisini tanladim")
        self.assertIn(f'store_id={self.store.pk}', blob)
        self.assertIn('Anor Fast Food', blob)

    def test_product_ids_visible_next_turn(self):
        registry.dispatch('delivery', 'list_products',
                          {'store_id': self.store.pk}, self.ctx)
        from delivery.models import Product
        p = Product.objects.get(store=self.store, name='Lavash')
        blob = self._next_turn_prompt("2 ta savatga qo'sh")
        self.assertIn(f'product_id={p.pk}', blob)

    def test_ordinal_selection_resolved_without_llm(self):
        """«ikkinchisini» — selection.resolve LLM'siz yechadi va ID beradi."""
        registry.dispatch('delivery', 'find_store', {'query': 'a'}, self.ctx)
        blob = self._next_turn_prompt("ikkinchisini tanladim")
        self.assertIn('[TANLOV]', blob)

    def test_name_selection_resolved(self):
        registry.dispatch('delivery', 'find_store', {'query': 'a'}, self.ctx)
        blob = self._next_turn_prompt("Milano ni tanladim")
        self.assertIn('[TANLOV]', blob)
        self.assertIn('Milano Pizza', blob)

    def test_no_selection_hint_for_unrelated_message(self):
        registry.dispatch('delivery', 'find_store', {'query': 'a'}, self.ctx)
        blob = self._next_turn_prompt("bugun ob-havo qanday")
        self.assertNotIn('[TANLOV]', blob)

    def test_no_list_block_before_any_search(self):
        blob = self._next_turn_prompt("salom")
        self.assertNotIn("[OXIRGI RO'YXAT]", blob)


class RepeatGuardTests(TestCase):
    """4.6 — model bir xil tool'ni takrorlasa, ikkinchi marta BAJARILMAYDI.

    `cart_add` ui qaytarmaydi → halqa davom etadi → adashgan model o'sha
    chaqiruvni takrorlashi mumkin. Bu «ikki marta savatga qo'shish» degani.
    """

    def setUp(self):
        from delivery.models import Product, Store
        self.user = _mk_user('998908000030')
        owner = _mk_user('998908000031')
        store = Store.objects.create(owner=owner, name='Anor', store_type='delivery',
                                     is_active=True)
        self.lavash = Product.objects.create(store=store, name='Lavash', price=35000,
                                             stock=50, is_available=True)
        self.ctx = _fixtures.user_ctx(self.user, session_key='repeat')

    def test_identical_call_executed_once(self):
        from delivery.models import get_active_cart
        # Model har safar AYNAN bir xil chaqiruvni qaytaradi (adashgan model)
        same = _tool_call('cart_add', product_id=self.lavash.pk, qty=2)
        with mock.patch.object(agent.llm, 'agent_enabled', return_value=True), \
             mock.patch.object(agent.llm, 'call', return_value=same):
            agent.run("2 ta lavash qo'sh", self.ctx)
        # 5 qadam emas — BITTA marta qo'shilgan
        self.assertEqual(get_active_cart(self.user).get_total_quantity(), 2)

    def test_repeated_propose_creates_one_pending(self):
        from ..models import PendingAction
        from delivery.models import CartItem, get_active_cart
        cart = get_active_cart(self.user)
        CartItem.objects.create(cart=cart, product=self.lavash, quantity=1)
        same = _tool_call('propose_order', address="Navoiy ko'chasi 12-uy")
        with mock.patch.object(agent.llm, 'agent_enabled', return_value=True), \
             mock.patch.object(agent.llm, 'call', return_value=same):
            agent.run("buyurtma qil", self.ctx)
        self.assertEqual(PendingAction.objects.filter(user=self.user).count(), 1)


class FullChainTests(TestCase):
    """To'liq oqim: do'kon → mahsulot → savat → buyurtma (section 9 qabul mezoni).

    Har navbatda model FAQAT dinamik kontekstdan olgan ID bilan ishlaydi —
    ya'ni haqiqiy modelda ham bajarilishi mumkin bo'lgan yo'l.
    """

    def setUp(self):
        from delivery.models import Product, Store
        self.user = _mk_user('998908000020')
        owner = _mk_user('998908000021')
        self.store = Store.objects.create(owner=owner, name='Anor Fast Food',
                                          store_type='delivery', is_active=True)
        self.lavash = Product.objects.create(store=self.store, name='Lavash',
                                             price=35000, stock=10, is_available=True)
        self.ctx = _fixtures.user_ctx(self.user, session_key='chain3')

    def _turn(self, message, llm_response):
        """Bitta navbat: modelga nima ko'rinishini qaytaradi + agent javobi."""
        seen = {}

        def fake_call(messages, **kw):
            seen['blob'] = "\n".join(m.get('content') or '' for m in messages)
            return llm_response

        with mock.patch.object(agent.llm, 'agent_enabled', return_value=True), \
             mock.patch.object(agent.llm, 'call', side_effect=fake_call):
            out = agent.run(message, self.ctx)
        return seen.get('blob', ''), out

    def test_full_order_chain_works(self):
        from delivery.models import Order

        # 1-navbat: do'kon qidirish
        _, r1 = self._turn("lavash bor do'konlarni ko'rsat",
                           _tool_call('find_store', query='lavash'))
        self.assertEqual(r1['ui']['type'], 'card_list')

        # 2-navbat: model store_id ni KONTEKSTDAN ko'radi
        blob2, r2 = self._turn("birinchisining mahsulotlarini ko'rsat",
                               _tool_call('list_products', store_id=self.store.pk))
        self.assertIn(f'store_id={self.store.pk}', blob2)
        self.assertEqual(r2['ui']['type'], 'product_grid')

        # 3-navbat: model product_id ni KONTEKSTDAN ko'radi
        blob3, _r3 = self._turn("2 ta savatga qo'sh",
                                _tool_call('cart_add', product_id=self.lavash.pk, qty=2))
        self.assertIn(f'product_id={self.lavash.pk}', blob3)
        from delivery.models import get_active_cart
        self.assertEqual(get_active_cart(self.user).get_total_quantity(), 2)

        # 4-navbat: buyurtma taklifi → tasdiq kartasi, buyurtma HALI yaratilmaydi
        _, r4 = self._turn("buyurtma qil", _tool_call('propose_order', address="Navoiy ko'chasi 12-uy"))
        self.assertEqual(r4['ui']['type'], 'confirm_payment')
        self.assertEqual(r4['ui']['total'], 35000 * 2 + 10000)
        self.assertEqual(Order.objects.count(), 0)

        # 5-qadam: tasdiq (tugma orqali — LLM ishtirok etmaydi)
        from .. import confirm
        out = confirm.execute(r4['pending_id'], self.user)
        self.assertTrue(out['ok'])
        self.assertEqual(Order.objects.count(), 1)
