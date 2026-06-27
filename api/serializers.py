"""
SamCity mobil API — serializerlar.
Mavjud `main` modellaridan foydalanadi (User, OTPCode, Ad, AdImage).
"""
from rest_framework import serializers

from main.models import User, Ad, AdImage


def normalize_phone(raw: str) -> str:
    """Telefon raqamini standartlash: faqat raqamlar, ixtiyoriy + bilan.
    Mavjud web-logikadagi normalizatsiya bilan bir xil."""
    raw = (raw or '').strip()
    if not raw:
        return ''
    digits = ''.join(filter(str.isdigit, raw))
    return ('+' + digits) if raw.startswith('+') else digits


# ─── User ─────────────────────────────────────────────────────────────────────
class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    avatar_upload = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('id', 'phone', 'name', 'username', 'bio', 'avatar',
                  'avatar_upload', 'role', 'rating', 'created_at')
        read_only_fields = ('id', 'phone', 'role', 'rating', 'created_at')

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.avatar:
            url = obj.avatar.url
            return request.build_absolute_uri(url) if request else url
        return obj.avatar_url or None

    def update(self, instance, validated_data):
        avatar = validated_data.pop('avatar_upload', None)
        if avatar is not None:
            instance.avatar = avatar
        return super().update(instance, validated_data)


# ─── Auth ─────────────────────────────────────────────────────────────────────
class RegisterSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    password = serializers.CharField(min_length=6, write_only=True)

    def validate_phone(self, value):
        phone = normalize_phone(value)
        digits = ''.join(filter(str.isdigit, phone))
        # 9–15 raqam (model regex bilan mos). 'abc123', '+998999', juda uzun — rad.
        if not (9 <= len(digits) <= 15):
            raise serializers.ValidationError(
                "Telefon raqamini to'g'ri kiriting (masalan: +998901234567).")
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("Bu raqam band. Boshqa raqam kiriting.")
        return phone


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_phone(self, value):
        return normalize_phone(value)


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)

    def validate_phone(self, value):
        return normalize_phone(value)


class ResendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        return normalize_phone(value)


# ─── Ads ──────────────────────────────────────────────────────────────────────
class AdImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = AdImage
        fields = ('id', 'image', 'order')

    def get_image(self, obj):
        request = self.context.get('request')
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class AdListSerializer(serializers.ModelSerializer):
    """Ro'yxat uchun yengil serializer (bitta asosiy rasm bilan)."""
    cover = serializers.SerializerMethodField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Ad
        fields = ('id', 'title', 'price', 'price_type', 'category', 'category_display',
                  'location', 'is_boosted', 'views', 'cover', 'created_at')

    def get_cover(self, obj):
        first = obj.images.all().first()
        if not first:
            return None
        request = self.context.get('request')
        url = first.image.url
        return request.build_absolute_uri(url) if request else url


class AdDetailSerializer(serializers.ModelSerializer):
    images = AdImageSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Ad
        fields = ('id', 'user', 'title', 'description', 'price', 'price_type',
                  'category', 'category_display', 'location', 'latitude', 'longitude',
                  'status', 'is_boosted', 'views', 'images',
                  'contact_phone', 'contact_telegram', 'contact_instagram',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'status', 'is_boosted', 'views',
                            'created_at', 'updated_at')


class AdCreateSerializer(serializers.ModelSerializer):
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(), required=False, write_only=True,
    )

    class Meta:
        model = Ad
        fields = ('id', 'title', 'description', 'price', 'price_type', 'category',
                  'location', 'latitude', 'longitude',
                  'contact_phone', 'contact_telegram', 'contact_instagram',
                  'uploaded_images')
        read_only_fields = ('id',)

    def create(self, validated_data):
        images = validated_data.pop('uploaded_images', [])
        ad = Ad.objects.create(user=self.context['request'].user, **validated_data)
        for i, img in enumerate(images[:10]):  # maksimal 10 rasm
            AdImage.objects.create(ad=ad, image=img, order=i)
        return ad
