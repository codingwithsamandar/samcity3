"""Taksi moduli serializerlari."""
from rest_framework import serializers

from taxi.models import TaxiService, Taxist, Route, Car, Trip


def _abs(request, field):
    if not field:
        return None
    url = field.url
    return request.build_absolute_uri(url) if request else url


class TaxiServiceSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    avg_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    example_5km = serializers.IntegerField(read_only=True)

    class Meta:
        model = TaxiService
        fields = ('id', 'name', 'short_number', 'phone', 'logo', 'description',
                  'base_price', 'price_per_km', 'working_hours', 'region',
                  'avg_rating', 'review_count', 'example_5km')

    def get_logo(self, obj):
        return _abs(self.context.get('request'), obj.logo)


class CarSerializer(serializers.ModelSerializer):
    car_class_display = serializers.CharField(source='get_car_class_display', read_only=True)
    photo = serializers.SerializerMethodField()
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Car
        fields = ('brand', 'model', 'full_name', 'color', 'plate_number', 'year',
                  'seats', 'car_class', 'car_class_display',
                  'has_conditioner', 'has_baby_seat', 'allows_pets', 'photo')

    def get_photo(self, obj):
        return _abs(self.context.get('request'), obj.photo)


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ('id', 'point_a', 'point_b', 'passenger_price', 'delivery_price', 'note')


class TaxistListSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()
    avg_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    min_price = serializers.SerializerMethodField()

    class Meta:
        model = Taxist
        fields = ('id', 'full_name', 'phone', 'car_model', 'photo', 'region',
                  'trips_count', 'is_online', 'avg_rating', 'review_count', 'min_price')

    def get_photo(self, obj):
        return _abs(self.context.get('request'), obj.photo)

    def get_min_price(self, obj):
        prices = [r.passenger_price for r in obj.routes.all() if r.is_active]
        return min(prices) if prices else None


class TaxistDetailSerializer(TaxistListSerializer):
    routes = serializers.SerializerMethodField()
    car = CarSerializer(read_only=True)

    class Meta(TaxistListSerializer.Meta):
        fields = TaxistListSerializer.Meta.fields + ('routes', 'car')

    def get_routes(self, obj):
        qs = obj.routes.filter(is_active=True)
        return RouteSerializer(qs, many=True, context=self.context).data


class TripTaxistMiniSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()

    class Meta:
        model = Taxist
        fields = ('id', 'full_name', 'phone', 'car_model', 'photo')

    def get_photo(self, obj):
        return _abs(self.context.get('request'), obj.photo)


class TripSerializer(serializers.ModelSerializer):
    taxist = TripTaxistMiniSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Trip
        fields = ('id', 'point_a', 'point_b', 'is_delivery', 'price',
                  'status', 'status_display', 'payment_method', 'payment_status',
                  'taxist', 'created_at')


class TripCreateSerializer(serializers.Serializer):
    route_id = serializers.UUIDField()
    is_delivery = serializers.BooleanField(default=False)
