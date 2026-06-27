import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0006_deliverydriver_order_driver'),
    ]

    operations = [
        migrations.CreateModel(
            name='DriverLocation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.FloatField()),
                ('longitude', models.FloatField()),
                ('heading', models.FloatField(blank=True, null=True, verbose_name="Yo'nalish (deg)")),
                ('speed', models.FloatField(blank=True, null=True, verbose_name='Tezlik (m/s)')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('driver', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='location', to='delivery.deliverydriver',
                )),
            ],
            options={
                'verbose_name': 'Haydovchi joylashuvi',
                'verbose_name_plural': 'Haydovchi joylashuvlari',
                'db_table': 'delivery_driver_locations',
            },
        ),
    ]
