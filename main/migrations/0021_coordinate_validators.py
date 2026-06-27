import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0020_alter_adimage_image_alter_otpcode_code_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ad',
            name='latitude',
            field=models.FloatField(blank=True, null=True, validators=[
                django.core.validators.MinValueValidator(-90),
                django.core.validators.MaxValueValidator(90)]),
        ),
        migrations.AlterField(
            model_name='ad',
            name='longitude',
            field=models.FloatField(blank=True, null=True, validators=[
                django.core.validators.MinValueValidator(-180),
                django.core.validators.MaxValueValidator(180)]),
        ),
        migrations.AlterField(
            model_name='helprequest',
            name='latitude',
            field=models.FloatField(blank=True, null=True, validators=[
                django.core.validators.MinValueValidator(-90),
                django.core.validators.MaxValueValidator(90)]),
        ),
        migrations.AlterField(
            model_name='helprequest',
            name='longitude',
            field=models.FloatField(blank=True, null=True, validators=[
                django.core.validators.MinValueValidator(-180),
                django.core.validators.MaxValueValidator(180)]),
        ),
    ]
