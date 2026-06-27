import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

CATS = [
    ('kommunal', "⚡ Kommunal xizmat"),
    ('kurs', "📚 O'quv kurslari"),
    ('bogcha', "🧸 Bog'cha"),
    ('maktab', "🏫 Maktab / litsey"),
    ('internet', "🌐 Internet / Aloqa"),
    ('boshqa', "📋 Boshqa"),
]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Provider',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200, verbose_name='Nomi')),
                ('category', models.CharField(choices=CATS, db_index=True, max_length=20, verbose_name='Turi')),
                ('description', models.TextField(blank=True, verbose_name='Tavsif')),
                ('address', models.CharField(blank=True, max_length=300, verbose_name='Manzil')),
                ('phone', models.CharField(blank=True, max_length=30, verbose_name='Telefon')),
                ('logo', models.ImageField(blank=True, null=True, upload_to='payments/logos/')),
                ('amount', models.BigIntegerField(default=0, help_text="0 bo'lsa — foydalanuvchi summani o'zi kiritadi (oylik/erkin to'lov)", verbose_name="Belgilangan summa (so'm)")),
                ('region', models.CharField(blank=True, default='Shofirkon', max_length=100, verbose_name='Hudud')),
                ('is_active', models.BooleanField(default=True, verbose_name='Faol')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Muassasa / xizmat',
                'verbose_name_plural': 'Muassasalar / xizmatlar',
                'db_table': 'payments_providers',
                'ordering': ['category', 'name'],
            },
        ),
        migrations.CreateModel(
            name='ServicePayment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('provider_name', models.CharField(max_length=200, verbose_name='Muassasa nomi')),
                ('category', models.CharField(choices=CATS, db_index=True, max_length=20)),
                ('payer_name', models.CharField(blank=True, help_text='Kim uchun (bola ismi, abonent kodi, shartnoma raqami)', max_length=150, verbose_name="To'lovchi / abonent")),
                ('period', models.CharField(blank=True, max_length=20, verbose_name='Davr (YYYY-MM)')),
                ('amount', models.BigIntegerField(verbose_name="Summa (so'm)")),
                ('card_holder', models.CharField(blank=True, max_length=120, verbose_name='Karta egasi')),
                ('card_last4', models.CharField(blank=True, max_length=4)),
                ('card_brand', models.CharField(blank=True, max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Kutilmoqda'), ('paid', "To'langan"), ('failed', 'Xato')], db_index=True, default='pending', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('provider', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payments', to='payments.provider')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': "To'lov",
                'verbose_name_plural': "To'lovlar",
                'db_table': 'payments_records',
                'ordering': ['-created_at'],
            },
        ),
    ]
