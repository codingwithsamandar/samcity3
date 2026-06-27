"""Booking (joy bron qilish) moduli serializerlari."""
from django.utils import timezone
from rest_framework import serializers

from booking.models import Venue, VenueBooking, VenueService, VenueStaff


def _abs(request, field):
    if not field:
        return None
    url = field.url
    return request.build_absolute_uri(url) if request else url


class VenueServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueService
        fields = ('id', 'name', 'price', 'duration_minutes')


class VenueStaffSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()

    class Meta:
        model = VenueStaff
        fields = ('id', 'name', 'specialty', 'photo', 'bio', 'rating',
                  'reviews_count', 'completed_count', 'experience_years')

    def get_photo(self, obj):
        return _abs(self.context.get('request'), obj.photo)


class VenueListSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    venue_type_display = serializers.CharField(source='get_venue_type_display', read_only=True)

    class Meta:
        model = Venue
        fields = ('id', 'name', 'venue_type', 'venue_type_display', 'address',
                  'phone', 'image', 'capacity', 'price_per_day', 'price_per_hour')

    def get_image(self, obj):
        return _abs(self.context.get('request'), obj.image)


class VenueDetailSerializer(VenueListSerializer):
    booked_dates = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    staff = serializers.SerializerMethodField()
    uses_slots = serializers.BooleanField(read_only=True)
    penalty_percent = serializers.IntegerField(read_only=True)

    class Meta(VenueListSerializer.Meta):
        fields = VenueListSerializer.Meta.fields + (
            'description', 'working_hours_start', 'working_hours_end', 'booked_dates',
            'latitude', 'longitude', 'prepay_required', 'penalty_percent',
            'uses_slots', 'services', 'staff')

    def get_services(self, obj):
        return VenueServiceSerializer(
            obj.services.filter(is_active=True), many=True, context=self.context).data

    def get_staff(self, obj):
        return VenueStaffSerializer(
            obj.staff.filter(is_active=True), many=True, context=self.context).data

    def get_booked_dates(self, obj):
        qs = (obj.bookings
              .filter(status__in=['pending', 'confirmed'],
                      booking_date__gte=timezone.now().date())
              .values_list('booking_date', flat=True))
        return sorted({d.isoformat() for d in qs})


class VenueBookingSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    venue_type = serializers.CharField(source='venue.venue_type', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True, default=None)
    staff_name = serializers.CharField(source='staff.name', read_only=True, default=None)
    penalty_percent = serializers.IntegerField(source='venue.penalty_percent', read_only=True)

    class Meta:
        model = VenueBooking
        fields = ('id', 'venue', 'venue_name', 'venue_type', 'status', 'status_display',
                  'booking_date', 'start_time', 'end_time', 'guests',
                  'message', 'total_amount', 'paid_amount', 'penalty_amount',
                  'refund_amount', 'penalty_percent', 'service_name', 'staff_name',
                  'event_type', 'created_at')


class BookingCreateSerializer(serializers.Serializer):
    booking_date = serializers.DateField()
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    guests = serializers.IntegerField(required=False, min_value=1, default=1)
    message = serializers.CharField(required=False, allow_blank=True, default='')
    service = serializers.UUIDField(required=False, allow_null=True)
    staff = serializers.UUIDField(required=False, allow_null=True)
    # Joy turiga qarab ixtiyoriy maydonlar
    event_type = serializers.CharField(required=False, allow_blank=True, default='')
    decoration_needed = serializers.BooleanField(required=False, default=False)
    master_name = serializers.CharField(required=False, allow_blank=True, default='')
    service_type = serializers.CharField(required=False, allow_blank=True, default='')
    table_count = serializers.IntegerField(required=False, min_value=1, default=1)
    special_request = serializers.CharField(required=False, allow_blank=True, default='')
    subscription_type = serializers.CharField(required=False, allow_blank=True, default='')
