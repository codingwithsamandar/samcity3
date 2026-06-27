import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0002_booking_services_staff_penalty'),
    ]

    operations = [
        migrations.AddField(
            model_name='venuestaff',
            name='bio',
            field=models.TextField(blank=True, verbose_name='Usta haqida'),
        ),
        migrations.AddField(
            model_name='venuestaff',
            name='experience_years',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Tajriba (yil)'),
        ),
        migrations.AddField(
            model_name='venuestaff',
            name='rating',
            field=models.FloatField(default=0, verbose_name='Baho',
                                    validators=[django.core.validators.MinValueValidator(0),
                                                django.core.validators.MaxValueValidator(5)]),
        ),
        migrations.AddField(
            model_name='venuestaff',
            name='reviews_count',
            field=models.PositiveIntegerField(default=0, verbose_name='Sharhlar soni'),
        ),
        migrations.AddField(
            model_name='venuestaff',
            name='completed_count',
            field=models.PositiveIntegerField(default=0, verbose_name='Bajarilgan ishlar'),
        ),
    ]
