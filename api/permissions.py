from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """O'qish hammaga ochiq; o'zgartirish/o'chirish faqat egasi uchun."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = getattr(obj, 'user', None)
        return owner is not None and owner == request.user
