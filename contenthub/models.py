from django.db import models
from django.utils import timezone


class PublishedQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(is_published=True, approval_status='approved', published_at__lte=timezone.now())


class ContentBase(models.Model):
    title = models.CharField(max_length=220)
    summary = models.TextField(blank=True)
    APPROVAL_CHOICES = [
        ('draft', 'Draft'), ('pending', 'Pending approval'),
        ('approved', 'Approved'), ('rejected', 'Changes requested'),
    ]
    # Default approved keeps already-published legacy records visible after migration.
    approval_status = models.CharField(max_length=12, choices=APPROVAL_CHOICES, default='approved', db_index=True)
    submitted_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    reviewed_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(default=timezone.now)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = PublishedQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ('display_order', '-published_at')

    def __str__(self):
        return self.title


class Announcement(ContentBase):
    class Meta(ContentBase.Meta):
        permissions = [('approve_announcement', 'Can approve Announcement content')]

    CATEGORY_CHOICES = [('news', 'Company News'), ('announcement', 'Announcement'), ('recognition', 'Recognition')]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='news')
    image = models.ImageField(upload_to='content/announcements/', blank=True)
    body = models.TextField(blank=True)


class Resource(ContentBase):
    class Meta(ContentBase.Meta):
        permissions = [('approve_resource', 'Can approve Resource content'), ('manage_policy_only', 'Can manage policy resources only')]

    KIND_CHOICES = [('policy', 'Policy'), ('document', 'Document'), ('brochure', 'Brochure')]
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='policy')
    department = models.CharField(max_length=100, blank=True)
    file = models.FileField(upload_to='content/resources/', blank=True)
    external_url = models.URLField(blank=True)

    @property
    def access_url(self):
        return self.file.url if self.file else self.external_url


class JobOpening(ContentBase):
    class Meta(ContentBase.Meta):
        permissions = [('approve_jobopening', 'Can approve JobOpening content')]

    department = models.CharField(max_length=100)
    location = models.CharField(max_length=120)
    employment_type = models.CharField(max_length=80, default='Full-time')
    apply_url = models.URLField(blank=True)
    deadline = models.DateField(null=True, blank=True)


class NewJoiner(ContentBase):
    class Meta(ContentBase.Meta):
        permissions = [('approve_newjoiner', 'Can approve NewJoiner content')]

    employee_name = models.CharField(max_length=150)
    designation = models.CharField(max_length=150)
    department = models.CharField(max_length=100)
    location = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to='content/joiners/', blank=True)
    joining_date = models.DateField(default=timezone.localdate)


class Event(ContentBase):
    class Meta(ContentBase.Meta):
        permissions = [('approve_event', 'Can approve Event content')]

    starts_at = models.DateTimeField()
    location = models.CharField(max_length=150, blank=True)
    image = models.ImageField(upload_to='content/events/', blank=True)


class ContentNotification(models.Model):
    recipient = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='content_notifications')
    actor = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    section = models.CharField(max_length=30)
    object_id = models.PositiveIntegerField()
    title = models.CharField(max_length=220)
    message = models.TextField(blank=True)
    kind = models.CharField(max_length=30)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.title


class ContentAuditEvent(models.Model):
    section = models.CharField(max_length=30, db_index=True)
    object_id = models.PositiveIntegerField(db_index=True)
    actor = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    actor_label = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=24)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-pk')
        indexes = [models.Index(fields=['section', 'object_id', '-created_at'], name='content_audit_lookup')]

    def __str__(self):
        return f'{self.section} #{self.object_id}: {self.action}'


class ApprovalReminderDelivery(models.Model):
    """Idempotency key for a threshold notification within a submission cycle."""
    recipient = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='+')
    section = models.CharField(max_length=30)
    object_id = models.PositiveIntegerField()
    submitted_at = models.DateTimeField()
    threshold_hours = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=['recipient', 'section', 'object_id', 'submitted_at', 'threshold_hours'],
            name='unique_approval_reminder_delivery',
        )]
