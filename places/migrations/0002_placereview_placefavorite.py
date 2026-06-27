import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('places', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PlaceReview',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(default=5)),
                ('text', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('place', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='places.place')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='place_reviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Joy sharhi', 'verbose_name_plural': 'Joy sharhlari',
                'db_table': 'place_reviews', 'ordering': ['-created_at'],
                'unique_together': {('place', 'user')},
            },
        ),
        migrations.CreateModel(
            name='PlaceFavorite',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('place', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorited_by', to='places.place')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorite_places', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'place_favorites', 'ordering': ['-created_at'],
                'unique_together': {('place', 'user')},
            },
        ),
    ]
