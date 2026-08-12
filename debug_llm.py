"""LLM ulanishini tekshirish — xato matnini OCHIQ ko'rsatadi.

Ishlatish:
    python debug_llm.py

`assistant/llm.py` xatolarni ataylab yutadi (chat oqimi buzilmasin uchun).
Bu skript esa aynan o'sha so'rovni yuboradi, lekin xatoni to'liq chiqaradi.
Uch bosqich: (1) sozlama, (2) tool'siz oddiy so'rov, (3) tool bilan.
"""

import json
import os
import sys
import urllib.error
import urllib.request

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sdev.settings')
django.setup()


def mask(key):
    if not key:
        return '(BO\'SH)'
    return f'{key[:7]}…{key[-4:]}  ({len(key)} belgi)'


# Cloudflare Python-urllib ning standart User-Agent'ini bot deb bloklaydi
# (xato 1010). Oddiy UA yuborilsa o'tadi.
UA = 'SamCity/1.0 (Django; +https://samcity.uz)'


def post(url, payload, headers, timeout=30, ua=UA):
    """So'rov yuboradi. (ok, data_yoki_xato_matni) qaytaradi."""
    hdrs = {'Content-Type': 'application/json', **headers}
    if ua:
        hdrs['User-Agent'] = ua
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode('utf-8'),
        headers=hdrs, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return False, f'HTTP {e.code} {e.reason}\n{body}'
    except urllib.error.URLError as e:
        return False, f'Tarmoq xatosi: {e.reason}'
    except Exception as e:  # noqa: BLE001
        return False, f'{type(e).__name__}: {e}'


def probe_user_agents(url, auth):
    """Qaysi User-Agent Cloudflare'dan o'tishini aniqlaydi."""
    print('\n' + '═' * 60)
    print('1.5) USER-AGENT SINOVI (Cloudflare 1010 tekshiruvi)')
    print('═' * 60)
    candidates = [
        (None, 'standart Python-urllib (UA yuborilmaydi)'),
        (UA, 'SamCity/1.0'),
        ('curl/8.4.0', 'curl'),
        ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
         '(KHTML, like Gecko) Chrome/126.0 Safari/537.36', 'Chrome (brauzer)'),
    ]
    payload = {'model': model, 'messages': [{'role': 'user', 'content': 'hi'}],
               'max_tokens': 5}
    working = []
    for ua, label in candidates:
        ok, res = post(url, payload, auth, timeout=20, ua=ua)
        if ok:
            print(f'  ✅ {label}')
            working.append(ua)
        else:
            first = str(res).splitlines()[0] if res else '?'
            code = ' (Cloudflare 1010)' if '1010' in str(res) else ''
            print(f'  ❌ {label} → {first}{code}')
    return working


# ── 1) Sozlama ───────────────────────────────────────────────────────────────
provider = os.environ.get('AI_PROVIDER', 'openai')
base_url = os.environ.get('AI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
api_key = os.environ.get('AI_API_KEY', '').strip()
model = os.environ.get('AI_MODEL', 'gpt-4o-mini').strip()

print('═' * 60)
print('1) SOZLAMA')
print('═' * 60)
print(f'AI_PROVIDER : {provider}')
print(f'AI_BASE_URL : {base_url}')
print(f'AI_MODEL    : {model}')
print(f'AI_API_KEY  : {mask(api_key)}')

if not api_key:
    print('\n❌ Kalit bo\'sh. .env dagi AI_API_KEY ni tekshiring.')
    sys.exit(1)
if api_key == 'BU_YERGA_YANGI_KALIT':
    print('\n❌ Kalit almashtirilmagan — .env da hali BU_YERGA_YANGI_KALIT turibdi.')
    sys.exit(1)

url = f'{base_url}/chat/completions'
auth = {'Authorization': f'Bearer {api_key}'}

working_uas = probe_user_agents(url, auth)
if not working_uas:
    print('\n❌ Hech qaysi User-Agent o\'tmadi.')
    print('   Demak muammo UA da emas — IP/mamlakat bloki yoki kalit xato.')
    print('   Tekshiring: brauzerda console.groq.com ochilyaptimi?')
    sys.exit(1)

UA = working_uas[0] if working_uas[0] else UA
print(f'\n→ Ishlatiladigan UA: {UA[:60]}')

# ── 2) Tool'siz oddiy so'rov ─────────────────────────────────────────────────
print('\n' + '═' * 60)
print('2) TOOL\'SIZ SO\'ROV (kalit + model to\'g\'rimi?)')
print('═' * 60)

ok, res = post(url, {
    'model': model,
    'messages': [{'role': 'user', 'content': "Salom deb javob ber."}],
    'max_tokens': 50,
}, auth, ua=UA)

if ok:
    try:
        print('✅ ISHLADI. Javob:', res['choices'][0]['message']['content'][:200])
    except (KeyError, IndexError):
        print('⚠️  Javob keldi, lekin shakli kutilmagan:')
        print(json.dumps(res, ensure_ascii=False, indent=2)[:1500])
else:
    print('❌ XATO:')
    print(res[:2000])
    print('\nMa\'nosi:')
    print('  401 → kalit noto\'g\'ri yoki o\'chirilgan')
    print('  404 → model nomi noto\'g\'ri (AI_MODEL) yoki base_url xato')
    print('  429 → limit tugagan')
    sys.exit(1)

# ── 3) Tool bilan ────────────────────────────────────────────────────────────
print('\n' + '═' * 60)
print('3) TOOL BILAN (Groq bizning sxemamizni qabul qiladimi?)')
print('═' * 60)

from assistant import registry  # noqa: E402

try:
    tools = registry.build_llm_tools()
except Exception as e:  # noqa: BLE001
    print(f'❌ build_llm_tools() ishlamadi: {type(e).__name__}: {e}')
    sys.exit(1)

print(f'Tool soni: {len(tools)}')
for t in tools:
    fn = t.get('function', {})
    print(f"  • {fn.get('name')}")

# Avval BITTA tool bilan — sxema muammosini ajratish uchun.
if tools:
    print('\n— 3a) faqat birinchi tool bilan —')
    ok, res = post(url, {
        'model': model,
        'messages': [{'role': 'user', 'content': "Menga eng yaqin dorixonani top."}],
        'tools': tools[:1], 'tool_choice': 'auto', 'max_tokens': 150,
    }, auth, ua=UA)
    if ok:
        msg = res.get('choices', [{}])[0].get('message', {})
        print('✅ ISHLADI.')
        print('   content   :', (msg.get('content') or '')[:150])
        print('   tool_calls:', json.dumps(msg.get('tool_calls'), ensure_ascii=False)[:400])
    else:
        print('❌ XATO (bitta tool):')
        print(res[:2000])
        print('\n→ Sxema muammosi. Birinchi tool JSON Schema si:')
        print(json.dumps(tools[0], ensure_ascii=False, indent=2)[:2500])
        sys.exit(1)

print('\n— 3b) hamma tool bilan —')
ok, res = post(url, {
    'model': model,
    'messages': [{'role': 'user', 'content': "Menga eng yaqin dorixonani top."}],
    'tools': tools, 'tool_choice': 'auto', 'max_tokens': 150,
}, auth)
if ok:
    msg = res.get('choices', [{}])[0].get('message', {})
    print('✅ ISHLADI.')
    print('   content   :', (msg.get('content') or '')[:150])
    print('   tool_calls:', json.dumps(msg.get('tool_calls'), ensure_ascii=False)[:400])
    print('\n🎉 Hammasi joyida — muammo boshqa joyda (agent halqasi yoki ctx).')
else:
    print('❌ XATO (hamma tool):')
    print(res[:2000])
