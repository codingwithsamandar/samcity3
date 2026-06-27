import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

VENUE_TYPES = [
    ('wedding', "💍 To'yxona"), ('restaurant', '🍽️ Restoran'), ('barber', '💈 Sartaroshxona'),
    ('gym', '🏋️ Sport zal'), ('cafe', '☕ Kafe'), ('beauty', "💅 Go'zallik saloni"),
    ('other', '📍 Boshqa'),
]
STATUSES = [
    ('pending', 'Kutilmoqda'), ('confirmed', 'Tasdiqlangan'),
    ('cancelled', 'Bekor qilingan'), ('completed', 'Yakunlangan'),
]
EVENT_TYPES = [
    ('wedding', "To'y"), ('birthday', "Tug'ilgan kun"),
    ('engagement', 'Unashtiruv (Fotiha)'), ('other', 'Boshqa'),
]
SUB_TYPES = [('daily', 'Kunlik'), ('monthly', 'Oylik'), ('yearly', 'Yillik')]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Venue',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200, verbose_name='Nomi')),
                ('venue_type', models.CharField(choices=VENUE_TYPES, db_index=True, default='other', max_length=20, verbose_name='Turi')),
                ('description', models.TextField(blank=True, verbose_name='Tavsif')),
                ('address', models.CharField(blank=True, max_length=300, verbose_name='Manzil')),
                ('phone', models.CharField(blank=True, max_length=30, verbose_name='Telefon')),
                ('image', models.ImageField(blank=True, null=True, upload_to='venues/%Y/%m/')),
                ('capacity', models.PositiveIntegerField(blank=True, null=True, verbose_name="Sig'imi (kishi)")),
                ('price_per_day', models.BigIntegerField(blank=True, null=True, verbose_name="Narx (kunlik, so'm)")),
                ('price_per_hour', models.BigIntegerField(blank=True, null=True, verbose_name="Narx (soatlik, so'm)")),
                ('working_hours_start', models.TimeField(blank=True, null=True, verbose_name='Ish boshlanishi')),
                ('working_hours_end', models.TimeField(blank=True, null=True, verbose_name='Ish tugashi')),
                ('is_active', models.BooleanField(default=True, verbose_name='Faol')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='venues', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Joy (venue)',
                'verbose_name_plural': 'Joylar (venues)',
                'db_table': 'venues',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='VenueBooking',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=STATUSES, db_index=True, default='pending', max_length=20)),
                ('booking_date', models.DateField(verbose_name='Sana')),
                ('start_time', models.TimeField(blank=True, null=True, verbose_name='Boshlanish vaqti')),
                ('end_time', models.TimeField(blank=True, null=True, verbose_name='Tugash vaqti')),
                ('guests', models.PositiveIntegerField(default=1, verbose_name='Mehmonlar soni')),
                ('message', models.TextField(blank=True, verbose_name='Xabar')),
                ('total_amount', models.BigIntegerField(blank=True, null=True, verbose_name="Umumiy summa (so'm)")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('event_type', models.CharField(blank=True, choices=EVENT_TYPES, max_length=20, verbose_name='Tadbir turi')),
                ('decoration_needed', models.BooleanField(default=False, verbose_name='Bezatish kerak')),
                ('master_name', models.CharField(blank=True, max_length=120, verbose_name='Usta ismi')),
                ('service_type', models.CharField(blank=True, max_length=120, verbose_name='Xizmat turi')),
                ('table_count', models.PositiveIntegerField(default=1, verbose_name='Stollar soni')),
                ('special_request', models.TextField(blank=True, verbose_name='Maxsus talab')),
                ('subscription_type', models.CharField(blank=True, choices=SUB_TYPES, max_length=20, verbose_name='Obuna turi')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='venue_bookings', to=settings.AUTH_USER_MODEL)),
                ('venue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to='booking.venue')),
            ],
            options={
                'verbose_name': 'Bron',
                'verbose_name_plural': 'Bronlar',
                'db_table': 'venue_bookings',
                'ordering': ['-created_at'],
            },
        ),
    ]
