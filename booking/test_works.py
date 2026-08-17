"""Joy egasining portfoliosi (bajarilgan ishlar) testlari.

    python manage.py test booking.test_works
"""
import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from main.models import User
from booking.models import (
    Venue, VenueService, VenueStaff, VenueWork, MAX_WORKS_PER_VENUE,
)


def make_image(name='ish.jpg'):
    buf = io.BytesIO()
    Image.new('RGB', (80, 80), (20, 180, 120)).save(buf, format='JPEG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/jpeg')


_TEST_MEDIA = tempfile.mkdtemp(prefix='booking-works-')


@override_settings(MEDIA_ROOT=_TEST_MEDIA)
class VenueWorkTests(TestCase):
    """Rasm yuklovchi testlar — media haqiqiy MEDIA_ROOT'ni ifloslantirmasin."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEST_MEDIA, ignore_errors=True)

    def setUp(self):
        self.owner = User.objects.create_user(phone='+998910000101', password='x', is_active=True)
        self.other = User.objects.create_user(phone='+998910000102', password='x', is_active=True)
        self.venue = Venue.objects.create(owner=self.owner, name='Soch Usta', venue_type='barber')
        self.svc = VenueService.objects.create(
            venue=self.venue, name='Soch olish', price=30000, duration_minutes=30)
        self.master = VenueStaff.objects.create(venue=self.venue, name='Ali')

    def _login_owner(self):
        self.client.force_login(self.owner)

    def test_owner_adds_work_with_image(self):
        self._login_owner()
        resp = self.client.post(reverse('work_add', args=[self.venue.pk]), {
            'title': 'Fade turmak', 'description': 'Mashinka + qaychi',
            'price': '50000', 'service': str(self.svc.pk), 'staff': str(self.master.pk),
            'image': make_image(),
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        work = VenueWork.objects.get(venue=self.venue)
        self.assertEqual(work.title, 'Fade turmak')
        self.assertEqual(work.price, 50000)
        self.assertEqual(work.service_id, self.svc.pk)
        self.assertEqual(work.staff_id, self.master.pk)
        self.assertTrue(work.image.name)

    def test_work_requires_title_and_image(self):
        self._login_owner()
        self.client.post(reverse('work_add', args=[self.venue.pk]),
                         {'title': 'Rasmsiz ish'}, follow=True)
        self.client.post(reverse('work_add', args=[self.venue.pk]),
                         {'title': '', 'image': make_image()}, follow=True)
        self.assertEqual(VenueWork.objects.count(), 0)

    def test_stranger_cannot_add_work(self):
        self.client.force_login(self.other)
        self.client.post(reverse('work_add', args=[self.venue.pk]),
                         {'title': 'Begona ish', 'image': make_image()}, follow=True)
        self.assertEqual(VenueWork.objects.count(), 0)

    def test_stranger_cannot_delete_work(self):
        work = VenueWork.objects.create(venue=self.venue, title='Ish', image=make_image())
        self.client.force_login(self.other)
        self.client.post(reverse('work_delete', args=[work.pk]), follow=True)
        self.assertTrue(VenueWork.objects.filter(pk=work.pk).exists())

        self._login_owner()
        self.client.post(reverse('work_delete', args=[work.pk]), follow=True)
        self.assertFalse(VenueWork.objects.filter(pk=work.pk).exists())

    def test_works_shown_on_public_detail_page(self):
        VenueWork.objects.create(venue=self.venue, title='Fade turmak',
                                 description='Mashinka + qaychi', image=make_image())
        VenueWork.objects.create(venue=self.venue, title='Yashirin ish',
                                 image=make_image(), is_active=False)
        resp = self.client.get(reverse('venue_detail', args=[self.venue.pk]))
        self.assertContains(resp, 'Fade turmak')
        self.assertContains(resp, 'Mashinka + qaychi')
        self.assertNotContains(resp, 'Yashirin ish')

    def test_service_accepts_image_and_description(self):
        self._login_owner()
        self.client.post(reverse('service_add', args=[self.venue.pk]), {
            'name': 'Soqol olish', 'price': '20000', 'duration_minutes': '20',
            'description': 'Issiq sochiq bilan', 'image': make_image('svc.jpg'),
        }, follow=True)
        svc = VenueService.objects.get(venue=self.venue, name='Soqol olish')
        self.assertEqual(svc.description, 'Issiq sochiq bilan')
        self.assertTrue(svc.image.name)

    def test_work_limit_enforced(self):
        """Chegara to'lganda yangi ish qabul qilinmaydi, forma ham yashiriladi."""
        VenueWork.objects.bulk_create([
            VenueWork(venue=self.venue, title=f'Ish {i}', image='venues/works/x.jpg')
            for i in range(MAX_WORKS_PER_VENUE)
        ])
        self._login_owner()
        resp = self.client.post(reverse('work_add', args=[self.venue.pk]), {
            'title': 'Ortiqcha ish', 'image': make_image(),
        }, follow=True)
        self.assertEqual(VenueWork.objects.filter(venue=self.venue).count(),
                         MAX_WORKS_PER_VENUE)
        self.assertFalse(VenueWork.objects.filter(title='Ortiqcha ish').exists())
        self.assertContains(resp, "chegarasi")
        # Chegara to'lganda qo'shish formasi ko'rsatilmaydi
        self.assertNotContains(resp, 'name="title"')

    def test_work_allowed_under_limit(self):
        VenueWork.objects.bulk_create([
            VenueWork(venue=self.venue, title=f'Ish {i}', image='venues/works/x.jpg')
            for i in range(MAX_WORKS_PER_VENUE - 1)
        ])
        self._login_owner()
        self.client.post(reverse('work_add', args=[self.venue.pk]), {
            'title': 'Oxirgi ish', 'image': make_image(),
        }, follow=True)
        self.assertTrue(VenueWork.objects.filter(title='Oxirgi ish').exists())

    def test_limit_is_per_venue(self):
        """Chegara har bir joyga alohida — boshqa joy ta'sirlanmaydi."""
        other_venue = Venue.objects.create(
            owner=self.owner, name='Ikkinchi joy', venue_type='beauty')
        VenueWork.objects.bulk_create([
            VenueWork(venue=self.venue, title=f'Ish {i}', image='venues/works/x.jpg')
            for i in range(MAX_WORKS_PER_VENUE)
        ])
        self._login_owner()
        self.client.post(reverse('work_add', args=[other_venue.pk]), {
            'title': 'Yangi joydagi ish', 'image': make_image(),
        }, follow=True)
        self.assertTrue(VenueWork.objects.filter(venue=other_venue).exists())
