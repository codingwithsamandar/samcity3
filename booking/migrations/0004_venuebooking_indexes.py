from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0003_venuestaff_profile'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='venuebooking',
            index=models.Index(fields=['staff', 'booking_date'], name='vb_staff_date_idx'),
        ),
        migrations.AddIndex(
            model_name='venuebooking',
            index=models.Index(fields=['venue', 'booking_date'], name='vb_venue_date_idx'),
        ),
        migrations.AddIndex(
            model_name='venuebooking',
            index=models.Index(fields=['user', '-created_at'], name='vb_user_created_idx'),
        ),
    ]
