import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

CATS = [
    ('furniture', "Mebel do'konlari"), ('electronics', 'Elektronika do\'konlari'),
    ('tourist', 'Diqqatga sazovor joylar'), ('government', 'Davlat binolari'),
    ('organization', 'Tashkilot ofislari'), ('post', "Pochta bo'limlari"),
    ('bank', 'Banklar'), ('pharmacy', 'Dorixonalar'), ('hospital', 'Shifoxonalar'),
    ('hotel', 'Mehmonxonalar'), ('wedding', "To'yxonalar"), ('restaurant', 'Restoranlar'),
    ('delivery_store', "Do'konlar"),
]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Place',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Nomi')),
                ('category', models.CharField(choices=CATS, db_index=True, max_length=30, verbose_name='Toifa')),
                ('description', models.TextField(blank=True, verbose_name='Tavsif')),
                ('latitude', models.FloatField(verbose_name='Kenglik (latitude)')),
                ('longitude', models.FloatField(verbose_name='Uzunlik (longitude)')),
                ('address', models.CharField(blank=True, max_length=300, verbose_name='Manzil')),
                ('phone', models.CharField(blank=True, max_length=40, verbose_name='Telefon')),
                ('working_hours', models.CharField(blank=True, max_length=120, verbose_name='Ish vaqti')),
                ('website', models.URLField(blank=True, verbose_name='Veb-sayt')),
                ('image', models.ImageField(blank=True, null=True, upload_to='places/%Y/%m/')),
                ('is_active', models.BooleanField(default=True, verbose_name='Faol')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='places', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Joy (xarita)',
                'verbose_name_plural': 'Joylar (xarita)',
                'db_table': 'places',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='PlaceImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='places/gallery/%Y/%m/')),
                ('place', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='places.place')),
            ],
            options={
                'verbose_name': 'Joy rasmi',
                'verbose_name_plural': 'Joy rasmlari',
                'db_table': 'place_images',
            },
        ),
    ]
