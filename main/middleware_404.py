"""DEBUG rejimida ham chiroyli 404 sahifa ko'rsatadi.

Muammo: `DEBUG=True` bo'lganda Django o'zining texnik 404 sahifasini
chiqaradi va unda **loyihaning BARCHA URL manzillari** ro'yxati ko'rinadi
(admin yo'llari, ichki API endpointlari va h.k.). Ishlab chiqish paytida bu
qulay, lekin sahifa xodimlarga yoki demo ko'rsatuvda begonalarga ochilib
qolsa — ichki tuzilma oshkor bo'ladi.

Bu middleware `main/templates/404.html` ni DEBUG'da ham ishlatadi.
Django'ning texnik sahifasi kerak bo'lsa, `.env` da:

    DEBUG_SHOW_URL_LIST=True

`DEBUG=False` bo'lganda Django allaqachon 404.html ni ko'rsatadi —
middleware u yerda hech narsani o'zgartirmaydi.
"""
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render


class PrettyNotFoundMiddleware:
    """404 javobini loyiha shabloni bilan almashtiradi."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code != 404:
            return response
        # Faqat DEBUG'dagi texnik sahifa almashtiriladi.
        if not settings.DEBUG or getattr(settings, 'DEBUG_SHOW_URL_LIST', False):
            return response
        # API/JSON klientiga HTML sahifa yuborib bo'lmaydi (parse xatosi),
        # lekin Django texnik sahifasini ham qoldirib bo'lmaydi — u ayni
        # o'sha URL ro'yxatini oshkor qiladi. Shu bois qisqa JSON qaytariladi.
        path = request.path
        wants_json = (path.startswith('/api/')
                      or 'application/json' in request.headers.get('Accept', ''))
        if wants_json:
            return JsonResponse({'detail': 'Not found.'}, status=404)

        # Statik/media — tegilmaydi (fayl serveri o'zi javob beradi).
        if path.startswith(('/static/', '/media/')):
            return response

        return render(request, '404.html', status=404)
