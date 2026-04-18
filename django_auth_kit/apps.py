from django.apps import AppConfig


class DjangoAuthKitConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_auth_kit"
    verbose_name = "Django Auth Kit"

    def ready(self):
        from django_auth_kit import checks  # noqa: F401
