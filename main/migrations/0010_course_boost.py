import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_business_categories_images'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ── Task 21: Course modeli ────────────────────────────────────────────
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nomi', models.CharField(max_length=200, verbose_name='Kurs nomi')),
                ('kategoriya', models.CharField(
                    choices=[
                        ('til',    "🌍 Til kurslari (ingliz, rus, arab...)"),
                        ('maktab', '📚 Maktab fanlari (matematika, fizika...)'),
                        ('kasb',   '💼 Kasb kurslari (IT, dizayn, muhasib...)'),
                        ('sport',  '🏋️ Sport / Jismoniy tarbiya'),
                        ('sanaat', "🎨 San'at / Musiqa / Raqs"),
                        ('boshqa', '📋 Boshqa'),
                    ],
                    db_index=True,
                    max_length=20,
                )),
                ('format', models.CharField(
                    choices=[
                        ('offline', '🏫 Offline (bevosita)'),
                        ('online',  '💻 Online (masofaviy)'),
                        ('gibrid',  '🔀 Gibrid (aralash)'),
                    ],
                    default='offline',
                    max_length=10,
                )),
                ('tavsif', models.TextField(blank=True, verbose_name='Tavsif')),
                ('telefon', models.CharField(blank=True, max_length=20)),
                ('telegram', models.CharField(blank=True, max_length=100)),
                ('manzil', models.CharField(blank=True, max_length=300)),
                ('narx', models.BigIntegerField(blank=True, null=True, verbose_name="Narx (so'm / oyiga)")),
                ('narx_bepul', models.BooleanField(default=False, verbose_name='Bepul')),
                ('davomiyligi', models.CharField(blank=True, max_length=100, verbose_name='Davomiylik (mas: 3 oy)')),
                ('ish_vaqti', models.CharField(blank=True, max_length=150, verbose_name='Dars vaqti')),
                ('rasm', models.ImageField(blank=True, null=True, upload_to='courses/%Y/%m/')),
                ('views', models.PositiveIntegerField(default=0)),
                ('status', models.CharField(
                    choices=[('active', 'Faol'), ('inactive', 'Faol emas'), ('deleted', "O'chirilgan")],
                    db_index=True,
                    default='active',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='courses',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Kurs',
                'verbose_name_plural': 'Kurslar',
                'db_table': 'courses',
                'ordering': ['-created_at'],
            },
        ),

        # ── Task 23: BoostPayment modeli ──────────────────────────────────────
        migrations.CreateModel(
            name='BoostPayment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('plan', models.CharField(
                    choices=[
                        ('week',    "7 kunlik — 10,000 so'm"),
                        ('month',   "30 kunlik — 30,000 so'm"),
                        ('quarter', "90 kunlik — 75,000 so'm"),
                    ],
                    max_length=20,
                )),
                ('amount', models.BigIntegerField(verbose_name="To'lov summasi (so'm)")),
                ('status', models.CharField(
                    choices=[
                        ('pending',   'Kutilmoqda'),
                        ('active',    'Faol'),
                        ('expired',   'Muddati tugagan'),
                        ('cancelled', 'Bekor qilindi'),
                    ],
                    db_index=True,
                    default='pending',
                    max_length=20,
                )),
                ('starts_at', models.DateTimeField(blank=True, null=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ad', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='boosts',
                    to='main.ad',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='boost_payments',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': "Boost to'lov",
                'verbose_name_plural': "Boost to'lovlar",
                'db_table': 'boost_payments',
                'ordering': ['-created_at'],
            },
        ),
    ]
