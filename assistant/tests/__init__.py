"""AI yordamchi testlari.

⚠️ TESTLAR HECH QACHON HAQIQIY LLM GA CHIQMAYDI.

Dasturchi mashinasida (yoki CI'da) `.env` ichida `AI_API_KEY` bo'lishi mumkin —
o'sha holda `llm.agent_enabled()` True bo'lib, testlar Groq/OpenAI ga haqiqiy
so'rov yuborardi: sekin, beqaror va PULLIK. Shuning uchun kalitni shu yerda
tozalaymiz. Bu paket test modullaridan OLDIN import qilinadi, ya'ni kafolatli.

LLM xatti-harakati kerak bo'lgan testlar uni o'zi mock qiladi
(`mock.patch.object(agent.llm, 'call', ...)`).

Haqiqiy model bilan sinash uchun test emas, alohida buyruq bor:
    python manage.py smoke_agent --model ...
"""

import os

os.environ['AI_API_KEY'] = ''
