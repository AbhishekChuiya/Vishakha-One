from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Announcement, Resource, JobOpening, NewJoiner, Event

MAX_UPLOAD = 10 * 1024 * 1024
VIDEO_EXTENSIONS = {'.mp4', '.webm'}
MAX_VIDEO_UPLOAD = 100 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.png', '.jpg', '.jpeg', '.webp'}


class FriendlyForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'cm-input')
            if name == 'summary':
                field.widget.attrs.setdefault('rows', 3)
            if name == 'body':
                field.widget.attrs.setdefault('rows', 6)
            if name == 'published_at':
                field.widget = forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'cm-input'}, format='%Y-%m-%dT%H:%M')
                field.input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S']
                if self.instance and self.instance.pk and self.instance.published_at:
                    field.initial = timezone.localtime(self.instance.published_at).strftime('%Y-%m-%dT%H:%M')
            if name == 'starts_at':
                field.widget = forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'cm-input'}, format='%Y-%m-%dT%H:%M')
                field.input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S']
                if self.instance and self.instance.pk and self.instance.starts_at:
                    field.initial = timezone.localtime(self.instance.starts_at).strftime('%Y-%m-%dT%H:%M')
            if name in ('deadline', 'joining_date'):
                field.widget = forms.DateInput(attrs={'type': 'date', 'class': 'cm-input'}, format='%Y-%m-%d')
                field.input_formats = ['%Y-%m-%d']
                val = getattr(self.instance, name, None)
                if val:
                    field.initial = val.strftime('%Y-%m-%d')
        # Publishing is controlled by the three clear action buttons, not a checkbox.
        self.fields.pop('is_published', None)
        if 'display_order' in self.fields:
            self.fields['display_order'].label = 'Display priority (optional)'
            self.fields['display_order'].help_text = '0 is the default. Lower numbers appear first.'
        if 'published_at' in self.fields:
            self.fields['published_at'].label = 'Scheduled publishing date and time'
            self.fields['published_at'].required = False
            self.fields['published_at'].help_text = 'Only needed if you click Schedule. Publish now uses the current time.'
        for key in ('image', 'photo', 'file', 'cover_image'):
            if key in self.fields:
                self.fields[key].widget.attrs['data-upload-preview'] = '1'
                self.fields[key].help_text = 'Maximum 10 MB. Images: JPG/PNG/WebP. Documents: PDF, Word, Excel or PowerPoint.'

    def clean(self):
        data = super().clean()
        for field_name in ('image', 'photo', 'file', 'cover_image'):
            uploaded = data.get(field_name)
            if uploaded and hasattr(uploaded, 'size'):
                if uploaded.size > (MAX_VIDEO_UPLOAD if field_name == 'file' and data.get('kind') == 'video' else MAX_UPLOAD):
                    self.add_error(field_name, 'Video files must be 100 MB or smaller; other files must be 10 MB or smaller.')
                if field_name == 'file':
                    import os
                    ext = os.path.splitext(uploaded.name)[1].lower()
                    if ext not in (VIDEO_EXTENSIONS if data.get('kind') == 'video' else ALLOWED_EXTENSIONS):
                        self.add_error(field_name, 'For Company Videos, upload MP4 or WebM. Other resources accept PDF, Office, PNG, JPG, JPEG or WebP.')
                elif field_name in ('image', 'photo', 'cover_image'):
                    from django.core.files.images import get_image_dimensions
                    try:
                        get_image_dimensions(uploaded)
                    except Exception:
                        self.add_error(field_name, 'Please upload a valid image.')
        return data


class AnnouncementForm(FriendlyForm):
    def clean(self):
        data = super().clean()
        if data.get('category') == 'gallery' and not (data.get('image') or getattr(self.instance, 'image', None)):
            self.add_error('image', 'Please upload a photograph for a gallery entry.')
        return data

    class Meta:
        model = Announcement
        fields = ('title', 'category', 'summary', 'body', 'image', 'is_published', 'published_at', 'display_order')


class ResourceForm(FriendlyForm):
    class Meta:
        model = Resource
        fields = ('title', 'kind', 'department', 'summary', 'cover_image', 'file', 'external_url', 'is_published', 'published_at', 'display_order')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'file' in self.fields:
            self.fields['file'].widget.attrs['accept'] = '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.png,.jpg,.jpeg,.webp,.mp4,.webm'
            self.fields['file'].help_text = 'Upload PDF, Office document or image (max 10 MB); Company Videos: MP4/WebM (max 100 MB).'
        if 'cover_image' in self.fields:
            self.fields['cover_image'].widget.attrs['accept'] = '.png,.jpg,.jpeg,.webp'
            self.fields['cover_image'].help_text = 'Optional cover/preview image: PNG, JPG, JPEG or WebP (max 10 MB).'

    def clean(self):
        data = super().clean()
        if not data.get('file') and not data.get('external_url') and not getattr(self.instance, 'file', None):
            raise ValidationError('Please upload a file or provide a link.')
        return data


class JobOpeningForm(FriendlyForm):
    class Meta:
        model = JobOpening
        fields = ('title', 'department', 'location', 'employment_type', 'apply_url', 'deadline', 'summary', 'is_published', 'published_at', 'display_order')


class NewJoinerForm(FriendlyForm):
    def clean_introduction_document(self):
        uploaded = self.cleaned_data.get('introduction_document')
        if not uploaded:
            return uploaded
        from pathlib import Path
        suffix = Path(uploaded.name).suffix.lower()
        if suffix not in {'.pdf', '.png', '.jpg', '.jpeg', '.webp'}:
            raise forms.ValidationError('Upload a PDF or image (PNG, JPG, JPEG, WebP).')
        if uploaded.size > 15 * 1024 * 1024:
            raise forms.ValidationError('Introduction document must be 15 MB or smaller.')
        return uploaded

    class Meta:
        model = NewJoiner
        fields = ('employee_name', 'designation', 'department', 'location', 'joining_date', 'photo', 'introduction_document', 'title', 'summary', 'is_published', 'published_at', 'display_order')


class EventForm(FriendlyForm):
    class Meta:
        model = Event
        fields = ('title', 'starts_at', 'location', 'summary', 'image', 'is_published', 'published_at', 'display_order')
