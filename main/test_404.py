"""DEBUG rejimida 404 sahifasi loyiha shabloni bilan almashtirilishi.

    python manage.py test main.test_404
"""
import json

from django.test import TestCase, override_settings


@override_settings(DEBUG=True, DEBUG_SHOW_URL_LIST=False)
class PrettyNotFoundTests(TestCase):
    """DEBUG=True — texnik sahifa o'rniga 404.html."""

    def test_unknown_page_uses_project_template(self):
        resp = self.client.get('/qandaydir-yoq-sahifa/')
        self.assertEqual(resp.status_code, 404)
        self.assertContains(resp, 'SamCity', status_code=404)

    def test_url_list_not_exposed(self):
        """Eng muhimi: loyiha URL manzillari ro'yxati chiqmasin."""
        html = self.client.get('/qandaydir-yoq-sahifa/').content.decode()
        self.assertNotIn('URLconf', html)
        self.assertNotIn('Django tried these URL patterns', html)
        self.assertNotIn('admin_dashboard', html)

    def test_api_returns_json_not_technical_page(self):
        """API klienti HTML emas, JSON kutadi — va URL ro'yxati chiqmasin."""
        resp = self.client.get('/api/yoq-endpoint/')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp['Content-Type'], 'application/json')
        self.assertNotIn('URLconf', resp.content.decode())

    def test_json_accept_header_gets_json(self):
        resp = self.client.get('/yoq-sahifa/', HTTP_ACCEPT='application/json')
        self.assertEqual(resp.status_code, 404)
        self.assertNotIn(b'<!DOCTYPE html>', resp.content)
        self.assertEqual(json.loads(resp.content)['detail'], 'Not found.')

    def test_existing_page_untouched(self):
        self.assertEqual(self.client.get('/').status_code, 200)


@override_settings(DEBUG=True, DEBUG_SHOW_URL_LIST=True)
class TechnicalPageOptInTests(TestCase):
    """Sozlama yoqilsa — Django texnik sahifasi qaytadi (nosozlik izlash uchun)."""

    def test_technical_page_when_opted_in(self):
        html = self.client.get('/qandaydir-yoq-sahifa/').content.decode()
        self.assertIn('URLconf', html)


@override_settings(DEBUG=False)
class ProductionNotFoundTests(TestCase):
    """DEBUG=False — Django o'zi 404.html ni ko'rsatadi, middleware aralashmaydi."""

    def test_still_shows_project_template(self):
        resp = self.client.get('/qandaydir-yoq-sahifa/')
        self.assertEqual(resp.status_code, 404)
        self.assertContains(resp, 'SamCity', status_code=404)

    def test_no_url_list_in_production(self):
        html = self.client.get('/qandaydir-yoq-sahifa/').content.decode()
        self.assertNotIn('URLconf', html)
