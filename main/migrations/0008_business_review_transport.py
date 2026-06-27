import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_booking_payment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ── Task 01: related_name clash tuzatish ─────────────────────────────
        migrations.AlterField(
            model_name='user',
            name='groups',
            field=models.ManyToManyField(
                blank=True,
                related_name='main_user_set',
                related_query_name='main_user',
                to='auth.group',
                verbose_name='groups',
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='user_permissions',
            field=models.ManyToManyField(
                blank=True,
                related_name='main_user_set',
                related_query_name='main_user',
                to='auth.permission',
                verbose_name='user permissions',
            ),
        ),

        # ── Task 02: Business modeli ──────────────────────────────────────────
        migrations.CreateModel(
            name='Business',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nomi', models.CharField(max_length=200, verbose_name='Biznes nomi')),
                ('kategoriya', models.CharField(
                    choices=[
                        ('kafe',     '☕ Kafe / Restoran'),
                        ('dorixona', '💊 Dorixona'),
                        ('klinika',  '🏥 Klinika / Shifokor'),
                        ('salon',    "💇 Go'zallik saloni"),
                        ('do_kon',   "🛒 Do'kon"),
                        ('restoran', '🍽️ Restoran'),
                        ('boshqa',   '🏢 Boshqa'),
                    ],
                    db_index=True,
                    max_length=20,
                )),
                ('telefon', models.CharField(blank=True, max_length=20)),
                ('manzil', models.CharField(blank=True, max_length=300)),
                ('ish_vaqti', models.CharField(blank=True, max_length=100, verbose_name='Ish vaqti')),
                ('tavsif', models.TextField(blank=True)),
                ('rasm', models.ImageField(blank=True, null=True, upload_to='businesses/%Y/%m/')),
                ('lat', models.FloatField(blank=True, null=True)),
                ('lng', models.FloatField(blank=True, null=True)),
                ('is_verified', models.BooleanField(default=False)),
                ('is_featured', models.BooleanField(default=False)),
                ('views', models.PositiveIntegerField(default=0)),
                ('status', models.CharField(
                    choices=[
                        ('pending',  'Kutilmoqda'),
                        ('active',   'Faol'),
                        ('rejected', 'Rad etilgan'),
                        ('closed',   'Yopilgan'),
                    ],
                    db_index=True,
                    default='pending',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='businesses',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Biznes',
                'verbose_name_plural': 'Bizneslar',
                'db_table': 'businesses',
                'ordering': ['-is_featured', '-created_at'],
            },
        ),

        # ── Task 03: Review modeli ────────────────────────────────────────────
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('yulduz', models.PositiveSmallIntegerField(
                    choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
                    verbose_name='Yulduz (1–5)',
                )),
                ('izoh', models.TextField(blank=True, verbose_name='Izoh')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('business', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='reviews',
                    to='main.business',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='reviews',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Sharh',
                'verbose_name_plural': 'Sharhlar',
                'db_table': 'reviews',
                'ordering': ['-created_at'],
                'unique_together': {('business', 'user')},
            },
        ),

        # ── Task 04: Transport modeli ─────────────────────────────────────────
        migrations.CreateModel(
            name='Transport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('ism', models.CharField(max_length=100, verbose_name='Haydovchi ismi')),
                ('telefon', models.CharField(max_length=20)),
                ('kategoriya', models.CharField(
                    choices=[
                        ('taxi',         '🚕 Taxi'),
                        ('yuk',          '🚚 Yuk tashish'),
                        ('shaharlararo', "🛣️ Shaharlararo"),
                        ('transfer',     '✈️ Transfer (aeroport)'),
                        ('boshqa',       '🚗 Boshqa'),
                    ],
                    db_index=True,
                    max_length=20,
                )),
                ('mashina_turi', models.CharField(blank=True, max_length=100, verbose_name='Mashina turi/modeli')),
                ('marshrut', models.CharField(blank=True, max_length=200, verbose_name='Marshrut / hudud')),
                ('ish_vaqti', models.CharField(blank=True, max_length=100, verbose_name='Ish vaqti')),
                ('narx', models.BigIntegerField(blank=True, null=True, verbose_name="Narx (so'm)")),
                ('rasm', models.ImageField(blank=True, null=True, upload_to='transport/%Y/%m/')),
                ('is_active', models.BooleanField(default=True)),
                ('status', models.CharField(
                    choices=[
                        ('active',   'Faol'),
                        ('inactive', 'Faol emas'),
                        ('deleted',  "O'chirilgan"),
                    ],
                    db_index=True,
                    default='active',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('driver', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='transports',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Transport',
                'verbose_name_plural': 'Transportlar',
                'db_table': 'transports',
                'ordering': ['-created_at'],
            },
        ),
    ]
