"""Mahalla (community) — so'rovnomalar va yordam markazi API."""
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes as perm
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Poll, PollOption, PollVote, HelpRequest


def _abs(request, field):
    if not field:
        return None
    return request.build_absolute_uri(field.url) if request else field.url


# ─────────────────────── So'rovnomalar ───────────────────────
class PollOptionSerializer(serializers.ModelSerializer):
    votes = serializers.IntegerField(source='vote_count', read_only=True)

    class Meta:
        model = PollOption
        fields = ('id', 'text', 'votes')


class PollSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True, read_only=True)
    total_votes = serializers.IntegerField(read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    my_votes = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = ('id', 'question', 'description', 'poll_type', 'is_anonymous',
                  'is_open', 'options', 'total_votes', 'my_votes', 'creator_name',
                  'created_at')

    def get_my_votes(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []
        return list(PollVote.objects.filter(
            option__poll=obj, user=request.user).values_list('option_id', flat=True))

    def get_creator_name(self, obj):
        return obj.creator.name or obj.creator.phone


class PollListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        qs = (Poll.objects.filter(is_active=True)
              .select_related('creator').prefetch_related('options__votes'))
        ser = PollSerializer(qs, many=True, context={'request': request})
        return Response({'results': ser.data})


@api_view(['POST'])
@perm([IsAuthenticated])
def poll_vote(request, poll_id):
    poll = Poll.objects.filter(pk=poll_id, is_active=True).first()
    if poll is None:
        return Response({'detail': "So'rovnoma topilmadi."}, status=404)
    if not poll.is_open:
        return Response({'detail': "So'rovnoma yopilgan."}, status=400)

    option_ids = request.data.get('options') or []
    if isinstance(request.data.get('option'), (str, int)):
        option_ids = [request.data.get('option')]
    options = list(poll.options.filter(pk__in=option_ids))
    if not options:
        return Response({'detail': 'Variant tanlanmagan.'}, status=400)
    if poll.poll_type == 'single':
        options = options[:1]

    # Avvalgi ovozlarni o'chirib, yangisini yozamiz
    PollVote.objects.filter(option__poll=poll, user=request.user).delete()
    for opt in options:
        PollVote.objects.get_or_create(option=opt, user=request.user)

    return Response(PollSerializer(poll, context={'request': request}).data)


# ─────────────────────── Yordam markazi ───────────────────────
class HelpSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source='get_category_display', read_only=True)
    kind_label = serializers.CharField(source='get_kind_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    image = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()

    class Meta:
        model = HelpRequest
        fields = ('id', 'kind', 'kind_label', 'category', 'category_label',
                  'title', 'description', 'location', 'phone', 'image', 'status',
                  'status_label', 'is_urgent', 'creator_name', 'created_at')
        read_only_fields = ('id', 'status', 'created_at')

    def get_image(self, obj):
        return _abs(self.context.get('request'), obj.image)

    def get_creator_name(self, obj):
        return obj.creator.name or obj.creator.phone


class HelpListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        qs = HelpRequest.objects.select_related('creator').all()
        cat = request.query_params.get('category')
        if cat:
            qs = qs.filter(category=cat)
        ser = HelpSerializer(qs, many=True, context={'request': request})
        return Response({
            'categories': [{'key': k, 'label': v} for k, v in HelpRequest.CATEGORY_CHOICES],
            'results': ser.data,
        })

    def post(self, request):
        title = (request.data.get('title') or '').strip()
        description = (request.data.get('description') or '').strip()
        if not title or not description:
            return Response({'detail': 'Sarlavha va tavsif majburiy.'},
                            status=status.HTTP_400_BAD_REQUEST)
        req = HelpRequest.objects.create(
            creator=request.user, title=title, description=description,
            kind=request.data.get('kind', 'request'),
            category=request.data.get('category', 'general'),
            location=(request.data.get('location') or '').strip(),
            phone=(request.data.get('phone') or '').strip(),
            is_urgent=str(request.data.get('is_urgent')).lower() in ('1', 'true', 'on'),
        )
        return Response(HelpSerializer(req, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)
