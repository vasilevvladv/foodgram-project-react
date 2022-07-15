from django.contrib.admin import ModelAdmin, register

from .models import CustomUser


@register(CustomUser)
class CustomUserAdmin(ModelAdmin):

    list_display = (
        'id', 'username', 'email', 'first_name',
        'last_name', 'password', 'role',
        'is_superuser', 'is_active', 'date_joined',
        'is_staff'
    )
    list_editable = (
        'username', 'email', 'first_name',
        'last_name', 'password', 'role',
        'is_superuser', 'is_active', 'is_staff'
    )
    list_filter = ('email', 'first_name')
    search_fields = ('email', 'first_name')
