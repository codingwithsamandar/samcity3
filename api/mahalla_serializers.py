"""Mahalla bo'limi — mobil API serializerlari."""
from rest_framework import serializers

from main.models import Neighborhood, NeighborhoodAnnouncement, CitizenRequest


def _abs(request, field):
    if not field:
        return None
    return request.build_absolute_uri(field.url) if request else field.url


class NeighborhoodSerializer(serializers.ModelSerializer):
    centroid = serializers.SerializerMethodField()

    class Meta:
        model = Neighborhood
        fields = ('id', 'name', 'description', 'population', 'head_name', 'head_phone',
                  'color', 'centroid')

    def get_centroid(self, obj):
        return obj.centroid()


class AnnouncementSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = NeighborhoodAnnouncement
        fields = ('id', 'title', 'text', 'image', 'created_at')

    def get_image(self, obj):
        return _abs(self.context.get('request'), obj.image)


class CitizenRequestSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    author = serializers.SerializerMethodField()

    class Meta:
        model = CitizenRequest
        fields = ('id', 'category', 'category_display', 'title', 'text', 'image',
                  'status', 'status_display', 'response', 'author', 'created_at', 'updated_at')

    def get_image(self, obj):
        return _abs(self.context.get('request'), obj.image)

    def get_author(self, obj):
        return obj.user.name or obj.user.phone


class MahallaPlaceMiniSerializer(serializers.Serializer):
    """Do'kon/joy uchun yagona qisqa ko'rinish (xarita/ro'yxat)."""
    id = serializers.CharField()
    name = serializers.CharField()
    category = serializers.CharField()
    category_label = serializers.CharField()
    icon = serializers.CharField()
    address = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    url = serializers.CharField()
