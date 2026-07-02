"""Do'kon xodimi bilan chat — mobil API serializerlari."""
from rest_framework import serializers

from delivery.models import StoreChatThread, StoreChatMessage


class StoreChatMessageSerializer(serializers.ModelSerializer):
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = StoreChatMessage
        fields = ('id', 'text', 'sender', 'is_owner', 'is_read', 'created_at')

    def get_is_owner(self, obj):
        return obj.sender_id == obj.thread.store.owner_id


class StoreChatThreadSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_id = serializers.IntegerField(source='store.pk', read_only=True)
    customer_name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = StoreChatThread
        fields = ('id', 'store_id', 'store_name', 'customer', 'customer_name',
                  'last_message', 'unread_count', 'updated_at', 'created_at')

    def get_customer_name(self, obj):
        return obj.customer.name or obj.customer.phone

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        return msg.text if msg else ''

    def get_unread_count(self, obj):
        user = getattr(self.context.get('request'), 'user', None)
        if not user:
            return 0
        return obj.messages.exclude(sender=user).filter(is_read=False).count()
