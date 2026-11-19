import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


class Command(BaseCommand):
    help = "Create the VAPID key pair used for browser push notifications. Run once; keep the private key secret."

    def handle(self, *args, **options):
        key = ec.generate_private_key(ec.SECP256R1())
        private = b64url(key.private_numbers().private_value.to_bytes(32, "big"))
        public = b64url(key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
        self.stdout.write("Add these two lines to your environment file (.env.<name>), then restart the application:\n")
        self.stdout.write(f"VONE_VAPID_PUBLIC_KEY={public}")
        self.stdout.write(f"VONE_VAPID_PRIVATE_KEY={private}")
        self.stdout.write("VONE_VAPID_SUBJECT=mailto:your-it-support@vishakha.com\n")
        self.stdout.write(self.style.WARNING("Keep the private key secret and never commit it. Changing the keys later makes every employee allow notifications again."))
