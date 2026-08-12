"""[SAVAT] bloki — model savatda nima borligini ko'rishi kerak (smoke 14-holat).

Busiz «buyurtma qil» so'roviga model «nima buyurtma qilay?» deb qaytardi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import prompts
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='T')


class CartBlockTests(TestCase):
    def setUp(self):
        from delivery.models import Product, Store
        self.user = _mk_user('998910000001')
        owner = _mk_user('998910000002')
        self.store = Store.objects.create(owner=owner, name='Anor',
                                          store_type='delivery', is_active=True)
        self.lavash = Product.objects.create(store=self.store, name='Lavash (katta)',
                                             price=35000, stock=50, is_available=True)
        self.choy = Product.objects.create(store=self.store, name="Ko'k choy",
                                           price=5000, stock=50, is_available=True)
        self.ctx = _fixtures.user_ctx(self.user, session_key='cart')

    def _ctxt(self):
        return prompts.build_dynamic_context(self.ctx, None)

    def _add(self, product, qty):
        from delivery.models import CartItem, get_active_cart
        CartItem.objects.create(cart=get_active_cart(self.user),
                                product=product, quantity=qty)

    def test_empty_cart_adds_nothing(self):
        """Bo'sh savat — blok qo'shilmasin (token tejash)."""
        self.assertNotIn('[SAVAT]', self._ctxt())

    def test_cart_items_listed_with_total(self):
        self._add(self.lavash, 2)
        self._add(self.choy, 1)
        blob = self._ctxt()
        self.assertIn('[SAVAT]', blob)
        self.assertIn('Lavash (katta) × 2', blob)
        self.assertIn("Ko'k choy × 1", blob)
        self.assertIn('75 000', blob)          # 70 000 + 5 000

    def test_product_ids_included(self):
        """Savatdagi mahsulot ID'lari ham bo'lsin — model ular bilan ishlaydi."""
        self._add(self.lavash, 1)
        self.assertIn(f'product_id={self.lavash.pk}', self._ctxt())

    def test_anonymous_gets_no_cart_block(self):
        anon = _fixtures.anon_ctx(session_key='x')
        self.assertNotIn('[SAVAT]', prompts.build_dynamic_context(anon, None))

    def test_long_cart_is_truncated(self):
        from delivery.models import Product
        for i in range(13):
            p = Product.objects.create(store=self.store, name=f'Mahsulot {i}',
                                       price=1000, stock=10, is_available=True)
            self._add(p, 1)
        blob = self._ctxt()
        self.assertIn('va yana', blob)
        # 10 tadan ko'p qator bo'lmasin
        self.assertEqual(blob.count('  • '), prompts._CART_MAX_ITEMS)

    def test_cart_block_is_untrusted_user_message(self):
        """Savat — ISHONCHSIZ blokda (`role: user`), system'da EMAS.

        Mahsulot nomlari foydalanuvchi kiritgan kontent, shuning uchun ular
        system xabariga tushmasligi kerak (test_trust_boundary.py ga qara).
        """
        self._add(self.lavash, 1)
        self.assertNotIn('[SAVAT]', prompts.STATIC_PROMPT)
        msgs = prompts.build_messages('buyurtma qil', ctx=self.ctx)
        self.assertEqual(msgs[0]['content'], prompts.STATIC_PROMPT)

        systems = "\n".join(m['content'] for m in msgs if m['role'] == 'system')
        self.assertNotIn('[SAVAT]', systems)

        cart_msgs = [m for m in msgs
                     if m['role'] == 'user' and '[SAVAT]' in m['content']]
        self.assertEqual(len(cart_msgs), 1)
        self.assertIn('trusted="false"', cart_msgs[0]['content'])


class SectionBoundaryTests(TestCase):
    """3-tuzatish — places/delivery chegarasi tavsiflarda aniq bo'lsin."""

    def test_places_description_has_no_restaurant(self):
        from .. import registry
        self.assertNotIn('restoran', registry.SECTION_DESC['places'].lower())

    def test_delivery_description_mentions_food(self):
        from .. import registry
        desc = registry.SECTION_DESC['delivery'].lower()
        self.assertIn('ovqat', desc)
        self.assertIn('yeyishni', desc)

    def test_prompt_states_the_rule(self):
        self.assertIn('OVQAT so\'ralsa', prompts.STATIC_PROMPT)

    def test_places_tool_description_redirects_to_delivery(self):
        from .. import registry
        spec = registry.get_tool('places', 'find_nearest')
        self.assertIn('delivery.find_store', spec.description)


class VoiceRuleTests(TestCase):
    """Yangi qoida — LLM ekrandagi ro'yxatni ovozda sanamasin."""

    def test_screen_voice_rule_present(self):
        self.assertIn('EKRAN VA OVOZ ROLLARI', prompts.STATIC_PROMPT)
        self.assertIn('QAYTA SANAB BERMA', prompts.STATIC_PROMPT)
