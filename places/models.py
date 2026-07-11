from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _, pgettext_lazy
from main.utils import validate_file_type


CATEGORY_CHOICES = [
    ('furniture', _('Mebel do\'konlari')),
    ('electronics', _('Elektronika do\'konlari')),
    ('tourist', _('Diqqatga sazovor joylar')),
    ('government', _('Davlat binolari')),
    ('organization', _('Tashkilot ofislari')),
    ('post', pgettext_lazy('joy toifasi', 'Pochta bo\'limlari')),
    ('bank', _('Banklar')),
    ('pharmacy', _('Dorixonalar')),
    ('hospital', _('Shifoxonalar')),
    ('hotel', _('Mehmonxonalar')),
    ('wedding', _('To\'yxonalar')),
    ('restaurant', _('Restoranlar')),
    ('delivery_store', pgettext_lazy('joy toifasi', 'Do\'konlar')),
    ('school', _('Maktablar')),
    ('kindergarten', _('Bog\'chalar')),
    ('barber', _('Sartaroshxonalar')),
]

CATEGORY_ICON = {
    'furniture': '🛋️', 'electronics': '📱', 'tourist': '🗺️', 'government': '🏛️',
    'organization': '🏢', 'post': '✉️', 'bank': '🏦', 'pharmacy': '💊',
    'hospital': '🏥', 'hotel': '🏨', 'wedding': '💍', 'restaurant': '🍽️',
    'delivery_store': '🛒', 'school': '🏫', 'kindergarten': '🧸', 'barber': '💈',
}

CATEGORY_COLOR = {
    'furniture': '#b45309', 'electronics': '#2563eb', 'tourist': '#9333ea',
    'government': '#475569', 'organization': '#0891b2', 'post': '#ea580c',
    'bank': '#15803d', 'pharmacy': '#dc2626', 'hospital': '#e11d48',
    'hotel': '#7c3aed', 'wedding': '#db2777', 'restaurant': '#d97706',
    'delivery_store': '#059669', 'school': '#0284c7', 'kindergarten': '#f472b6',
    'barber': '#0d9488',
}


class Place(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='places',
    )
    name = models.CharField(max_length=200, verbose_name='Nomi')
    name_ru = models.CharField(max_length=200, blank=True, verbose_name='Nomi (ruscha)')
    name_en = models.CharField(max_length=200, blank=True, verbose_name='Nomi (inglizcha)')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, db_index=True, verbose_name='Toifa')
    description = models.TextField(blank=True, verbose_name='Tavsif')
    description_ru = models.TextField(blank=True, verbose_name='Tavsif (ruscha)')
    description_en = models.TextField(blank=True, verbose_name='Tavsif (inglizcha)')
    latitude = models.FloatField(verbose_name='Kenglik (latitude)',
                                 validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(verbose_name='Uzunlik (longitude)',
                                  validators=[MinValueValidator(-180), MaxValueValidator(180)])
    address = models.CharField(max_length=300, blank=True, verbose_name='Manzil')
    phone = models.CharField(max_length=40, blank=True, verbose_name='Telefon')
    working_hours = models.CharField(max_length=120, blank=True, verbose_name='Ish vaqti')
    website = models.URLField(blank=True, verbose_name='Veb-sayt')
    image = models.ImageField(upload_to='places/%Y/%m/', blank=True, null=True, validators=[validate_file_type])
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    views = models.PositiveIntegerField(default=0, verbose_name='Ko\'rishlar')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'places'
        verbose_name = 'Joy (xarita)'
        verbose_name_plural = 'Joylar (xarita)'
        ordering = ['name']
        indexes = [
            # Xarita/katalog: faol joylarni toifa bo'yicha filtrlash
            models.Index(fields=['is_active', 'category'], name='place_active_cat_idx'),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_category_display()})'

    def _localized(self, base):
        """Joriy tilga mos maydon qiymati (bo'sh bo'lsa — o'zbekcha asl matn)."""
        from django.utils.translation import get_language
        lang = (get_language() or 'uz')[:2]
        if lang in ('ru', 'en'):
            return getattr(self, f'{base}_{lang}') or getattr(self, base)
        return getattr(self, base)

    @property
    def localized_name(self):
        return self._localized('name')

    @property
    def localized_description(self):
        return self._localized('description')

    @property
    def icon(self):
        return CATEGORY_ICON.get(self.category, '📍')

    @property
    def color(self):
        return CATEGORY_COLOR.get(self.category, '#f5b942')


class PlaceImage(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='places/gallery/%Y/%m/')

    class Meta:
        db_table = 'place_images'
        verbose_name = 'Joy rasmi'
        verbose_name_plural = 'Joy rasmlari'

    def __str__(self):
        return f'{self.place.name} — rasm'


class PlaceReview(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='place_reviews')
    rating = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])  # 1..5
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'place_reviews'
        ordering = ['-created_at']
        unique_together = [('place', 'user')]
        verbose_name = 'Joy sharhi'
        verbose_name_plural = 'Joy sharhlari'

    def __str__(self):
        return f'{self.place.name} — {self.rating}★'


class PlaceFavorite(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='favorited_by')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorite_places')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'place_favorites'
        ordering = ['-created_at']
        unique_together = [('place', 'user')]

    def __str__(self):
        return f'{self.user} ♥ {self.place.name}'


# ── Place rating helpers (computed; no denormalized column) ──────────────────
def _place_avg_rating(self):
    from django.db.models import Avg
    return round(self.reviews.aggregate(a=Avg('rating'))['a'] or 0, 1)


def _place_review_count(self):
    return self.reviews.count()


Place.add_to_class('avg_rating', property(_place_avg_rating))
Place.add_to_class('review_count', property(_place_review_count))
