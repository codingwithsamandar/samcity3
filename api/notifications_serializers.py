"""Bildirishnomalar (notifications) moduli serializerlari."""
from rest_framework import serializers

from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    icon = serializers.CharField(read_only=True)
    category_label = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            'id', 'text', 'url', 'category', 'category_label',
            'icon', 'is_read', 'created_at',
        )
        read_only_fields = fields

    def get_category_label(self, obj):
        return dict(Notification.CATEGORY_CHOICES).get(obj.category, obj.category)


class MarkReadSerializer(serializers.Serializer):
    """Tanlangan bildirishnomalarni o'qildi qilish uchun (ixtiyoriy id ro'yxati)."""
    ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True,
    )
