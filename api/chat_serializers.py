"""Chat (mahalla chat) moduli serializerlari."""
from rest_framework import serializers

from main.models import ChatRoom, ChatMessage


def _abs(request, field):
    if not field:
        return None
    url = field.url
    return request.build_absolute_uri(url) if request else url


class ChatRoomSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='neighborhood.name', read_only=True)
    description = serializers.CharField(source='neighborhood.description', read_only=True)
    member_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    my_status = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ('id', 'name', 'description', 'member_count', 'last_message', 'my_status')

    def get_member_count(self, obj):
        return obj.members.filter(is_approved=True, is_banned=False).count()

    def get_last_message(self, obj):
        msg = obj.messages.filter(is_deleted=False).order_by('-created_at').first()
        if not msg:
            return None
        return {
            'text': msg.text or ('📷 Rasm' if msg.image else '📎 Fayl'),
            'created_at': msg.created_at,
        }

    def get_my_status(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 'guest'
        m = obj.members.filter(user=request.user).first()
        if m is None:
            return 'none'
        if m.is_banned:
            return 'banned'
        return 'approved' if m.is_approved else 'pending'


class ChatUserMiniSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    def get_name(self, obj):
        return obj.name or obj.phone

    def get_avatar(self, obj):
        return _abs(self.context.get('request'), obj.avatar)


class ChatMessageSerializer(serializers.ModelSerializer):
    user = ChatUserMiniSerializer(read_only=True)
    image = serializers.SerializerMethodField()
    reply_to = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ('id', 'text', 'image', 'user', 'is_admin_message',
                  'reply_to', 'is_deleted', 'created_at')

    def get_image(self, obj):
        return _abs(self.context.get('request'), obj.image)

    def get_reply_to(self, obj):
        if not obj.reply_to_id:
            return None
        r = obj.reply_to
        return {
            'id': r.id,
            'text': (r.text[:60] if r.text else '📷 Rasm'),
            'user': (r.user.name or r.user.phone) if r.user_id else '',
        }


class SendMessageSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=4000)
    reply_to = serializers.IntegerField(required=False, allow_null=True)
