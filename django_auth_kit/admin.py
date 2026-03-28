from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from django_auth_kit.models import UserEmail, UserMobile

User = get_user_model()


class UserEmailInline(admin.TabularInline):
    model = UserEmail
    extra = 0
    readonly_fields = ("created_at", "updated_at")


class UserMobileInline(admin.TabularInline):
    model = UserMobile
    extra = 0
    readonly_fields = ("created_at", "updated_at")


class UserAdmin(BaseUserAdmin):
    inlines = [UserEmailInline, UserMobileInline]
    list_display = (
        "username",
        "email",
        "display_name",
        "first_name",
        "last_name",
        "is_staff",
    )
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Auth Kit", {"fields": ("avatar", "display_name")}),
    )


# Only register if AUTH_USER_MODEL points to our model
if User._meta.app_label == "django_auth_kit":
    admin.site.register(User, UserAdmin)


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
