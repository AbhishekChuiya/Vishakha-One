from django.core.exceptions import ValidationError
from django.db import models

class CompanyApplication(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.CharField(max_length=255, blank=True)
    url = models.URLField(max_length=1000, blank=True)
    category = models.CharField(max_length=100, blank=True)
    icon_path = models.CharField(max_length=500, blank=True, default="", help_text="Path relative to static/, e.g. assets/apps/sap.png")
    logo = models.ImageField(upload_to="app_logos/", blank=True, null=True,
                             help_text="Upload a sharp logo (PNG/SVG-like, ideally 256x256 or larger, transparent background). Overrides the built-in icon.")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name

    @property
    def logo_url(self):
        try:
            return self.logo.url if self.logo else ""
        except ValueError:
            return ""


LINK_ICONS = [
    ("search", "Search"), ("file", "Document"), ("folder", "Folder"), ("users", "People"), ("briefcase", "Briefcase"),
    ("award", "Award"), ("image", "Photos"), ("play", "Video"), ("card", "Card / bank"), ("link", "Link"),
    ("star", "Star"), ("calendar", "Calendar"), ("bell", "Bell"), ("utensils", "Canteen"), ("lifebuoy", "Help"),
    ("grid", "Apps"), ("news", "News"), ("home", "Home"), ("settings", "Settings"), ("sparkles", "Sparkles"),
]


def validate_link_url(value):
    """Only site paths or http(s) addresses: never javascript:, data: and similar."""
    value = (value or "").strip()
    if value.startswith("/") and not value.startswith("//"):
        return
    if value.lower().startswith(("https://", "http://")):
        return
    raise ValidationError("Use a page on this site (starting with /) or a full https:// address.")


class HelpfulLink(models.Model):
    """A shortcut in the 'Helpful links' bar under the header. Managed by administrators."""
    title = models.CharField(max_length=60)
    url = models.CharField(max_length=300, validators=[validate_link_url],
                           help_text="A page on this site such as /policies/ or a full https:// address.")
    icon = models.CharField(max_length=30, choices=LINK_ICONS, default="link")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "title"]
        verbose_name = "helpful link"
        verbose_name_plural = "helpful links"

    def __str__(self):
        return self.title

    @property
    def is_external(self):
        return self.url.lower().startswith(("http://", "https://"))


class PushSubscription(models.Model):
    """One browser/device that agreed to receive notifications for a user."""
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.CharField(max_length=600, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_success_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} @ {self.endpoint[:40]}"
