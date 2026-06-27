from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0002_car_trip_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxist', name='is_online',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Onlayn (buyurtma qabul qiladi)'),
        ),
        migrations.AddField(model_name='taxist', name='latitude', field=models.FloatField(blank=True, null=True)),
        migrations.AddField(model_name='taxist', name='longitude', field=models.FloatField(blank=True, null=True)),
        migrations.AddField(model_name='taxist', name='location_updated_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='trip', name='pickup_lat', field=models.FloatField(blank=True, null=True)),
        migrations.AddField(model_name='trip', name='pickup_lng', field=models.FloatField(blank=True, null=True)),
        migrations.AddField(model_name='trip', name='dest_lat', field=models.FloatField(blank=True, null=True)),
        migrations.AddField(model_name='trip', name='dest_lng', field=models.FloatField(blank=True, null=True)),
        migrations.AddField(model_name='trip', name='distance_km', field=models.FloatField(blank=True, null=True)),
    ]
