from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Custom-user create form (phone-based). Used by the admin "Add user" page.

    `UserCreationForm` already declares the `password1`/`password2` fields, so
    `Meta.fields` lists only real model fields.
    """
    email = forms.EmailField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        # 'role' admin add_fieldsets'da ko'rsatilgani uchun shu yerda ham bo'lishi shart
        fields = ("phone", "name", "email", "role")


class CustomUserChangeForm(UserChangeForm):
    """Custom-user change form (admin user edit page). Provides the read-only
    password hash widget and binds to the custom User model."""

    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
