"""Mahalla (community) — so'rovnomalar va yordam markazi API."""
from django.db.models import Count
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes as perm
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import (
    Poll, PollOption, PollVote, PollComment, HelpRequest, Neighborhood,
)


def _abs(request, field):
    if not field:
        return None
    return request.build_absolute_uri(field.url) if request else field.url


def _neighborhood(request):
    """?neighborhood=<id> query paramidan mahallani oladi (yoki None)."""
    nid = request.query_params.get('neighborhood') or request.data.get('neighborhood')
    if not nid:
        return None
    return Neighborhood.objects.filter(pk=nid).first()


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
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = ('id', 'question', 'description', 'poll_type', 'is_anonymous',
                  'is_open', 'options', 'total_votes', 'my_votes', 'creator_name',
                  'comment_count', 'created_at')

    def get_my_votes(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []
        return list(PollVote.objects.filter(
            option__poll=obj, user=request.user).values_list('option_id', flat=True))

    def get_creator_name(self, obj):
        return obj.creator.name or obj.creator.phone

    def get_comment_count(self, obj):
        return getattr(obj, 'comment_total', None) or obj.comments.count()


class PollListView(APIView):
    """GET — so'rovnomalar (?neighborhood bilan mahallaga cheklanadi);
    POST — mahalla admini yangi so'rovnoma yaratadi."""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        qs = (Poll.objects.filter(is_active=True)
              .select_related('creator')
              .prefetch_related('options__votes')
              .annotate(comment_total=Count('comments', distinct=True)))
        nb = _neighborhood(request)
        if nb is not None:
            qs = qs.filter(neighborhood=nb)
        ser = PollSerializer(qs, many=True, context={'request': request})
        return Response({
            'is_admin': bool(nb and nb.is_admin(request.user)),
            'results': ser.data,
        })

    def post(self, request):
        nb = _neighborhood(request)
        if nb is None:
            return Response({'detail': 'Mahalla majburiy.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not nb.is_admin(request.user):
            return Response({'detail': "Faqat mahalla admini so'rovnoma ochadi."},
                            status=status.HTTP_403_FORBIDDEN)
        question = (request.data.get('question') or '').strip()
        if not question:
            return Response({'detail': 'Savol majburiy.'},
                            status=status.HTTP_400_BAD_REQUEST)
        options = request.data.get('options') or []
        if isinstance(options, str):
            options = [o.strip() for o in options.split('\n') if o.strip()]
        options = [str(o).strip() for o in options if str(o).strip()]
        # Kiritilmasa — sodda "Ha / Yo'q" so'rovnomasi.
        if len(options) < 2:
            options = ['Ha', "Yo'q"]
        poll = Poll.objects.create(
            neighborhood=nb, creator=request.user, question=question,
            description=(request.data.get('description') or '').strip(),
            poll_type=request.data.get('poll_type', 'single'),
            is_anonymous=str(request.data.get('is_anonymous')).lower() in ('1', 'true', 'on', 'yes'),
        )
        for i, text in enumerate(options[:10]):
            PollOption.objects.create(poll=poll, text=text[:200], order=i)
        try:
            from main.community_views import _notify_mahalla
            from django.urls import reverse
            _notify_mahalla(nb, f"🗳 Yangi so'rovnoma: {question[:60]}",
                            reverse('mahalla_detail', args=[nb.pk]), exclude_user=request.user)
        except Exception:
            pass
        return Response(PollSerializer(poll, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


class PollCommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = PollComment
        fields = ('id', 'text', 'author', 'created_at')

    def get_author(self, obj):
        return obj.user.name or obj.user.phone


@api_view(['GET', 'POST'])
@perm([IsAuthenticatedOrReadOnly])
def poll_comments(request, poll_id):
    """GET — so'rovnoma izohlari; POST {text} — yangi izoh qo'shadi."""
    poll = Poll.objects.filter(pk=poll_id).first()
    if poll is None:
        return Response({'detail': "So'rovnoma topilmadi."}, status=404)
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return Response({'detail': 'Avtorizatsiya kerak.'}, status=401)
        text = (request.data.get('text') or '').strip()
        if not text:
            return Response({'detail': 'Izoh bo\'sh.'}, status=400)
        PollComment.objects.create(poll=poll, user=request.user, text=text)
    qs = poll.comments.select_related('user')
    return Response({'results': PollCommentSerializer(qs, many=True, context={'request': request}).data})


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
        nb = _neighborhood(request)
        if nb is not None:
            qs = qs.filter(neighborhood=nb)
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
            neighborhood=_neighborhood(request),
            kind=request.data.get('kind', 'request'),
            category=request.data.get('category', 'general'),
            location=(request.data.get('location') or '').strip(),
            phone=(request.data.get('phone') or '').strip(),
            is_urgent=str(request.data.get('is_urgent')).lower() in ('1', 'true', 'on'),
        )
        return Response(HelpSerializer(req, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)
