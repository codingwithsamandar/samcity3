import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0010_order_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='driverlocation',
            name='latitude',
            field=models.FloatField(validators=[
                django.core.validators.MinValueValidator(-90),
                django.core.validators.MaxValueValidator(90)]),
        ),
        migrations.AlterField(
            model_name='driverlocation',
            name='longitude',
            field=models.FloatField(validators=[
                django.core.validators.MinValueValidator(-180),
                django.core.validators.MaxValueValidator(180)]),
        ),
    ]
