"""AI yordamchi — javob berilmagan savollar jurnali.

Mahalliy dvigatel tushunmagan (va LLM ham javob bermagan) savollarni bazaga
yozib boradi. Admin panelda (Jazzmin) eng ko'p takrorlangan javobsiz savollarni
ko'rib, ularga kalit so'z yoki qo'llanma qo'shib, asistantni vaqt o'tgani sari
aqlliroq qilib borish mumkin — LLMsiz yuqori sifatga erishishning asosiy usuli.
"""

from django.db import models


class UnansweredQuery(models.Model):
    # Normallashtirilgan kalit — bir xil savollarni birlashtirish (dedupe) uchun.
    normalized = models.CharField(max_length=255, unique=True, verbose_name='Kalit (ichki)')
    text = models.CharField(max_length=1000, verbose_name='Savol')
    count = models.PositiveIntegerField(default=1, verbose_name='Necha marta so‘ralgan')
    resolved = models.BooleanField(default=False, verbose_name='Hal qilingan')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Birinchi marta')
    last_seen = models.DateTimeField(auto_now=True, verbose_name='Oxirgi marta')

    class Meta:
        db_table = 'assistant_unanswered'
        ordering = ['-count', '-last_seen']
        verbose_name = 'Javobsiz savol'
        verbose_name_plural = 'Javobsiz savollar (AI)'

    def __str__(self):
        return f'{self.text} ×{self.count}'


def record_unanswered(text):
    """Tushunilmagan savolni yozadi/hisoblagichini oshiradi. Xatoga chidamli.

    Chat oqimini hech qachon buzmasligi uchun barcha xatoliklar yutiladi
    (chaqiruvchi tomonda ham try/except bor).
    """
    text = (text or '').strip()
    if not text:
        return
    from django.utils import timezone
    from django.db.models import F
    from .engine import _norm
    key = _norm(text)[:255]
    if not key:
        return
    obj, created = UnansweredQuery.objects.get_or_create(
        normalized=key, defaults={'text': text[:1000]})
    if not created:
        UnansweredQuery.objects.filter(pk=obj.pk).update(
            count=F('count') + 1, last_seen=timezone.now())
