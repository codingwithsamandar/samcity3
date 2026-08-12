"""Tashqi manbalardan e'lon qidirish (OLX va h.k.) — kengaytiriladigan tizim.

Maqsad: AI asistent faqat SAYT ichidagi e'lonlar bilan cheklanmasin. Saytda
natija kam bo'lsa yoki foydalanuvchi so'rasa — tashqi saytlardan (hozircha
OLX.uz) qo'shimcha e'lonlar keltiriladi.

Yangi sayt qo'shish uchun: `base.Provider` dan meros olib `search()` yozing va
`base.register` bilan ro'yxatga qo'shing (namuna — `olx.py`). Boshqa hech joyni
o'zgartirish shart emas: `service.search()` avtomatik foydalanadi.
"""

from .service import search  # noqa: F401  (qulay import: external.search(...))
