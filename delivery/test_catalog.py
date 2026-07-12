"""Markaziy katalog (CatalogProduct) + Product.catalog_product testlari.

Qamrov:
  • CatalogProduct + Product.catalog_product bog'lanishi, is_custom.
  • Mahalla do'koni 10 ta custom (katalogsiz) mahsulot chegarasi (clean + API + web).
  • Katalogga bog'langan mahsulotlar cheklovsiz (mahalla ham).
  • Supermarket (delivery) — cheklovsiz custom.
  • Mavjud do'konlar grandfather qilinadi (10 dan oshgan holda ham tegilmaydi).
  • /api/catalog/ endpoint + ProductSerializer yangi maydonlari (cover fallback).
  • Admin 'promote_to_catalog' — custom → katalog (manba bog'lanadi); custom
    promote qilinmaguncha katalogda ko'rinmaydi.
"""
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from main.models import User, Neighborhood
from delivery.models import Store, Product, CatalogProduct, DeliveryCategory


def make_user(phone, **extra):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True, **extra)


def make_custom(store, name='X', price=1000, stock=5):
    """ORM orqali custom mahsulot (clean chaqirilmaydi — setup uchun)."""
    return Product.objects.create(store=store, name=name, price=price, stock=stock)


class CatalogModelTests(TestCase):
    def setUp(self):
        self.owner = make_user('+998939100001')
        self.cat = DeliveryCategory.objects.create(name='Oziq-ovqat', slug='oziq-ovqat')
        self.store = Store.objects.create(owner=self.owner, name='Market', store_type='delivery')
        self.catalog = CatalogProduct.objects.create(
            name='Sut 1L', brand='Nestle', category=self.cat, unit='liter')

    def test_custom_flag(self):
        p_custom = make_custom(self.store, name='Uy noni')
        p_linked = Product.objects.create(
            store=self.store, catalog_product=self.catalog, name='Sut 1L', price=12000, stock=10)
        self.assertTrue(p_custom.is_custom)
        self.assertFalse(p_linked.is_custom)
        self.assertEqual(p_linked.catalog_product, self.catalog)

    def test_catalog_str_and_unit(self):
        self.assertIn('Sut 1L', str(self.catalog))
        self.assertEqual(self.catalog.unit, 'liter')

    def test_store_custom_product_count(self):
        make_custom(self.store, name='A')
        make_custom(self.store, name='B')
        Product.objects.create(store=self.store, catalog_product=self.catalog,
                               name='Sut', price=1, stock=1)
        # Faqat custom (katalogsiz) sanaladi.
        self.assertEqual(self.store.custom_product_count(), 2)


class MahallaCustomLimitTests(TestCase):
    def setUp(self):
        self.owner = make_user('+998939100010')
        self.nb = Neighborhood.objects.create(name='Mahalla L')
        self.mahalla = Store.objects.create(
            owner=self.owner, name='Mahalla do\'kon', store_type='mahalla',
            neighborhood=self.nb, pickup_enabled=True)
        self.catalog = CatalogProduct.objects.create(name='Guruch 1kg', unit='kg')
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def _fill_custom(self, n):
        for i in range(n):
            make_custom(self.mahalla, name=f'Custom {i}')

    def test_clean_blocks_11th_custom(self):
        self._fill_custom(10)
        p = Product(store=self.mahalla, name='11-chi', price=1000, stock=1)
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_api_blocks_11th_custom(self):
        self._fill_custom(10)
        r = self.api.post(f'/api/stores/{self.mahalla.pk}/products/',
                          {'name': 'O\'n birinchi', 'price': 5000, 'stock': 3}, format='json')
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.mahalla.custom_product_count(), 10)

    def test_api_allows_10th_custom(self):
        self._fill_custom(9)
        r = self.api.post(f'/api/stores/{self.mahalla.pk}/products/',
                          {'name': 'O\'ninchi', 'price': 5000, 'stock': 3}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.mahalla.custom_product_count(), 10)

    def test_web_blocks_11th_custom(self):
        self._fill_custom(10)
        self.client.force_login(self.owner)
        r = self.client.post(
            f'/delivery/store/{self.mahalla.pk}/product/create/',
            {'name': '11-chi', 'price': 5000, 'stock': 3}, HTTP_HOST='127.0.0.1')
        self.assertEqual(r.status_code, 200)  # forma qayta ko'rsatiladi (redirect emas)
        self.assertEqual(self.mahalla.custom_product_count(), 10)

    def test_catalog_linked_unlimited_for_mahalla(self):
        self._fill_custom(10)  # custom limitga yetdi
        # Katalogga bog'langan mahsulotlar cheklovsiz qo'shiladi.
        for i in range(5):
            r = self.api.post(
                f'/api/stores/{self.mahalla.pk}/products/',
                {'catalog_product': self.catalog.pk, 'price': 20000 + i, 'stock': 4},
                format='json')
            self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.mahalla.custom_product_count(), 10)  # o'zgarmadi
        self.assertEqual(self.mahalla.products.filter(catalog_product__isnull=False).count(), 5)

    def test_catalog_prefills_name(self):
        r = self.api.post(
            f'/api/stores/{self.mahalla.pk}/products/',
            {'catalog_product': self.catalog.pk, 'price': 20000, 'stock': 4}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['name'], 'Guruch 1kg')
        self.assertEqual(r.data['catalog_product'], self.catalog.pk)
        self.assertFalse(r.data['is_custom'])
        self.assertEqual(r.data['unit'], 'kg')


class SupermarketUnlimitedTests(TestCase):
    def setUp(self):
        self.owner = make_user('+998939100020', is_staff=True)
        self.store = Store.objects.create(owner=self.owner, name='Katta market', store_type='delivery')
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def test_delivery_store_unlimited_custom(self):
        for i in range(12):
            r = self.api.post(f'/api/stores/{self.store.pk}/products/',
                              {'name': f'Mahsulot {i}', 'price': 1000, 'stock': 2}, format='json')
            self.assertEqual(r.status_code, 201)
        self.assertEqual(self.store.custom_product_count(), 12)


class GrandfatherTests(TestCase):
    """10 dan oshgan mavjud mahalla do'koni — tegilmaydi, lekin yangi custom bloklanadi."""
    def setUp(self):
        self.owner = make_user('+998939100030')
        self.nb = Neighborhood.objects.create(name='Eski mahalla')
        self.mahalla = Store.objects.create(
            owner=self.owner, name='Eski do\'kon', store_type='mahalla',
            neighborhood=self.nb, pickup_enabled=True)
        for i in range(12):
            make_custom(self.mahalla, name=f'Eski {i}')  # ORM — clean chetlab o'tiladi
        self.catalog = CatalogProduct.objects.create(name='Tuz', unit='pack')
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def test_existing_over_limit_not_trimmed(self):
        self.assertEqual(self.mahalla.custom_product_count(), 12)

    def test_new_custom_still_blocked(self):
        r = self.api.post(f'/api/stores/{self.mahalla.pk}/products/',
                          {'name': 'Yangi custom', 'price': 1000, 'stock': 1}, format='json')
        self.assertEqual(r.status_code, 409)

    def test_catalog_still_addable(self):
        r = self.api.post(f'/api/stores/{self.mahalla.pk}/products/',
                          {'catalog_product': self.catalog.pk, 'price': 3000, 'stock': 9}, format='json')
        self.assertEqual(r.status_code, 201)


class CatalogApiTests(TestCase):
    def setUp(self):
        self.user = make_user('+998939100040')
        self.active = CatalogProduct.objects.create(name='Non', unit='piece', is_active=True)
        self.inactive = CatalogProduct.objects.create(name='Eski shakar', unit='kg', is_active=False)
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def test_catalog_list_only_active(self):
        r = self.api.get('/api/catalog/')
        self.assertEqual(r.status_code, 200)
        names = [c['name'] for c in (r.data.get('results') or r.data)]
        self.assertIn('Non', names)
        self.assertNotIn('Eski shakar', names)

    def test_catalog_search(self):
        CatalogProduct.objects.create(name='Sut', unit='liter')
        r = self.api.get('/api/catalog/?search=Non')
        names = [c['name'] for c in (r.data.get('results') or r.data)]
        self.assertIn('Non', names)
        self.assertNotIn('Sut', names)

    def test_catalog_search_by_brand_and_category_name(self):
        """Qidiruv brend va kategoriya NOMI bo'yicha ham ishlaydi (Phase 4)."""
        cat = DeliveryCategory.objects.create(name='Ichimliklar', slug='ichimliklar')
        CatalogProduct.objects.create(name='Cola 1L', brand='CocaCola',
                                      category=cat, unit='bottle')
        # brend bo'yicha
        r = self.api.get('/api/catalog/?search=CocaCola')
        names = [c['name'] for c in (r.data.get('results') or r.data)]
        self.assertEqual(names, ['Cola 1L'])
        # kategoriya nomi bo'yicha
        r = self.api.get('/api/catalog/?search=Ichimliklar')
        names = [c['name'] for c in (r.data.get('results') or r.data)]
        self.assertEqual(names, ['Cola 1L'])

    def test_catalog_filter_by_brand_and_unit(self):
        """?brand= va ?unit= filtrlari (Phase 4)."""
        CatalogProduct.objects.create(name='Fanta 1L', brand='CocaCola', unit='bottle')
        CatalogProduct.objects.create(name='Guruch 1kg', brand='Devzira', unit='kg')
        r = self.api.get('/api/catalog/?brand=CocaCola')
        names = [c['name'] for c in (r.data.get('results') or r.data)]
        self.assertEqual(names, ['Fanta 1L'])
        r = self.api.get('/api/catalog/?unit=kg')
        names = [c['name'] for c in (r.data.get('results') or r.data)]
        self.assertEqual(names, ['Guruch 1kg'])

    def test_catalog_filter_by_category_id(self):
        cat = DeliveryCategory.objects.create(name='Bozor', slug='bozor')
        CatalogProduct.objects.create(name='Olma 1kg', category=cat, unit='kg')
        r = self.api.get(f'/api/catalog/?category={cat.pk}')
        names = [c['name'] for c in (r.data.get('results') or r.data)]
        self.assertEqual(names, ['Olma 1kg'])


class InactiveCatalogLinkTests(TestCase):
    """6-vazifa: nofaol (is_active=False) katalog mahsulotiga bog'lash taqiqlanadi."""

    def setUp(self):
        self.owner = make_user('+998939100060')
        self.store = Store.objects.create(
            owner=self.owner, name='Link market', store_type='delivery')
        self.inactive = CatalogProduct.objects.create(
            name="O'chirilgan mahsulot", unit='piece', is_active=False)
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def test_api_rejects_inactive_catalog_link(self):
        r = self.api.post(f'/api/stores/{self.store.pk}/products/',
                          {'catalog_product': self.inactive.pk, 'price': 5000, 'stock': 3},
                          format='json')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Product.objects.filter(store=self.store).exists())

    def test_web_rejects_inactive_catalog_link(self):
        from django.urls import reverse
        self.client.force_login(self.owner)
        self.client.post(
            reverse('delivery:product_create', args=[self.store.pk]),
            {'catalog_product': self.inactive.pk, 'name': 'X', 'price': 5000},
            HTTP_HOST='127.0.0.1')
        self.assertFalse(Product.objects.filter(store=self.store).exists())


class StoreDashboardCountsTests(TestCase):
    """5-vazifa: /api/my/stores/ mahalla do'koni uchun custom X/10 + katalog Y."""

    def setUp(self):
        self.owner = make_user('+998939100070')
        self.nb = Neighborhood.objects.create(name='Stats mahalla')
        self.store = Store.objects.create(
            owner=self.owner, name='Stats do\'kon', store_type='mahalla',
            neighborhood=self.nb, pickup_enabled=True)
        self.catalog = CatalogProduct.objects.create(name='Katalog non', unit='piece')
        make_custom(self.store, name='O\'z mahsulot 1')
        make_custom(self.store, name='O\'z mahsulot 2')
        Product.objects.create(store=self.store, name='Katalog non',
                               catalog_product=self.catalog, price=4000, stock=10)
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def test_my_stores_exposes_counts(self):
        r = self.api.get('/api/my/stores/')
        self.assertEqual(r.status_code, 200)
        s = r.data['results'][0]
        self.assertEqual(s['custom_product_count'], 2)
        self.assertEqual(s['custom_limit'], Product.MAHALLA_CUSTOM_LIMIT)
        self.assertEqual(s['catalog_product_count'], 1)

    def test_counts_null_for_delivery_store(self):
        sup = Store.objects.create(owner=self.owner, name='Supermarket', store_type='delivery')
        Product.objects.create(store=sup, name='K', catalog_product=self.catalog,
                               price=1000, stock=1)
        r = self.api.get('/api/my/stores/')
        by_name = {s['name']: s for s in r.data['results']}
        self.assertIsNone(by_name['Supermarket']['custom_product_count'])
        self.assertIsNone(by_name['Supermarket']['catalog_product_count'])

    def test_web_my_stores_shows_counts(self):
        from django.urls import reverse
        self.client.force_login(self.owner)
        html = self.client.get(reverse('delivery:my_stores'), HTTP_HOST='127.0.0.1').content.decode()
        self.assertIn('2 / 10', html)
        self.assertIn('Katalogdan: 1', html)


class PromoteToCatalogTests(TestCase):
    def setUp(self):
        self.admin = make_user('+998939100050', is_staff=True, is_superuser=True, role='admin')
        self.owner = make_user('+998939100051')
        self.nb = Neighborhood.objects.create(name='Promo mahalla')
        self.store = Store.objects.create(
            owner=self.owner, name='Promo do\'kon', store_type='mahalla',
            neighborhood=self.nb, pickup_enabled=True)
        self.custom = make_custom(self.store, name='Uy murabbosi', price=25000, stock=3)
        self.client.force_login(self.admin)

    def test_custom_not_in_catalog_until_promoted(self):
        # Custom mahsulot avtomatik katalogga tushmaydi.
        self.assertFalse(CatalogProduct.objects.filter(name='Uy murabbosi').exists())

    def test_admin_promote_creates_catalog_and_links(self):
        resp = self.client.post('/admin/delivery/product/', {
            'action': 'promote_to_catalog',
            '_selected_action': [str(self.custom.pk)],
        }, HTTP_HOST='127.0.0.1')
        self.assertIn(resp.status_code, (200, 302))
        cat = CatalogProduct.objects.filter(name='Uy murabbosi').first()
        self.assertIsNotNone(cat)
        self.assertEqual(cat.promoted_from_id, self.custom.pk)
        self.custom.refresh_from_db()
        # Manba mahsulot endi katalogga bog'landi (custom emas).
        self.assertEqual(self.custom.catalog_product_id, cat.pk)
        self.assertFalse(self.custom.is_custom)

    def test_promote_skips_already_linked(self):
        cat = CatalogProduct.objects.create(name='Allaqachon', unit='piece')
        linked = Product.objects.create(store=self.store, catalog_product=cat,
                                        name='Allaqachon', price=1, stock=1)
        before = CatalogProduct.objects.count()
        self.client.post('/admin/delivery/product/', {
            'action': 'promote_to_catalog',
            '_selected_action': [str(linked.pk)],
        }, HTTP_HOST='127.0.0.1')
        self.assertEqual(CatalogProduct.objects.count(), before)  # yangi yaratilmadi


class AdminRenderTests(TestCase):
    """Katalog admin sahifalari 500'siz ochiladi (affected pages smoke)."""
    def setUp(self):
        self.admin = make_user('+998939100060', is_staff=True, is_superuser=True, role='admin')
        self.client.force_login(self.admin)

    def test_admin_pages_render(self):
        for url in ('/admin/delivery/catalogproduct/',
                    '/admin/delivery/catalogproduct/add/',
                    '/admin/delivery/product/'):
            r = self.client.get(url, HTTP_HOST='127.0.0.1')
            self.assertEqual(r.status_code, 200, url)


class StoreDetailApiTests(TestCase):
    """Do'kon detali (API) katalog maydonlari + cover fallback bilan ishlaydi."""
    def setUp(self):
        self.owner = make_user('+998939100070')
        self.store = Store.objects.create(
            owner=self.owner, name='Detal market', store_type='delivery', is_active=True)
        self.cat = CatalogProduct.objects.create(name='Sut 1L', unit='liter')
        Product.objects.create(store=self.store, catalog_product=self.cat,
                               name='Sut 1L', price=12000, stock=5, is_available=True)
        make_custom(self.store, name='Uy noni', price=4000, stock=8)

    def test_detail_exposes_catalog_and_custom(self):
        r = APIClient().get(f'/api/stores/{self.store.pk}/')
        self.assertEqual(r.status_code, 200)
        prods = {p['name']: p for p in r.data['products']}
        self.assertEqual(prods['Sut 1L']['catalog_product'], self.cat.pk)
        self.assertFalse(prods['Sut 1L']['is_custom'])
        self.assertEqual(prods['Sut 1L']['unit'], 'liter')
        self.assertTrue(prods['Uy noni']['is_custom'])
        self.assertIsNone(prods['Uy noni']['catalog_product'])


class CatalogPaginationTests(TestCase):
    """5-vazifa (Phase 5): /api/catalog/ paginatsiyasi — hajm, navigatsiya,
    qidiruv/filtr bilan birga ishlashi."""

    PAGE_SIZE = 20  # settings.REST_FRAMEWORK['PAGE_SIZE']

    def setUp(self):
        self.user = make_user('+998939100080')
        self.cat = DeliveryCategory.objects.create(name='Pag kat', slug='pag-kat')
        for i in range(25):
            CatalogProduct.objects.create(
                name=f'Mahsulot {i:02d}', unit='piece',
                category=self.cat if i < 5 else None)
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def test_page_size_and_navigation(self):
        r = self.api.get('/api/catalog/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 25)
        self.assertEqual(len(r.data['results']), self.PAGE_SIZE)
        self.assertIsNotNone(r.data['next'])
        self.assertIsNone(r.data['previous'])
        r2 = self.api.get('/api/catalog/?page=2')
        self.assertEqual(len(r2.data['results']), 25 - self.PAGE_SIZE)
        self.assertIsNone(r2.data['next'])
        self.assertIsNotNone(r2.data['previous'])

    def test_pagination_with_filter_and_search(self):
        r = self.api.get(f'/api/catalog/?category={self.cat.pk}')
        self.assertEqual(r.data['count'], 5)
        self.assertEqual(len(r.data['results']), 5)
        r = self.api.get('/api/catalog/?search=Mahsulot 1')
        # DRF SearchFilter atamalarni bo'lib qidiradi: nomida '1' borlar —
        # 01, 10..19, 21 = 12 ta.
        self.assertEqual(r.data['count'], 12)

    def test_out_of_range_page_returns_404(self):
        r = self.api.get('/api/catalog/?page=99')
        self.assertEqual(r.status_code, 404)


class CatalogToolingTests(TestCase):
    """Phase 5 buyruqlari: catalog_health, export_catalog, import --validate-only
    va admin hisoboti (rasm qamrovi + CSV)."""

    def setUp(self):
        self.cat = DeliveryCategory.objects.create(name='Tool kat', slug='tool-kat')
        CatalogProduct.objects.create(name='Rasmli non', unit='piece', category=self.cat)
        CatalogProduct.objects.create(name='Rasmsiz sut', unit='liter')
        CatalogProduct.objects.create(name='Nofaol tuz', unit='kg', is_active=False)

    def _call(self, cmd, *args):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command(cmd, *args, stdout=out)
        return out.getvalue()

    def test_catalog_health_reports_counts(self):
        out = self._call('catalog_health')
        self.assertIn('Jami mahsulotlar:        3', out)
        self.assertIn('Faol (is_active=True):   2', out)
        self.assertIn('Nofaol:                  1', out)
        self.assertIn('Rasmsiz:                 3', out)  # testda rasm yuklanmagan
        self.assertIn('Kategoriyasiz (NULL) mahsulotlar: 2', out)

    def test_export_catalog_writes_json(self):
        import json
        import os
        import tempfile
        path = os.path.join(tempfile.gettempdir(), 'test_catalog_export.json')
        try:
            out = self._call('export_catalog', '--output', path)
            self.assertIn('2 ta mahsulot eksport qilindi', out)  # faqat faollar
            data = json.load(open(path, encoding='utf-8'))
            self.assertEqual(data['count'], 2)
            names = {p['name'] for p in data['products']}
            self.assertEqual(names, {'Rasmli non', 'Rasmsiz sut'})
            p = data['products'][0]
            for key in ('name', 'category', 'brand', 'unit', 'description',
                        'image_path', 'image_url'):
                self.assertIn(key, p)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_import_validate_only_writes_nothing(self):
        import json
        import os
        import tempfile
        payload = {'products': [
            {'name': 'Yangi validatsiya mahsuloti', 'brand': 'X', 'unit': 'piece',
             'category': 'Beverages', 'subcategory': 'Water',
             'description': 'test', 'image_path': 'catalog/yoq.webp'},
        ]}
        path = os.path.join(tempfile.gettempdir(), 'test_validate_only.json')
        json.dump(payload, open(path, 'w', encoding='utf-8'))
        before = CatalogProduct.objects.count()
        try:
            out = self._call('import_catalog', '--validate-only',
                             '--json', path, '--images', 'yo-q-zip.zip')
            self.assertIn('VALIDATE-ONLY', out)
            self.assertIn('VALIDATSIYA XULOSASI', out)
            self.assertEqual(CatalogProduct.objects.count(), before)  # yozilmadi
        finally:
            os.remove(path)

    def test_admin_report_and_csv(self):
        admin_u = make_user('+998939100090', is_staff=True, is_superuser=True, role='admin')
        self.client.force_login(admin_u)
        r = self.client.get('/admin/delivery/catalogproduct/report/', HTTP_HOST='127.0.0.1')
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn('Katalog hisoboti', html)
        self.assertIn('Rasmsiz sut', html)  # rasmsizlar jadvalida
        r = self.client.get('/admin/delivery/catalogproduct/missing-images.csv',
                            HTTP_HOST='127.0.0.1')
        self.assertEqual(r.status_code, 200)
        self.assertIn('text/csv', r['Content-Type'])
        body = r.content.decode('utf-8-sig')
        self.assertIn('Rasmsiz sut', body)
        self.assertIn('Nofaol tuz', body)
