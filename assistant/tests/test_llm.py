"""llm.py sof yordamchilari — jumla ajratish (4.4) va fragment yig'ish (4.3).

Bular tarmoqsiz (API kalitisiz) ishlaydi.
"""

from unittest import mock

from django.test import TestCase

from .. import llm, prompts


class _FakeResp:
    """urlopen o'rniga — tarmoqqa chiqmasdan javob qaytaradi."""

    def __init__(self, body=b'{"choices":[{"message":{"content":"ok"}}]}'):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._body


class UserAgentTests(TestCase):
    """⚠️ Cloudflare orqasidagi provayderlar (Groq, OpenRouter) `urllib` ning
    standart "Python-urllib/3.x" imzosini bot deb bloklaydi (HTTP 403, xato 1010).
    Bu ishlab chiqarishga ham tegishli — Render'dan chiqishda ham shu bo'lardi.
    """

    def _capture(self, fn):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured['req'] = req
            return _FakeResp()

        with mock.patch('urllib.request.urlopen', fake_urlopen):
            fn()
        return captured.get('req')

    def test_http_json_sends_user_agent(self):
        req = self._capture(
            lambda: llm._http_json('https://example.test/v1', {'a': 1},
                                   {'Authorization': 'Bearer k'}, 5))
        ua = req.get_header('User-agent')
        self.assertTrue(ua, "User-Agent sarlavhasi umuman yo'q")
        self.assertNotIn('Python-urllib', ua)

    def test_user_agent_configurable_via_env(self):
        with mock.patch.dict('os.environ', {'AI_USER_AGENT': 'MyBot/9.9'}):
            req = self._capture(
                lambda: llm._http_json('https://example.test/v1', {}, {}, 5))
        self.assertEqual(req.get_header('User-agent'), 'MyBot/9.9')

    def test_openai_path_has_user_agent(self):
        with mock.patch.dict('os.environ', {'AI_API_KEY': 'k', 'AI_PROVIDER': 'openai'}):
            req = self._capture(lambda: llm.call([{'role': 'user', 'content': 'x'}]))
        self.assertNotIn('Python-urllib', req.get_header('User-agent'))

    def test_gemini_path_also_has_user_agent(self):
        """Gemini ham `_http_json` orqali ketadi — UA undan ham o'tishi shart."""
        with mock.patch.dict('os.environ', {'AI_API_KEY': 'k', 'AI_PROVIDER': 'gemini'}):
            req = self._capture(lambda: llm.call([{'role': 'user', 'content': 'x'}]))
        self.assertIsNotNone(req, "Gemini so'rov yubormadi")
        self.assertNotIn('Python-urllib', req.get_header('User-agent'))

    def test_caller_header_still_applied(self):
        req = self._capture(
            lambda: llm._http_json('https://example.test/v1', {},
                                   {'Authorization': 'Bearer abc'}, 5))
        self.assertEqual(req.get_header('Authorization'), 'Bearer abc')


class SentenceSplitTests(TestCase):
    def test_basic_two_sentences(self):
        self.assertEqual(llm.split_sentences("Salom. Qandaysiz?"),
                         ["Salom.", "Qandaysiz?"])

    def test_number_with_space_not_split(self):
        # "35 000 so'm" — probelli son, bo'linmasin
        self.assertEqual(llm.split_sentences("Narxi 35 000 so'm"),
                         ["Narxi 35 000 so'm"])

    def test_decimal_not_split(self):
        self.assertEqual(llm.split_sentences("Masofa 8.5 km"), ["Masofa 8.5 km"])

    def test_time_not_split(self):
        self.assertEqual(llm.split_sentences("Ish vaqti soat 14.30 gacha"),
                         ["Ish vaqti soat 14.30 gacha"])

    def test_abbreviation_not_split(self):
        # "va h.k." o'rtada jumlani buzmasligi kerak
        self.assertEqual(len(llm.split_sentences("Non, suv va h.k. bor")), 1)

    def test_ordinal_not_split(self):
        self.assertEqual(llm.split_sentences("2-chi do'kon"), ["2-chi do'kon"])

    def test_url_not_split(self):
        self.assertEqual(llm.split_sentences("Manzil t.me/samcity da"),
                         ["Manzil t.me/samcity da"])

    def test_exclamation_and_question(self):
        self.assertEqual(llm.split_sentences("Zo'r! Nima olasiz?"),
                         ["Zo'r!", "Nima olasiz?"])


class SentenceStreamerTests(TestCase):
    def test_streams_complete_sentences(self):
        s = llm.SentenceStreamer()
        out = []
        out += s.feed("Birinchi jumla. Ikkinchi")
        out += s.feed(" jumla. Uchi")
        out += s.flush()
        self.assertEqual(out, ["Birinchi jumla.", "Ikkinchi jumla.", "Uchi"])

    def test_no_premature_split_on_number(self):
        s = llm.SentenceStreamer()
        out = []
        out += s.feed("Jami 42 ")
        out += s.feed("000 so'm.")
        out += s.flush()
        self.assertEqual(out, ["Jami 42 000 so'm."])


class AssembleToolCallsTests(TestCase):
    def test_fragments_joined_as_text(self):
        # Oqim bo'laklari — name va arguments bo'lak-bo'lak keladi
        chunks = [
            {'index': 0, 'id': 'call_1', 'function': {'name': 'deliv', 'arguments': '{"act'}},
            {'index': 0, 'function': {'name': 'ery', 'arguments': 'ion":"ca'}},
            {'index': 0, 'function': {'name': '', 'arguments': 'rt_add"}'}},
        ]
        calls = llm.assemble_tool_calls(chunks)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['name'], 'delivery')
        self.assertEqual(calls[0]['arguments'], {'action': 'cart_add'})

    def test_bad_json_becomes_empty_dict(self):
        chunks = [{'index': 0, 'function': {'name': 'x', 'arguments': '{not json'}}]
        calls = llm.assemble_tool_calls(chunks)
        self.assertEqual(calls[0]['arguments'], {})

    def test_multiple_indices(self):
        chunks = [
            {'index': 0, 'function': {'name': 'a', 'arguments': '{}'}},
            {'index': 1, 'function': {'name': 'b', 'arguments': '{}'}},
        ]
        calls = llm.assemble_tool_calls(chunks)
        self.assertEqual([c['name'] for c in calls], ['a', 'b'])


class PromptCacheOrderTests(TestCase):
    """Xabar tartibi statik → dinamik bo'lishi SHART (kesh uchun)."""

    def test_static_first_dynamic_after(self):
        msgs = prompts.build_messages("salom", voice=False)
        self.assertEqual(msgs[0]['role'], 'system')
        self.assertEqual(msgs[0]['content'], prompts.STATIC_PROMPT)
        self.assertEqual(msgs[-1]['role'], 'user')

    def test_static_prompt_has_no_time(self):
        # Vaqt STATIC_PROMPT ichida BO'LMASLIGI kerak (kesh buzilmasin)
        self.assertNotIn('JORIY VAQT', prompts.STATIC_PROMPT)

    def test_dynamic_context_has_time(self):
        ctx = prompts.build_dynamic_context()
        self.assertIn('JORIY VAQT', ctx)

    def test_max_tokens_voice_shorter(self):
        self.assertLess(prompts.max_tokens_for(voice=True),
                        prompts.max_tokens_for(voice=False))
