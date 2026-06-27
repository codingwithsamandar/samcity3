# Generated manually 2026-06-12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0002_cart_cartitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to='delivery/stores/', verbose_name='Logo'),
        ),
        migrations.AddField(
            model_name='store',
            name='phone',
            field=models.CharField(blank=True, max_length=20, verbose_name='Telefon'),
        ),
    ]
