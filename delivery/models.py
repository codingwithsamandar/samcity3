import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from main.utils import validate_file_type


class DeliveryCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.ImageField(upload_to='delivery/categories/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'delivery_categories'
        verbose_name = 'Yetkazib berish kategoriyasi'
        verbose_name_plural = 'Yetkazib berish kategoriyalari'
        ordering = ['name']

    def __str__(self):
        return self.name


class Store(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stores',
    )
    category = models.ForeignKey(
        DeliveryCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stores',
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=300, blank=True)
    latitude = models.FloatField(blank=True, null=True,
                                 validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(blank=True, null=True,
                                  validators=[MinValueValidator(-180), MaxValueValidator(180)])
    logo = models.ImageField(upload_to='delivery/stores/', blank=True, null=True, verbose_name='Logo',
                             validators=[validate_file_type])
    phone = models.CharField(max_length=20, blank=True, verbose_name='Telefon')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'delivery_stores'
        verbose_name = "Do'kon"
        verbose_name_plural = "Do'konlar"
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Product(models.Model):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='products',
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'delivery_products'
        verbose_name = 'Mahsulot'
        verbose_name_plural = 'Mahsulotlar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.store.name}'


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
    )
    image = models.ImageField(upload_to='delivery/products/%Y/%m/')

    class Meta:
        db_table = 'delivery_product_images'
        verbose_name = 'Mahsulot rasmi'
        verbose_name_plural = 'Mahsulot rasmlari'

    def clean(self):
        if not self.pk:
            count = ProductImage.objects.filter(product=self.product).count()
            if count >= 4:
                raise ValidationError("Bir mahsulotga 4 tadan ko'p rasm qo'shib bo'lmaydi.")

    def __str__(self):
        return f'{self.product.name} — rasm'


# ── CART ──────────────────────────────────────────────────────────────────────

class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delivery_cart',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'delivery_carts'
        verbose_name = 'Savat'
        verbose_name_plural = 'Savatlar'

    def __str__(self):
        return f"Savat — {self.user}"

    def get_total_items(self):
        """Number of distinct product lines in the cart."""
        return self.items.count()

    def get_total_quantity(self):
        """Sum of all item quantities."""
        result = self.items.aggregate(total=models.Sum('quantity'))
        return result['total'] or 0

    def get_subtotal(self):
        """Total price across all items (price × quantity)."""
        subtotal = 0
        for item in self.items.select_related('product'):
            subtotal += item.product.price * item.quantity
        return subtotal

    def get_summary(self):
        return {
            'total_items': self.get_total_items(),
            'total_quantity': self.get_total_quantity(),
            'subtotal_price': self.get_subtotal(),
        }


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items',
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'delivery_cart_items'
        verbose_name = 'Savat elementi'
        verbose_name_plural = 'Savat elementlari'
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

    def get_line_total(self):
        return self.product.price * self.quantity


# ── ORDER (buyurtma — checkout natijasi) ────────────────────────────────────────

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('accepted', 'Qabul qilindi'),
        ('preparing', 'Tayyorlanmoqda'),
        ('ready', 'Tayyor'),
        ('assigned', 'Haydovchi biriktirildi'),
        ('picked_up', 'Olib ketildi'),
        ('on_the_way', "Yo'lda"),
        ('delivered', 'Yetkazildi'),
        ('cancelled', 'Bekor qilingan'),
    ]
    PAYMENT_METHOD_CHOICES = [('card', 'Karta'), ('cash', "Yetkazishda naqd")]
    PAYMENT_STATUS_CHOICES = [('unpaid', "To'lanmagan"), ('paid', "To'langan")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_orders',
    )
    full_name = models.CharField(max_length=120, verbose_name='Qabul qiluvchi')
    phone = models.CharField(max_length=30, verbose_name='Telefon')
    address = models.CharField(max_length=300, verbose_name='Yetkazish manzili')
    note = models.TextField(blank=True, verbose_name='Izoh')
    subtotal = models.BigIntegerField(default=0, verbose_name="Mahsulotlar summasi")
    delivery_fee = models.BigIntegerField(default=0, verbose_name="Yetkazish narxi")
    total = models.BigIntegerField(default=0, verbose_name="Umumiy summa")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='card')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='unpaid', db_index=True)
    card_last4 = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=20, blank=True)
    driver = models.ForeignKey(
        'delivery.DeliveryDriver', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='deliveries', verbose_name='Haydovchi',
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'delivery_orders'
        verbose_name = 'Buyurtma'
        verbose_name_plural = 'Buyurtmalar'
        ordering = ['-created_at']
        indexes = [
            # Haydovchi paneli: filter(status='ready', driver__isnull=True)
            models.Index(fields=['status', 'driver'], name='order_status_driver_idx'),
            # Foydalanuvchi buyurtmalari ro'yxati (eng so'nggidan)
            models.Index(fields=['user', '-created_at'], name='order_user_created_idx'),
        ]

    def __str__(self):
        return f'Buyurtma #{str(self.id)[:8]} — {self.total} so\'m'

    @property
    def is_paid(self):
        return self.payment_status == 'paid'


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    product_name = models.CharField(max_length=200)
    store_name = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'delivery_order_items'
        verbose_name = 'Buyurtma elementi'
        verbose_name_plural = 'Buyurtma elementlari'

    def __str__(self):
        return f'{self.product_name} × {self.quantity}'

    def get_line_total(self):
        return self.price * self.quantity


# ── DELIVERY DRIVER (yetkazib beruvchi haydovchi) ───────────────────────────────

class DeliveryDriver(models.Model):
    VEHICLE_CHOICES = [
        ('foot', '🚶 Piyoda'),
        ('bike', '🚲 Velosiped'),
        ('moto', '🏍️ Mototsikl'),
        ('car', '🚗 Avtomobil'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_driver',
    )
    full_name = models.CharField(max_length=120, verbose_name='Ism familiya')
    phone = models.CharField(max_length=30, verbose_name='Telefon')
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_CHOICES, default='moto', verbose_name='Transport turi')
    vehicle_number = models.CharField(max_length=30, blank=True, verbose_name='Davlat raqami')
    is_available = models.BooleanField(default=True, verbose_name='Bo\'sh (buyurtma qabul qiladi)')
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'delivery_drivers'
        verbose_name = 'Yetkazib beruvchi'
        verbose_name_plural = 'Yetkazib beruvchilar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} ({self.get_vehicle_type_display()})'


# ── DRIVER LOCATION (real-time tracking) ────────────────────────────────────────

class DriverLocation(models.Model):
    """Yetkazib beruvchi haydovchining oxirgi joylashuvi (real-time tracking)."""
    driver = models.OneToOneField(
        DeliveryDriver, on_delete=models.CASCADE, related_name='location',
    )
    latitude = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])
    heading = models.FloatField(null=True, blank=True, verbose_name='Yo\'nalish (deg)')
    speed = models.FloatField(null=True, blank=True, verbose_name='Tezlik (m/s)')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'delivery_driver_locations'
        verbose_name = 'Haydovchi joylashuvi'
        verbose_name_plural = 'Haydovchi joylashuvlari'

    def __str__(self):
        return f'{self.driver.full_name}: {self.latitude:.5f}, {self.longitude:.5f}'


# ── Buyurtma holati o'tishlarini tekshirish (validatsiya) ───────────────────────
ORDER_TRANSITIONS = {
    'pending': {'accepted', 'cancelled'},
    'accepted': {'preparing', 'cancelled'},
    'preparing': {'ready', 'cancelled'},
    'ready': {'assigned', 'cancelled'},
    # ready = haydovchi voz kechdi; picked_up = do'kondan oldi
    'assigned': {'picked_up', 'on_the_way', 'ready', 'cancelled'},
    'picked_up': {'on_the_way', 'delivered', 'cancelled'},
    'on_the_way': {'delivered', 'cancelled'},
    'delivered': set(),
    'cancelled': set(),
}


def can_transition(old, new):
    return new in ORDER_TRANSITIONS.get(old, set())
