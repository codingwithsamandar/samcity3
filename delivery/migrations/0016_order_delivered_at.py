from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0015_alter_cart_options_cart_is_active_cart_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivered_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Yetkazilgan vaqt'),
        ),
    ]
