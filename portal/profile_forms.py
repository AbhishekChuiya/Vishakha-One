import io
import re

from django import forms
from django.core.files.base import ContentFile
from PIL import Image

MAX_PHOTO_BYTES = 3 * 1024 * 1024
NAME_RE = re.compile(r"^[^\W\d_][^\d_<>@/\\{}\[\]=;:!?*#$%^&|~`]*$", re.UNICODE)


class NameForm(forms.Form):
    first_name = forms.CharField(label="First name", max_length=60)
    last_name = forms.CharField(label="Last name", max_length=60, required=False)

    def _clean_part(self, key):
        value = " ".join((self.cleaned_data.get(key) or "").split())
        if value and not NAME_RE.match(value):
            raise forms.ValidationError("Please use letters only.")
        return value

    def clean_first_name(self):
        return self._clean_part("first_name")

    def clean_last_name(self):
        return self._clean_part("last_name")


class PhotoForm(forms.Form):
    photo = forms.ImageField(label="Photo")

    def clean_photo(self):
        f = self.cleaned_data["photo"]
        if f.size > MAX_PHOTO_BYTES:
            raise forms.ValidationError("Photo must be smaller than 3 MB.")
        return f

    def processed(self):
        """Square-crop to 512 px and re-encode, so only a clean JPEG is ever stored."""
        f = self.cleaned_data["photo"]
        img = Image.open(f)
        img = img.convert("RGB")
        side = min(img.size)
        left, top = (img.width - side) // 2, (img.height - side) // 2
        img = img.crop((left, top, left + side, top + side)).resize((512, 512))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=88)
        return ContentFile(buf.getvalue())
