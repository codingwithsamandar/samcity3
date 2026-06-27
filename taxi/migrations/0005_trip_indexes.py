from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0004_alter_taxist_latitude_alter_taxist_longitude_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='trip',
            index=models.Index(fields=['passenger', '-created_at'], name='trip_passenger_created_idx'),
        ),
        migrations.AddIndex(
            model_name='trip',
            index=models.Index(fields=['taxist', 'status'], name='trip_taxist_status_idx'),
        ),
    ]
