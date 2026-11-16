import os
import ssl
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse

from portal import saml_support


class Command(BaseCommand):
    help = (
        "Show exactly what company SSO will send to Microsoft and what must be registered in Entra. "
        "Read-only; prints no secrets."
    )

    def add_arguments(self, parser):
        parser.add_argument("--host", default="localhost:8000",
                            help="Address you browse the site at, e.g. localhost:8000 or one.vishakha.live")
        parser.add_argument("--scheme", default=None, choices=["http", "https"],
                            help="Default: http for localhost/127.0.0.1, otherwise https")

    def handle(self, *args, **options):
        out = self.stdout.write
        host = options["host"]
        scheme = options["scheme"] or ("http" if host.split(":")[0] in ("localhost", "127.0.0.1") else "https")

        def line(ok, good, bad):
            out(self.style.SUCCESS("  OK   " + good) if ok else self.style.ERROR("  FAIL " + bad))
            return ok

        out(f"Checking SSO as seen when you browse {scheme}://{host}\n")
        try:
            import onelogin.saml2.auth  # noqa: F401
            lib = True
        except ImportError:
            lib = False
        line(lib, "python3-saml is installed", "python3-saml is NOT installed (pip install python3-saml==1.16.0)")
        line(bool(settings.VONE_SAML_TENANT_ID), f"tenant id: {settings.VONE_SAML_TENANT_ID}", "no tenant id")

        cert_path = Path(settings.VONE_SAML_IDP_CERT_FILE)
        cert_ok = cert_path.is_file()
        line(cert_ok, f"signing certificate file found ({cert_path.name})", f"certificate file missing: {cert_path}")
        if cert_ok and lib:
            from onelogin.saml2.utils import OneLogin_Saml2_Utils
            thumb = (OneLogin_Saml2_Utils.calculate_x509_fingerprint(cert_path.read_text(encoding="utf-8")) or "").upper()
            out("       SHA-1 thumbprint: " + ":".join(thumb[i:i + 2] for i in range(0, len(thumb), 2)))
            out("       (must equal the 'Thumbprint' of the ACTIVE certificate in Entra > SAML Certificates)")
            try:
                with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as handle:
                    handle.write(cert_path.read_text(encoding="utf-8"))
                info = ssl._ssl._test_decode_cert(handle.name)
                out(f"       valid until: {info.get('notAfter')}")
                Path(handle.name).unlink(missing_ok=True)
            except Exception:
                pass

        override = getattr(settings, "VONE_SAML_SP_ENTITY_ID", "")
        computed_entity = f"{scheme}://{host}{reverse('sso_metadata')}"
        entity = override or computed_entity
        acs = f"{scheme}://{host}{reverse('sso_acs')}"
        out("")
        if override:
            out(self.style.WARNING(f"  VONE_SAML_SP_ENTITY_ID is SET and overrides the automatic value: {override}"))
            src = "an environment variable in this terminal session" if "VONE_SAML_SP_ENTITY_ID" in os.environ \
                else "a .env file"
            out(f"       (it comes from {src}; remove it for local testing)")
            if "/accounts/sso/" in override:
                out(self.style.ERROR("  FAIL it uses the OLD path /accounts/sso/... ; Entra/IT use /saml/metadata/"))
            if override != computed_entity:
                out(self.style.WARNING(f"  NOTE the automatic value would be: {computed_entity}"))
        out("")
        out("The app will send this to Microsoft:")
        out(f"   Identifier (Entity ID) : {entity}")
        out(f"   Reply URL (ACS)        : {acs}")
        out("")
        out("Register EXACTLY these two values in Entra > Single sign-on > Basic SAML Configuration")
        out("(add them; keep IT's existing entries). Microsoft error AADSTS700016 means the Identifier")
        out("above is not registered; AADSTS50011 means the Reply URL is not registered.")
