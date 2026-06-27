import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_business_review_transport'),
    ]

    operations = [

        # ── Task 15: Yangi business kategoriyalar ────────────────────────────
        migrations.AlterField(
            model_name='business',
            name='kategoriya',
            field=models.CharField(
                choices=[
                    ('kafe',       '☕ Kafe / Restoran'),
                    ('dorixona',   '💊 Dorixona'),
                    ('klinika',    '🏥 Klinika / Shifokor'),
                    ('salon',      "💇 Go'zallik saloni"),
                    ('do_kon',     "🛒 Do'kon"),
                    ('restoran',   '🍽️ Restoran'),
                    ('ustaxona',   "🔧 Ustaxona / Ta'mirxona"),
                    ('bank',       '🏦 Bank / Moliya'),
                    ('maktab',     "🏫 Maktab / O'quv markazi"),
                    ('sport',      '🏋️ Sport / Fitnes'),
                    ('gozallik',   "💅 Go'zallik / Kosmetika"),
                    ('mehmonxona', '🏨 Mehmonxona / Hotel'),
                    ('boshqa',     '🏢 Boshqa'),
                ],
                db_index=True,
                max_length=20,
            ),
        ),

        # ── Task 17: BusinessImage modeli ────────────────────────────────────
        migrations.CreateModel(
            name='BusinessImage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('image', models.ImageField(upload_to='businesses/%Y/%m/gallery/')),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('business', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='images',
                    to='main.business',
                )),
            ],
            options={
                'verbose_name': 'Biznes rasmi',
                'verbose_name_plural': 'Biznes rasmlari',
                'db_table': 'business_images',
                'ordering': ['order'],
            },
        ),
    ]
