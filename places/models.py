from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from main.utils import validate_file_type


CATEGORY_CHOICES = [
    ('furniture', 'Mebel do\'konlari'),
    ('electronics', 'Elektronika do\'konlari'),
    ('tourist', 'Diqqatga sazovor joylar'),
    ('government', 'Davlat binolari'),
    ('organization', 'Tashkilot ofislari'),
    ('post', 'Pochta bo\'limlari'),
    ('bank', 'Banklar'),
    ('pharmacy', 'Dorixonalar'),
    ('hospital', 'Shifoxonalar'),
    ('hotel', 'Mehmonxonalar'),
    ('wedding', 'To\'yxonalar'),
    ('restaurant', 'Restoranlar'),
    ('delivery_store', 'Do\'konlar'),
    ('school', 'Maktablar'),
    ('kindergarten', 'Bog\'chalar'),
]

CATEGORY_ICON = {
    'furniture': '🛋️', 'electronics': '📱', 'tourist': '🗺️', 'government': '🏛️',
    'organization': '🏢', 'post': '✉️', 'bank': '🏦', 'pharmacy': '💊',
    'hospital': '🏥', 'hotel': '🏨', 'wedding': '💍', 'restaurant': '🍽️',
    'delivery_store': '🛒', 'school': '🏫', 'kindergarten': '🧸',
}

CATEGORY_COLOR = {
    'furniture': '#b45309', 'electronics': '#2563eb', 'tourist': '#9333ea',
    'government': '#475569', 'organization': '#0891b2', 'post': '#ea580c',
    'bank': '#15803d', 'pharmacy': '#dc2626', 'hospital': '#e11d48',
    'hotel': '#7c3aed', 'wedding': '#db2777', 'restaurant': '#d97706',
    'delivery_store': '#059669', 'school': '#0284c7', 'kindergarten': '#f472b6',
}


class Place(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='places',
    )
    name = models.CharField(max_length=200, verbose_name='Nomi')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, db_index=True, verbose_name='Toifa')
    description = models.TextField(blank=True, verbose_name='Tavsif')
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
