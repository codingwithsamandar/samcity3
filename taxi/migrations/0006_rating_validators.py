import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0005_trip_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicereview',
            name='rating',
            field=models.PositiveSmallIntegerField(
                choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
                default=5, verbose_name='Baho (1-5)', validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5)]),
        ),
        migrations.AlterField(
            model_name='taxistreview',
            name='rating',
            field=models.PositiveSmallIntegerField(
                choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
                default=5, verbose_name='Baho (1-5)', validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5)]),
        ),
    ]
