from django.db import models

class CompanyApplication(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.CharField(max_length=255, blank=True)
    url = models.URLField(max_length=1000, blank=True)
    category = models.CharField(max_length=100, blank=True)
    icon_path = models.CharField(max_length=500, blank=True, default="", help_text="Path relative to static/, e.g. assets/apps/sap.png")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name
