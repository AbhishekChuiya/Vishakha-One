"""Thin wrapper around python3-saml for Microsoft Entra ID (SAML 2.0).

The library is imported lazily so the portal keeps working (password login, registration)
even if it is not installed; company SSO then simply reports "being set up".
"""
import base64
import logging
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)


@dataclass
class SamlResult:
    ok: bool
    attributes: dict = field(default_factory=dict)
    name_id: str = ""
    reason: str = ""


def _read_cert():
    path = Path(getattr(settings, "VONE_SAML_IDP_CERT_FILE", "") or "")
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    return "".join(line for line in text.splitlines() if "CERTIFICATE" not in line).strip()


def is_configured():
    try:
        import onelogin.saml2.auth  # noqa: F401
    except ImportError:
        return False
    return bool(getattr(settings, "VONE_SAML_TENANT_ID", "")) and bool(_read_cert())


def sp_entity_id(request):
    return getattr(settings, "VONE_SAML_SP_ENTITY_ID", "") or request.build_absolute_uri(
        reverse("sso_metadata"))


def acs_url(request):
    return request.build_absolute_uri(reverse("sso_acs"))


def saml_settings(request):
    tenant = settings.VONE_SAML_TENANT_ID
    return {
        "strict": True,
        "debug": False,
        "sp": {
            "entityId": sp_entity_id(request),
            "assertionConsumerService": {
                "url": acs_url(request),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
        },
        "idp": {
            "entityId": f"https://sts.windows.net/{tenant}/",
            "singleSignOnService": {
                "url": f"https://login.microsoftonline.com/{tenant}/saml2",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": _read_cert(),
        },
        "security": {
            "authnRequestsSigned": False,
            "logoutRequestSigned": False,
            "logoutResponseSigned": False,
            "wantMessagesSigned": False,
            "wantAssertionsSigned": True,
            "wantAssertionsEncrypted": False,
            "wantNameIdEncrypted": False,
            "requestedAuthnContext": False,
            "rejectDeprecatedAlgorithm": True,
            "allowRepeatAttributeName": True,
            "allowSingleLabelDomains": True,  # internal host names such as http://portal:8000
        },
    }


def _request_data(request):
    return {
        "https": "on" if request.is_secure() else "off",
        "http_host": request.get_host(),  # includes the port when it is not the default
        "script_name": request.path,
        "get_data": request.GET.dict(),
        "post_data": request.POST.dict(),
    }


def start_login(request, relay_state):
    """Return (redirect_url_to_microsoft, authn_request_id)."""
    from onelogin.saml2.authn_request import OneLogin_Saml2_Authn_Request
    from onelogin.saml2.settings import OneLogin_Saml2_Settings

    saml = OneLogin_Saml2_Settings(saml_settings(request))
    authn = OneLogin_Saml2_Authn_Request(saml, set_nameid_policy=False)
    sso_url = saml.get_idp_sso_url()
    params = urlencode({"SAMLRequest": authn.get_request(), "RelayState": relay_state})
    return f"{sso_url}{'&' if '?' in sso_url else '?'}{params}", authn.get_id()


def validate_response(request, request_id):
    """Verify signature, issuer, audience, recipient, timing and InResponseTo."""
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.errors import OneLogin_Saml2_Error

    auth = OneLogin_Saml2_Auth(_request_data(request), old_settings=saml_settings(request))
    try:
        auth.process_response(request_id=request_id)
    except OneLogin_Saml2_Error as exc:
        return SamlResult(False, reason=f"saml error: {exc}")
    errors = auth.get_errors()
    if errors or not auth.is_authenticated():
        return SamlResult(False, reason=f"{', '.join(errors) or 'not authenticated'}: {auth.get_last_error_reason()}")
    return SamlResult(True, attributes=auth.get_attributes(), name_id=auth.get_nameid() or "")


def sp_metadata_xml(request):
    from onelogin.saml2.settings import OneLogin_Saml2_Settings

    saml = OneLogin_Saml2_Settings(saml_settings(request), sp_validation_only=True)
    metadata = saml.get_sp_metadata()
    errors = saml.validate_metadata(metadata)
    if errors:
        raise ValueError("Invalid SP metadata: " + ", ".join(errors))
    return metadata
