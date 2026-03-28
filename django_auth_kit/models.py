import uuid

from django.conf import settings
from django.db import models, transaction


class UserEmail(models.Model):
    """Email addresses associated with a user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emails",
    )
    email = models.EmailField(db_index=True)
    is_verified = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "email")]
        ordering = ["-is_primary", "-created_at"]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.is_primary:
                UserEmail.objects.filter(user=self.user, is_primary=True).exclude(
                    pk=self.pk
                ).update(is_primary=False)

    def __str__(self) -> str:
        primary = " (primary)" if self.is_primary else ""
        verified = " [verified]" if self.is_verified else ""
        return f"{self.email}{primary}{verified}"


class UserMobile(models.Model):
    """Mobile numbers associated with a user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mobiles",
    )
    mobile = models.CharField(max_length=20, db_index=True)
    is_verified = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "mobile")]
        ordering = ["-is_primary", "-created_at"]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.is_primary:
                UserMobile.objects.filter(user=self.user, is_primary=True).exclude(
                    pk=self.pk
                ).update(is_primary=False)

    def __str__(self) -> str:
        primary = " (primary)" if self.is_primary else ""
        verified = " [verified]" if self.is_verified else ""
        return f"{self.mobile}{primary}{verified}"
