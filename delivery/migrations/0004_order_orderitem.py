import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('delivery', '0003_store_logo_phone'),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('full_name', models.CharField(max_length=120, verbose_name='Qabul qiluvchi')),
                ('phone', models.CharField(max_length=30, verbose_name='Telefon')),
                ('address', models.CharField(max_length=300, verbose_name='Yetkazish manzili')),
                ('note', models.TextField(blank=True, verbose_name='Izoh')),
                ('subtotal', models.BigIntegerField(default=0, verbose_name='Mahsulotlar summasi')),
                ('delivery_fee', models.BigIntegerField(default=0, verbose_name='Yetkazish narxi')),
                ('total', models.BigIntegerField(default=0, verbose_name='Umumiy summa')),
                ('status', models.CharField(choices=[('new', 'Yangi'), ('confirmed', 'Tasdiqlangan'), ('delivering', "Yo'lda"), ('delivered', 'Yetkazildi'), ('cancelled', 'Bekor qilingan')], db_index=True, default='new', max_length=20)),
                ('payment_method', models.CharField(choices=[('card', 'Karta'), ('cash', 'Yetkazishda naqd')], default='card', max_length=10)),
                ('payment_status', models.CharField(choices=[('unpaid', "To'lanmagan"), ('paid', "To'langan")], db_index=True, default='unpaid', max_length=10)),
                ('card_last4', models.CharField(blank=True, max_length=4)),
                ('card_brand', models.CharField(blank=True, max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='delivery_orders', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Buyurtma',
                'verbose_name_plural': 'Buyurtmalar',
                'db_table': 'delivery_orders',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('product_name', models.CharField(max_length=200)),
                ('store_name', models.CharField(blank=True, max_length=200)),
                ('price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='delivery.order')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_items', to='delivery.product')),
            ],
            options={
                'verbose_name': 'Buyurtma elementi',
                'verbose_name_plural': 'Buyurtma elementlari',
                'db_table': 'delivery_order_items',
            },
        ),
    ]
