from django.contrib import admin

from django_auth_kit.models import UserEmail, UserMobile


class UserEmailInline(admin.TabularInline):
    model = UserEmail
    extra = 0
    readonly_fields = ("created_at", "updated_at")


class UserMobileInline(admin.TabularInline):
    model = UserMobile
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserEmail)
class UserEmailAdmin(admin.ModelAdmin):
    list_display = ("email", "user", "is_verified", "is_primary", "created_at")
    list_filter = ("is_verified", "is_primary")
    search_fields = ("email", "user__username")


@admin.register(UserMobile)
class UserMobileAdmin(admin.ModelAdmin):
    list_display = ("mobile", "user", "is_verified", "is_primary", "created_at")
    list_filter = ("is_verified", "is_primary")
    search_fields = ("mobile", "user__username")
