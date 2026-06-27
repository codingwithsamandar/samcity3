import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=255)),
                ('url', models.CharField(blank=True, max_length=300)),
                ('category', models.CharField(choices=[('order', 'Buyurtma'), ('booking', 'Bron'), ('taxi', 'Taksi'), ('chat', 'Chat'), ('business', 'Biznes'), ('system', 'Tizim')], default='system', max_length=20)),
                ('is_read', models.BooleanField(db_index=True, default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Bildirishnoma',
                'verbose_name_plural': 'Bildirishnomalar',
                'db_table': 'notifications',
                'ordering': ['-created_at'],
            },
        ),
    ]
