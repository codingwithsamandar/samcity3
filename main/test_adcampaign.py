"""Reklama kampaniyasi testlari — auditoriya filtri, random N, kuniga-1 cheklovi."""
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone

from main.models import (
    User, Neighborhood, District, AdCampaign, AdCampaignDelivery,
)
from notifications.models import Notification


def _u(phone, **kw):
    return User.objects.create_user(phone=phone, password='x', **kw)


class AudienceFilterTest(TestCase):
    def setUp(self):
        self.d = District.objects.create(name='T')
        self.nb = Neighborhood.objects.create(name='M', district=self.d)
        self.other_nb = Neighborhood.objects.create(name='M2')
        y = date.today().year
        # erkak, 25 yosh, nb aholisi
        self.male25 = _u('+998900000101', gender='male',
                         birth_date=date(y - 25, 1, 1), neighborhood=self.nb)
        # ayol, 40 yosh, nb aholisi
        self.female40 = _u('+998900000102', gender='female',
                           birth_date=date(y - 40, 1, 1), neighborhood=self.nb)
        # erkak, 25 yosh, LEKIN boshqa mahalla
        self.male25_other = _u('+998900000103', gender='male',
                               birth_date=date(y - 25, 1, 1), neighborhood=self.other_nb)
        # erkak, yosh yo'q (birth_date=None)
        self.male_noage = _u('+998900000104', gender='male', neighborhood=self.nb)

    def test_gender_filter(self):
        c = AdCampaign.objects.create(title='x', text='y', gender='female', target_count=10)
        ids = set(c.audience_queryset().values_list('id', flat=True))
        self.assertIn(self.female40.id, ids)
        self.assertNotIn(self.male25.id, ids)

    def test_age_filter_excludes_unknown_age(self):
        c = AdCampaign.objects.create(title='x', text='y', age_min=18, age_max=30, target_count=10)
        ids = set(c.audience_queryset().values_list('id', flat=True))
        self.assertIn(self.male25.id, ids)       # 25 ∈ [18,30]
        self.assertIn(self.male25_other.id, ids)
        self.assertNotIn(self.female40.id, ids)  # 40 ∉
        self.assertNotIn(self.male_noage.id, ids)  # yoshi noma'lum → chiqmaydi

    def test_neighborhood_filter(self):
        c = AdCampaign.objects.create(title='x', text='y', neighborhood=self.nb, target_count=10)
        ids = set(c.audience_queryset().values_list('id', flat=True))
        self.assertIn(self.male25.id, ids)
        self.assertNotIn(self.male25_other.id, ids)

    def test_district_filter(self):
        c = AdCampaign.objects.create(title='x', text='y', district=self.d, target_count=10)
        ids = set(c.audience_queryset().values_list('id', flat=True))
        self.assertIn(self.male25.id, ids)          # nb ∈ district d
        self.assertNotIn(self.male25_other.id, ids)  # other_nb districtsiz

    def test_combined_gender_age_neighborhood(self):
        c = AdCampaign.objects.create(title='x', text='y', gender='male',
                                      age_min=18, age_max=30, neighborhood=self.nb, target_count=10)
        ids = set(c.audience_queryset().values_list('id', flat=True))
        self.assertEqual(ids, {self.male25.id})


class SendLogicTest(TestCase):
    def setUp(self):
        # 10 ta erkak, hammasi mos
        self.users = [_u(f'+99890000{i:04d}', gender='male') for i in range(10)]

    def test_random_n_limit(self):
        c = AdCampaign.objects.create(title='Aksiya', text='...', gender='male', target_count=3)
        sent = c.send()
        self.assertEqual(sent, 3)
        self.assertEqual(c.sent_count, 3)
        self.assertEqual(c.status, 'sent')
        self.assertEqual(Notification.objects.filter(category='ads').count(), 3)
        self.assertEqual(AdCampaignDelivery.objects.filter(campaign=c).count(), 3)

    def test_target_more_than_audience(self):
        c = AdCampaign.objects.create(title='x', text='y', gender='male', target_count=100)
        sent = c.send()
        self.assertEqual(sent, 10)  # bor-yo'g'i 10 kishi

    def test_one_ad_per_day_cap(self):
        # 1-kampaniya 10 kishiga yuboriladi
        c1 = AdCampaign.objects.create(title='A', text='...', gender='male', target_count=10)
        self.assertEqual(c1.send(), 10)
        # 2-kampaniya darhol yuborilsa — hamma 24 soat ichida olgan → 0
        c2 = AdCampaign.objects.create(title='B', text='...', gender='male', target_count=10)
        self.assertEqual(c2.send(), 0)

    def test_cap_expires_after_24h(self):
        c1 = AdCampaign.objects.create(title='A', text='...', gender='male', target_count=10)
        c1.send()
        # yetkazishlarni 25 soat oldinga surib qo'yamiz
        old = timezone.now() - timedelta(hours=25)
        AdCampaignDelivery.objects.filter(campaign=c1).update(sent_at=old)
        c2 = AdCampaign.objects.create(title='B', text='...', gender='male', target_count=10)
        self.assertEqual(c2.send(), 10)  # cheklov muddati o'tdi


class SendToAllTest(TestCase):
    """«Hammaga yuborish» — butun bazaga bir vaqtda (random N va 24-soat cheklovisiz)."""

    def setUp(self):
        # 12 ta har xil user (ba'zilari mahallali, jinsli — filtr yo'q bo'lsa hammasi)
        self.users = [_u(f'+99891000{i:04d}') for i in range(12)]
        # bitta nofaol — hammaga yuborishda ham chiqmasligi kerak
        self.inactive = _u('+998919999999', is_active=False)

    def test_broadcast_reaches_every_active_user(self):
        c = AdCampaign.objects.create(
            title='Rasmiy e‘lon', text='Hammaga', send_to_all=True, target_count=3)
        sent = c.send()
        # target_count=3 bo'lsa ham HAMMAGA (12) boradi, nofaol chiqmaydi
        self.assertEqual(sent, 12)
        self.assertEqual(c.status, 'sent')
        self.assertEqual(Notification.objects.count(), 12)
        self.assertEqual(
            Notification.objects.filter(recipient=self.inactive).count(), 0)

    def test_broadcast_ignores_24h_cap(self):
        # Avval hamma bugun bitta reklama olgan bo'lsin
        first = AdCampaign.objects.create(title='A', text='...', send_to_all=True)
        self.assertEqual(first.send(), 12)
        # Darhol yana «hammaga» — 24-soat cheklovi CHETLAB o'tiladi
        second = AdCampaign.objects.create(title='B', text='...', send_to_all=True)
        self.assertEqual(second.send(), 12)

    def test_broadcast_respects_filters_when_set(self):
        # Filtr qo'yilsa — «hammaga» ham faqat mos auditoriyaga boradi
        male = _u('+998911110001', gender='male')
        c = AdCampaign.objects.create(
            title='Erkaklarga', text='...', send_to_all=True, gender='male')
        sent = c.send()
        self.assertEqual(sent, 1)  # faqat bitta erkak
        self.assertEqual(Notification.objects.filter(recipient=male).count(), 1)
