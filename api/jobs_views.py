"""Ish e'lonlari va rezyumelar — mobil API."""
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import JobAd, ResumeAd


class JobSerializer(serializers.ModelSerializer):
    job_type_label = serializers.CharField(source='get_job_type_display', read_only=True)

    class Meta:
        model = JobAd
        fields = ('id', 'title', 'company', 'job_type', 'job_type_label',
                  'salary_min', 'salary_max', 'location', 'description',
                  'requirements', 'contact_phone', 'contact_telegram', 'created_at')
        read_only_fields = ('id', 'created_at')


class ResumeSerializer(serializers.ModelSerializer):
    experience_label = serializers.CharField(source='get_experience_display', read_only=True)

    class Meta:
        model = ResumeAd
        fields = ('id', 'title', 'experience', 'experience_label', 'salary_min',
                  'location', 'skills', 'about', 'contact_phone',
                  'contact_telegram', 'created_at')
        read_only_fields = ('id', 'created_at')


class JobListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        qs = JobAd.objects.filter(status='active')
        q = request.query_params.get('search', '').strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(title__icontains=q) | Q(company__icontains=q) |
                           Q(description__icontains=q))
        return Response({'results': JobSerializer(qs, many=True).data})

    def post(self, request):
        d = request.data
        if not (d.get('title') and d.get('company') and d.get('description')):
            return Response({'detail': 'Lavozim, kompaniya va tavsif majburiy.'},
                            status=status.HTTP_400_BAD_REQUEST)
        job = JobAd.objects.create(
            user=request.user, title=d['title'].strip(), company=d['company'].strip(),
            job_type=d.get('job_type', 'full_time'),
            salary_min=_int(d.get('salary_min')), salary_max=_int(d.get('salary_max')),
            location=(d.get('location') or '').strip(),
            description=d['description'].strip(),
            requirements=(d.get('requirements') or '').strip(),
            contact_phone=(d.get('contact_phone') or request.user.phone or '').strip(),
            contact_telegram=(d.get('contact_telegram') or '').strip(),
        )
        return Response(JobSerializer(job).data, status=status.HTTP_201_CREATED)


class ResumeListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        qs = ResumeAd.objects.filter(status='active')
        q = request.query_params.get('search', '').strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(title__icontains=q) | Q(skills__icontains=q) |
                           Q(about__icontains=q))
        return Response({'results': ResumeSerializer(qs, many=True).data})

    def post(self, request):
        d = request.data
        if not (d.get('title') and d.get('about')):
            return Response({'detail': 'Kasb nomi va o\'zingiz haqingizda majburiy.'},
                            status=status.HTTP_400_BAD_REQUEST)
        r = ResumeAd.objects.create(
            user=request.user, title=d['title'].strip(),
            experience=d.get('experience', 'no_exp'),
            salary_min=_int(d.get('salary_min')),
            location=(d.get('location') or '').strip(),
            skills=(d.get('skills') or '').strip(), about=d['about'].strip(),
            contact_phone=(d.get('contact_phone') or request.user.phone or '').strip(),
            contact_telegram=(d.get('contact_telegram') or '').strip(),
        )
        return Response(ResumeSerializer(r).data, status=status.HTTP_201_CREATED)


def _int(v):
    try:
        return int(str(v).replace(' ', '')) if v not in (None, '') else None
    except (ValueError, TypeError):
        return None
