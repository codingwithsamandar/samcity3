"""registry.py testlari — parametr tekshiruvi, dispatch, LLM sxemasi.

Muhim: dispatch HECH QACHON istisno tashlamaydi — noto'g'ri kirish ham aniq
{ok: False, ...} lug'ati bilan qaytadi (500 emas).
"""

from django.test import TestCase

from .. import registry
from . import _fixtures  # noqa: F401 — test tool'larini ro'yxatga oladi


class ParamValidationTests(TestCase):
    def test_unknown_action_is_clear_error_not_500(self):
        res = registry.dispatch('delivery', 'nope_action', {}, _fixtures.anon_ctx())
        self.assertFalse(res['ok'])
        self.assertEqual(res['result_status'], 'error')
        self.assertIn('reply', res)

    def test_missing_required_param(self):
        res = registry.dispatch('delivery', 't_echo', {'y': 'salom'}, _fixtures.anon_ctx())
        self.assertFalse(res['ok'])
        self.assertEqual(res['result_status'], 'error')

    def test_wrong_type_is_clear_error(self):
        res = registry.dispatch('delivery', 't_echo', {'x': 'abc'}, _fixtures.anon_ctx())
        self.assertFalse(res['ok'])
        self.assertEqual(res['result_status'], 'error')

    def test_extra_param_rejected(self):
        res = registry.dispatch('delivery', 't_echo',
                                {'x': 1, 'zzz': 9}, _fixtures.anon_ctx())
        self.assertFalse(res['ok'])
        self.assertIn('Ortiqcha', res['reply'])

    def test_type_coercion_string_to_int(self):
        # int("5") → 5 — tool int qiymatni ko'radi
        res = registry.dispatch('delivery', 't_echo', {'x': '5'}, _fixtures.anon_ctx())
        self.assertTrue(res['ok'])
        self.assertEqual(res['data']['x'], 5)
        self.assertIsInstance(res['data']['x'], int)

    def test_success_returns_speech(self):
        res = registry.dispatch('delivery', 't_echo',
                                {'x': 2, 'y': 'ha'}, _fixtures.anon_ctx())
        self.assertTrue(res['ok'])
        self.assertEqual(res['speech'], '2-ha')


class LlmSchemaTests(TestCase):
    def test_build_llm_tools_valid_schema(self):
        tools = registry.build_llm_tools()
        self.assertTrue(tools)
        for t in tools:
            self.assertEqual(t['type'], 'function')
            fn = t['function']
            self.assertIn(fn['name'], registry.SECTIONS)
            p = fn['parameters']
            self.assertEqual(p['type'], 'object')
            # Har bo'limda 'action' majburiy va enum bilan cheklangan
            self.assertIn('action', p['required'])
            self.assertIn('enum', p['properties']['action'])
            self.assertTrue(p['properties']['action']['enum'])

    def test_schema_is_json_serializable(self):
        import json
        json.dumps(registry.build_llm_tools())  # istisno bo'lmasa — o'tadi

    def test_at_most_twelve_sections(self):
        # LLM ga 12 tadan ko'p bo'lim berilmasin (arxitektura qoidasi)
        tools = registry.build_llm_tools()
        self.assertLessEqual(len(tools), 12)


class ToolNamingSchemaTests(TestCase):
    """⛔ Groq server tomonda rad etgan xatoni qoplaydi:

        "attempted to call tool 'find_nearest' which was not in request.tools"

    Sabab: amallar ro'yxati FUNKSIYA tavsifida edi — model uni chaqiriladigan
    funksiyalar ro'yxati deb tushunib, `name` ga amal nomini yozardi.
    Yechim: amallar `action` parametrining tavsifiga ko'chirildi.
    """

    def _fn(self, name):
        for t in registry.build_llm_tools():
            if t['function']['name'] == name:
                return t['function']
        self.fail(f"'{name}' bo'limi sxemada yo'q")

    def test_function_names_are_sections_only(self):
        names = {t['function']['name'] for t in registry.build_llm_tools()}
        self.assertTrue(names.issubset(set(registry.SECTIONS)))
        # Amal nomlari HECH QACHON funksiya nomi bo'lmasin
        self.assertNotIn('find_nearest', names)
        self.assertNotIn('cart_add', names)

    def test_action_list_not_in_function_description(self):
        """Amallar funksiya tavsifida BO'LMASIN — model shundan adashadi."""
        fn = self._fn('places')
        self.assertNotIn('find_nearest', fn['description'])

    def test_action_list_is_in_action_param_description(self):
        fn = self._fn('places')
        self.assertIn('find_nearest', fn['parameters']['properties']['action']['description'])

    def test_function_description_states_the_name(self):
        fn = self._fn('delivery')
        self.assertIn("FUNKSIYA NOMI HAR DOIM 'delivery'", fn['description'])

    def test_action_has_enum(self):
        action = self._fn('delivery')['parameters']['properties']['action']
        self.assertIn('find_store', action['enum'])
        self.assertIn('propose_order', action['enum'])


class ParamEnumTests(TestCase):
    """Cheklangan parametrlar sxemada `enum` bo'lishi kerak — prozadagi
    ko'rsatma yetarli emas (model «dorixona» deb o'zbekcha uzatgan edi)."""

    def test_category_enum_present_and_canonical(self):
        fn = [t['function'] for t in registry.build_llm_tools()
              if t['function']['name'] == 'places'][0]
        enum = fn['parameters']['properties']['category'].get('enum')
        self.assertIsNotNone(enum, "category uchun enum yo'q")
        self.assertIn('pharmacy', enum)
        self.assertIn('hospital', enum)
        self.assertNotIn('dorixona', enum)   # kanonik inglizcha kalitlar

    def test_enum_matches_engine_categories(self):
        from ..engine import VALID_CATEGORIES
        fn = [t['function'] for t in registry.build_llm_tools()
              if t['function']['name'] == 'places'][0]
        self.assertEqual(set(fn['parameters']['properties']['category']['enum']),
                         set(VALID_CATEGORIES))

    def test_three_tuple_params_still_work(self):
        """Orqaga moslik: enum'siz (3 elementli) spetsifikatsiya buzilmasin."""
        spec = registry.get_tool('delivery', 't_echo')
        cleaned = registry.validate_params(spec, {'x': '3'})
        self.assertEqual(cleaned['x'], 3)
        fn = [t['function'] for t in registry.build_llm_tools()
              if t['function']['name'] == 'delivery'][0]
        self.assertNotIn('enum', fn['parameters']['properties']['x'])

    def test_param_parts_handles_both_shapes(self):
        self.assertEqual(registry.param_parts(('int', True, 'd')),
                         ('int', True, 'd', None))
        self.assertEqual(registry.param_parts(('str', False, 'd', ['a', 'b'])),
                         ('str', False, 'd', ['a', 'b']))

    def test_enum_must_be_a_list(self):
        with self.assertRaises(ValueError):
            @registry.tool(section='places', action='t_bad_enum',
                           description='x', params={'p': ('str', False, 'd', 'notalist')})
            def _bad(ctx, p=None):
                return {}


class ParamErrorUnitTests(TestCase):
    """validate_params to'g'ridan-to'g'ri (dispatch'siz)."""

    def test_coerce_bad_int_raises_paramerror(self):
        spec = registry.get_tool('delivery', 't_echo')
        with self.assertRaises(registry.ParamError):
            registry.validate_params(spec, {'x': 'abc'})

    def test_coerce_ok(self):
        spec = registry.get_tool('delivery', 't_echo')
        cleaned = registry.validate_params(spec, {'x': '7', 'y': 5})
        self.assertEqual(cleaned['x'], 7)
        self.assertEqual(cleaned['y'], '5')  # str ga majburlanadi


class SectionSelectionTests(TestCase):
    """So'rovga qarab faqat kerakli bo'limlarni yuborish (token tejash).

    Asosiy shart: tanlash HECH QACHON agentni imkoniyatsiz qoldirmasin —
    noaniqlikda to'liq sxemaga qaytadi.
    """

    def test_keyword_picks_one_section(self):
        self.assertEqual(registry.select_sections('Sartaroshxona bron qil'),
                         ['booking'])

    def test_jobs_keywords(self):
        self.assertEqual(registry.select_sections('Ish qidiryapman, dasturchi'),
                         ['jobs'])

    def test_places_and_delivery_always_travel_together(self):
        """Chegarasi eng sirg'aluvchan juftlik — bittasi tanlansa ikkalasi ketadi."""
        for msg in ('Eng yaqin dorixona qayerda?', 'Lavash yeyishni xohlayman'):
            picked = registry.select_sections(msg)
            self.assertIn('places', picked, msg)
            self.assertIn('delivery', picked, msg)

    def test_unknown_message_falls_back_to_all(self):
        self.assertEqual(registry.select_sections('Salom'), list(registry.SECTIONS))

    def test_active_task_keeps_its_section(self):
        """«ha, tasdiqla» da kalit so'z yo'q — yagona ishora faol vazifa."""
        class _Task:
            goal = 'booking'
        self.assertEqual(registry.select_sections('Ha, tasdiqla', task=_Task()),
                         ['booking'])

    def test_history_gives_context(self):
        picked = registry.select_sections(
            'ikkinchisini', history=[{'role': 'user', 'content': 'lavash topib ber'}])
        self.assertIn('delivery', picked)

    def test_order_is_stable_for_cache(self):
        a = registry.select_sections('vakansiya va sartaroshxona')
        b = registry.select_sections('sartaroshxona va vakansiya')
        self.assertEqual(a, b)
        self.assertEqual(a, [s for s in registry.SECTIONS if s in a])

    def test_build_llm_tools_filters(self):
        names = {t['function']['name']
                 for t in registry.build_llm_tools(['booking', 'jobs'])}
        self.assertEqual(names, {'booking', 'jobs'})

    def test_build_llm_tools_without_arg_is_unchanged(self):
        self.assertEqual(len(registry.build_llm_tools(None)),
                         len(registry.build_llm_tools()))

    def test_tools_for_never_returns_empty(self):
        """Tanlangan bo'limda amal bo'lmasa (o'chirilgan modul) — to'liq sxema."""
        self.assertTrue(registry.tools_for('Buxoroga taksi kerak'))
        self.assertTrue(registry.tools_for('Salom'))

    def test_tools_for_is_a_subset_of_full_schema(self):
        full = {t['function']['name'] for t in registry.build_llm_tools()}
        picked = {t['function']['name']
                  for t in registry.tools_for('Sartaroshxona bron qil')}
        self.assertTrue(picked.issubset(full))
        self.assertTrue(picked)


class SchemaCompactnessTests(TestCase):
    """Sxema qisqartirildi — qayta shishib ketmasin (har token har chaqiruvda ketadi)."""

    def _chars(self, tools):
        import json
        return len(json.dumps(tools, ensure_ascii=False))

    def test_full_schema_stays_small(self):
        # ~3200 token (4 belgi ≈ 1 token). Boshlang'ich holat ~4000 edi.
        self.assertLess(self._chars(registry.build_llm_tools()), 14000)

    def test_repeated_param_description_is_not_duplicated(self):
        """Bir xil tavsif takrorlanmaydi — amal nomlari bitta qavsga yig'iladi."""
        fn = [t['function'] for t in registry.build_llm_tools(['jobs'])][0]
        phone = fn['parameters']['properties']['phone']['description']
        self.assertEqual(phone.count('aloqa telefoni'), 1)
        self.assertIn('post_job', phone)
        self.assertIn('post_resume', phone)

    def test_mutating_actions_are_still_marked(self):
        """Qisqartirish tasdiq belgisini yo'qotmasin — bu xavfsizlik ishorasi."""
        desc = [t['function'] for t in registry.build_llm_tools(['delivery'])][0][
            'parameters']['properties']['action']['description']
        self.assertIn('tasdiq talab qiladi', desc)   # sarlavhadagi izoh
        self.assertIn('propose_order⚠️', desc)

    def test_required_params_still_listed_per_action(self):
        desc = [t['function'] for t in registry.build_llm_tools(['delivery'])][0][
            'parameters']['properties']['action']['description']
        self.assertIn('propose_order⚠️ [address]', desc)
