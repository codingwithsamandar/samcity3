"""Validatsiya testlari — telefon, koordinata (lat/lng), reyting chegaralari."""
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import Ad, HelpRequest, User
from delivery.models import DriverLocation
from taxi.models import ServiceReview, TaxistReview


class PhoneRegisterValidationTests(TestCase):
    """API ro'yxatdan o'tishda noto'g'ri telefon rad etiladi."""

    def _post(self, phone):
        return APIClient().post(reverse('api:register'), {
            'phone': phone, 'password': 'Test12345!', 'name': 'X',
        }, format='json')

    def test_letters_rejected(self):
        self.assertEqual(self._post('abc123').status_code, 400)

    def test_too_short_rejected(self):
        self.assertEqual(self._post('+998999').status_code, 400)

    def test_too_long_rejected(self):
        self.assertEqual(self._post('+9989012345678901234').status_code, 400)

    @patch('api.views.send_sms', return_value=True)
    def test_valid_accepted(self, _send):
        resp = self._post('+998901234567')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(User.objects.filter(phone='+998901234567').exists())


class CoordinateValidatorTests(TestCase):
    """lat ∈ [-90,90], lng ∈ [-180,180] — model maydon validatorlari."""

    def _field(self, model, name):
        return model._meta.get_field(name)

    def test_latitude_out_of_range_raises(self):
        for model in (Ad, HelpRequest, DriverLocation):
            with self.assertRaises(ValidationError):
                self._field(model, 'latitude').run_validators(91)
            with self.assertRaises(ValidationError):
                self._field(model, 'latitude').run_validators(-91)

    def test_longitude_out_of_range_raises(self):
        for model in (Ad, HelpRequest, DriverLocation):
            with self.assertRaises(ValidationError):
                self._field(model, 'longitude').run_validators(181)

    def test_valid_coords_ok(self):
        # Xato otmasligi kerak
        self._field(Ad, 'latitude').run_validators(39.65)
        self._field(Ad, 'longitude').run_validators(66.96)


class RatingValidatorTests(TestCase):
    """Reyting 1..5 oralig'ida — taxi sharhlari uchun model validatorlari."""

    def test_rating_above_five_raises(self):
        for model in (ServiceReview, TaxistReview):
            with self.assertRaises(ValidationError):
                model._meta.get_field('rating').run_validators(7)
            with self.assertRaises(ValidationError):
                model._meta.get_field('rating').run_validators(999)

    def test_valid_rating_ok(self):
        ServiceReview._meta.get_field('rating').run_validators(5)
        TaxistReview._meta.get_field('rating').run_validators(1)
