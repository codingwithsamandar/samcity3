"""Mahalla bo'limi — mobil API view'lari.

Web bilan bir xil mantiq (main.community_views), lekin bog'lanish qoidasi ikki xil:
DO'KONLAR — FK bo'yicha (`_stores_in`: Store.neighborhood), JOYLAR esa poligon
(chegara) bo'yicha (`_places_in_grouped`: Neighborhood.contains_point). Bu yerda
avval "ikkalasi ham poligon bo'yicha" deb yozilgan edi — noto'g'ri."""
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from main.utils import check_images

from main.models import (
    Neighborhood, NeighborhoodAnnouncement, CitizenRequest,
    CITIZEN_REQUEST_TRANSITIONS, District, DistrictAnnouncement,
)
from main.community_views import _stores_in, _places_in_grouped
from .mahalla_serializers import (
    NeighborhoodSerializer, AnnouncementSerializer, CitizenRequestSerializer,
    DistrictSerializer, DistrictAnnouncementSerializer,
)


def _store_point(request, s):
    return {
        'id': f'store-{s.pk}', 'name': s.name, 'category': 'delivery_store',
        'category_label': (s.category.name if s.category else "Do'kon"),
        'icon': '🛒', 'address': s.address or '',
        'lat': s.latitude, 'lng': s.longitude,
        'url': request.build_absolute_uri(reverse('delivery:store_detail', args=[s.pk])),
    }


def _place_point(request, p):
    return {
        'id': f'place-{p.pk}', 'name': p.name, 'category': p.category,
        'category_label': p.get_category_display(), 'icon': p.icon,
        'address': p.address or '', 'lat': p.latitude, 'lng': p.longitude,
        'url': request.build_absolute_uri(reverse('places:place_detail', args=[p.pk])),
    }


class MahallaListView(APIView):
    """GET — mahallalar ro'yxati (+ foydalanuvchi mahallasi belgisi)."""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        qs = Neighborhood.objects.all()
        my_id = getattr(request.user, 'neighborhood_id', None) if request.user.is_authenticated else None
        return Response({
            'my_neighborhood': my_id,
            'results': NeighborhoodSerializer(qs, many=True, context={'request': request}).data,
        })


class MahallaDetailView(APIView):
    """GET — bitta mahalla: ma'lumot, e'lonlar, do'konlar, joylar (toifalar), admin belgisi."""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        nb = get_object_or_404(Neighborhood, pk=pk)
        is_admin = nb.is_admin(request.user)
        groups = []
        for g in _places_in_grouped(nb):
            groups.append({
                'key': g['key'], 'label': g['label'],
                'items': [_place_point(request, p) for p in g['items']],
            })
        return Response({
            'neighborhood': NeighborhoodSerializer(nb, context={'request': request}).data,
            'is_admin': is_admin,
            'announcements': AnnouncementSerializer(
                nb.announcements.all()[:30], many=True, context={'request': request}).data,
            'stores': [_store_point(request, s) for s in _stores_in(nb)],
            'place_groups': groups,
        })


class AnnouncementCreateView(APIView):
    """POST — admin rasmiy e'lon joylaydi."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        nb = get_object_or_404(Neighborhood, pk=pk)
        if not nb.is_admin(request.user):
            return Response({'detail': "Faqat mahalla admini."}, status=status.HTTP_403_FORBIDDEN)
        title = (request.data.get('title') or '').strip()
        text = (request.data.get('text') or '').strip()
        if not title or not text:
            return Response({'detail': "Sarlavha va matn majburiy."}, status=status.HTTP_400_BAD_REQUEST)
        img = request.FILES.get('image')
        # Maydondagi `validators=[validate_file_type]` `objects.create()` da
        # ishlamaydi (faqat full_clean'da) — shuning uchun ochiq tekshiramiz.
        err = check_images(img)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        ann = NeighborhoodAnnouncement.objects.create(
            neighborhood=nb, title=title, text=text, created_by=request.user,
            image=img)
        try:
            from main.community_views import _notify_mahalla
            _notify_mahalla(nb, f"📢 Mahalla e'loni: {title[:60]}",
                            reverse('mahalla_detail', args=[pk]), exclude_user=request.user)
        except Exception:
            pass
        return Response(AnnouncementSerializer(ann, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


class HokimPanelView(APIView):
    """GET — foydalanuvchi hokim bo'lgan tuman(lar) + e'lonlar (mobil hokim paneli)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            districts = District.objects.all()
        else:
            districts = District.objects.filter(
                admins__user=request.user).distinct()
        results = []
        for d in districts:
            results.append({
                'district': DistrictSerializer(d, context={'request': request}).data,
                'announcements': DistrictAnnouncementSerializer(
                    d.announcements.all()[:30], many=True,
                    context={'request': request}).data,
            })
        return Response({'is_hokim': bool(results), 'results': results})


class DistrictAnnounceView(APIView):
    """POST — tuman hokimi rasmiy e'lon joylaydi (+ butun tuman aholisiga push)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        district = get_object_or_404(District, pk=pk)
        if not district.is_admin(request.user):
            return Response({'detail': "Faqat tuman hokimi."},
                            status=status.HTTP_403_FORBIDDEN)
        title = (request.data.get('title') or '').strip()
        text = (request.data.get('text') or '').strip()
        if not title or not text:
            return Response({'detail': "Sarlavha va matn majburiy."},
                            status=status.HTTP_400_BAD_REQUEST)
        img = request.FILES.get('image')
        err = check_images(img)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        ann = DistrictAnnouncement.objects.create(
            district=district, title=title, text=text, created_by=request.user,
            image=img)
        try:
            from main.community_views import _notify_district
            sent = _notify_district(
                district, f"🏛️ Tuman e'loni: {title[:60]}",
                reverse('hokim_panel'), exclude_user=request.user)
            ann.recipients_count = sent
            ann.save(update_fields=['recipients_count'])
        except Exception:
            pass
        return Response(
            DistrictAnnouncementSerializer(ann, context={'request': request}).data,
            status=status.HTTP_201_CREATED)


class ComplaintListCreateView(APIView):
    """GET — murojaatlar (admin barchasini, boshqalar o'zinikini); POST — yangi murojaat."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        nb = get_object_or_404(Neighborhood, pk=pk)
        if nb.is_admin(request.user):
            qs = nb.citizen_requests.select_related('user')[:100]
        else:
            qs = nb.citizen_requests.filter(user=request.user)[:50]
        return Response({
            'is_admin': nb.is_admin(request.user),
            'results': CitizenRequestSerializer(qs, many=True, context={'request': request}).data,
        })

    def post(self, request, pk):
        nb = get_object_or_404(Neighborhood, pk=pk)
        title = (request.data.get('title') or '').strip()
        text = (request.data.get('text') or '').strip()
        category = request.data.get('category', 'other')
        if not title or not text:
            return Response({'detail': "Mavzu va matn majburiy."}, status=status.HTTP_400_BAD_REQUEST)
        if category not in dict(CitizenRequest.CATEGORY_CHOICES):
            category = 'other'
        img = request.FILES.get('image')
        err = check_images(img)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        req = CitizenRequest.objects.create(
            neighborhood=nb, user=request.user, category=category,
            title=title, text=text, image=img)
        try:
            from main.community_views import _notify_neighborhood_admins
            _notify_neighborhood_admins(nb, f"🗣 Yangi murojaat: {title[:50]}",
                                        reverse('mahalla_detail', args=[pk]), exclude_user=request.user)
        except Exception:
            pass
        return Response(CitizenRequestSerializer(req, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


class ComplaintStatusView(APIView):
    """POST {status?, response?} — admin murojaat holatini/javobini yangilaydi."""
    permission_classes = [IsAuthenticated]

    def post(self, request, req_id):
        req = get_object_or_404(
            CitizenRequest.objects.select_related('neighborhood', 'user'), pk=req_id)
        nb = req.neighborhood
        if not (nb and nb.is_admin(request.user)):
            return Response({'detail': "Faqat mahalla admini."}, status=status.HTTP_403_FORBIDDEN)
        new_status = request.data.get('status', '')
        response_text = (request.data.get('response') or '').strip()
        changed = False
        if new_status and new_status != req.status:
            if new_status in CITIZEN_REQUEST_TRANSITIONS.get(req.status, set()):
                req.status = new_status
                req.responded_by = request.user
                changed = True
            else:
                return Response({'detail': "Bu holatga o'tib bo'lmaydi."},
                                status=status.HTTP_409_CONFLICT)
        if response_text:
            req.response = response_text
            req.responded_by = request.user
            changed = True
        if changed:
            req.save()
            try:
                from notifications.models import notify
                notify(req.user, f"Murojaatingiz holati: {req.get_status_display()}",
                       reverse('mahalla_detail', args=[nb.pk]), 'system')
            except Exception:
                pass
        return Response(CitizenRequestSerializer(req, context={'request': request}).data)
