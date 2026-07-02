"""Joylar (xarita) — mobil API.

`GET /api/places/?category=<key>&q=<matn>` — faol joylar ro'yxati (xarita markerlari uchun).
Autentifikatsiyasiz (ochiq ma'lumot).
"""
from django.db.models import Q
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from places.models import Place, CATEGORY_CHOICES


def _abs(request, field):
    if not field:
        return ''
    url = field.url
    return request.build_absolute_uri(url) if request else url


class PlaceSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source='get_category_display', read_only=True)
    icon = serializers.ReadOnlyField()
    color = serializers.ReadOnlyField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = ('id', 'name', 'category', 'category_label', 'icon', 'color',
                  'latitude', 'longitude', 'address', 'phone', 'working_hours',
                  'description', 'image')

    def get_image(self, obj):
        return _abs(self.context.get('request'), obj.image)


class PlacesListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        qs = Place.objects.filter(is_active=True)
        cat = request.query_params.get('category', '').strip()
        if cat:
            qs = qs.filter(category=cat)
        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(address__icontains=q))
        ser = PlaceSerializer(qs, many=True, context={'request': request})
        return Response({
            'categories': [{'key': k, 'label': v} for k, v in CATEGORY_CHOICES],
            'results': ser.data,
        })
