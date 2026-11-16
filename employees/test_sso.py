"""Company SSO (Microsoft Entra SAML) tests.

Responses are signed with THROWAWAY keys generated only for these tests (a stand-in for Microsoft
and an "attacker"). They are not used anywhere else and protect nothing.
"""
import base64
import tempfile
import uuid
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import EmployeeProfile, SsoLoginState

try:
    from onelogin.saml2.utils import OneLogin_Saml2_Utils
    HAVE_SAML = True
except ImportError:  # pragma: no cover - library not installed
    HAVE_SAML = False

User = get_user_model()
TENANT = "test-tenant"
IDP_ENTITY = f"https://sts.windows.net/{TENANT}/"

# --- THROWAWAY TEST KEYS (unit tests only) -------------------------------------------------
IDP_CERT = """-----BEGIN CERTIFICATE-----
MIIDQzCCAiugAwIBAgIUaqaBSeSlkzKTcfKTTg1ZM08as4UwDQYJKoZIhvcNAQEL
BQAwMDEuMCwGA1UEAwwlVmlzaGFraGEgT25lIFVOSVQgVEVTVCBJZFAgKG5vdCBy
ZWFsKTAgFw0yNjExMDUwODM4MjJaGA8yMTI2MTAxMjA4MzgyMlowMDEuMCwGA1UE
AwwlVmlzaGFraGEgT25lIFVOSVQgVEVTVCBJZFAgKG5vdCByZWFsKTCCASIwDQYJ
KoZIhvcNAQEBBQADggEPADCCAQoCggEBAMbDzGwDS4FeUGH/lym8gFSigPs20qov
J6QZJYoSF3UgzTFYUCqiEyjK3SbNfsQQQt5zbjz+FYM0+9x9Do6i8jJVt3WJavrc
VswNj0fW/+6ZMnGqTZaRhDOGPclykg/bl1NEENcuRmbLxO3LU1MiZlsFLEdAKc7p
SltzWSDAhWUU0N5WNiYOqKMjXPhHV2Xtw7GTib+HOxOJT1PGy1debBNkdeUA7MQh
xajEzSplFwaKCm7Jv6x4Z5TNys2WqwI6OHzSWREjdw0whA5t3JPBdAf52RYgPjWS
Wfy5TDdeFHayg/lHRI/V8gBep5zw4kg0M2/zmS7qtfNZDEWS3TBUPb8CAwEAAaNT
MFEwHQYDVR0OBBYEFH9/Si8sSAo2Kv5sI1Eyo5IBLdx8MB8GA1UdIwQYMBaAFH9/
Si8sSAo2Kv5sI1Eyo5IBLdx8MA8GA1UdEwEB/wQFMAMBAf8wDQYJKoZIhvcNAQEL
BQADggEBACsnVUvbS/IJDfwTsLrRUULJuvB+jPRXy1KdddqT7e0Wty+L7+XeW4q+
pK0MhK/+hQTpr4HNmT0rkfQlKOXj65T2LGRpfXj5IsZi02QtlHZ8N/xv1KHaiNb7
hyd8DQ90A6rDCEs74KDEe6ZIsi/AsI3B029LF2ilK0vPxy5RTRLWDgYKQebMESmS
MjYFwpT/oKIZrcBUPfH9gLmIO555rAAv6TCVNYRlQtscfoWc1aaDylOre2TzFbWT
x/pVfJNyJ3HeNRYt2rYAai8ZHN4HY7T2OAa3RhUgMD1Xhq6nFrdoheYoezSLkf+M
4We3mhylXSSuLtz7BQ13c3BT07p4Nn4=
-----END CERTIFICATE-----"""
IDP_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDGw8xsA0uBXlBh
/5cpvIBUooD7NtKqLyekGSWKEhd1IM0xWFAqohMoyt0mzX7EEELec248/hWDNPvc
fQ6OovIyVbd1iWr63FbMDY9H1v/umTJxqk2WkYQzhj3JcpIP25dTRBDXLkZmy8Tt
y1NTImZbBSxHQCnO6Upbc1kgwIVlFNDeVjYmDqijI1z4R1dl7cOxk4m/hzsTiU9T
xstXXmwTZHXlAOzEIcWoxM0qZRcGigpuyb+seGeUzcrNlqsCOjh80lkRI3cNMIQO
bdyTwXQH+dkWID41kln8uUw3XhR2soP5R0SP1fIAXqec8OJINDNv85ku6rXzWQxF
kt0wVD2/AgMBAAECggEAAtAxpLx1M+av+QbATtY83GRZsovTPFD0ormj2IQ2ZoLG
S/50UXnLg4k/hW/CJ7OgINlyOGaB4nDwrUp4Ba/OpDka/8bt6nmB/kQCUjMescUp
akyH0rGFBotN6WSDg+jDE2nyt0D4dvDTH906F9QXOZpOGHOHWztpb8l4kyg8PgRP
IxJp26qCWH7C1gmtOtrbf9zrIR3O/8EpEB0xMlXK8IRDoXLRO4IvcHLQEbQ2a4ao
DfrdJJdq23j9zjKSv/l1ka7sMfoFE9wANRxXpfFQOtj9b5BoRg5N8mqUlf/YTL/B
L4kgWaaW64xPX4l+2Lg3g8SF8nQ43ih7masxOw3L3QKBgQD0yyj2yrM652qrsH2e
LzRyOkfTni8b3obx0wF3xclaEGOMSfLHdjW39+KrN6e74b1ujKvLOrGHC6R7ovZd
cSRSCU841ni0KHWp6AyUkSdwvy2m9Q/S8kb75OU7lJvlMe9MTDegx+OidsUdScq7
GEFreyqpmXT9JRoodIuo//OrawKBgQDP3TU+yG605fSDv5laOqBU6u40i9dEssaz
6Rj20WzgZloG86kPhk7lKOEWJsw5lWEnWvuWCF8/LaoRFKs00L4QCQW8w8vzw21Y
Uah2vF/VQEG5a+lcpVjwrgs1/ztvPu1CoqAmFPACDGcYPDQPRJRXr21gHb/FuNxK
2shOrZ2//QKBgDUOAybZ79aIaXokmlU6beeD8iVPV2524FBxJxRKbcVzX9/79v58
BFCHDT2Gpnf2CRR4sJMveWKHh3K0cyj1aKXPFrh+41JIopfcjz1z6FRrWv2gh3l0
wSW/Cl/Laa5XEEI9EqFqMU/45effIm1CaIte+nQfqldjPzQdbleGgc1ZAoGAZOEY
fDXN9KE9f8s246FcOpohrQLJIKAa6ymPYgnVazqBKqqKO+yU0YZ7ZsLBjpi+o9j2
DKRXhVPmG5AKXwGHnESksi3cB5uqr5hByA43/EjJHPIQOVRNy9DLxBLwh1bk0tgW
HSVALd5TEmH1aguAauXKkUEe1xiWYQW4/OYpjwkCgYEA4mEEpceM1slPZZI8U4ub
cXSltfIJMANQb+pFSZ1E/MJE35x25rCV1sMREL4RozazXIt+CQJ7nskr1FaKsVv7
8iIJHI0Xdhn7eAvmvAjh/kXZ4JywUySr58XBFICoYtuJGFCbVJ/ZOCXQ5mCa3/T8
jMIsE1scduIgI+DJTGCztxA=
-----END PRIVATE KEY-----"""
EVIL_CERT = """-----BEGIN CERTIFICATE-----
MIIDITCCAgmgAwIBAgIUR9KI8JvqWR4uzmD2DdquBMSOoW0wDQYJKoZIhvcNAQEL
BQAwHzEdMBsGA1UEAwwUQXR0YWNrZXIgKHVuaXQgdGVzdCkwIBcNMjYxMTA1MDgz
ODIzWhgPMjEyNjEwMTIwODM4MjNaMB8xHTAbBgNVBAMMFEF0dGFja2VyICh1bml0
IHRlc3QpMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqIZ92AbCG6QJ
/H/UhksBtPOl0710uzCFgkY5q7hlhkAihLwxHUQ3SloTlpI17i7NeQKadyDZ4+E6
mw/wEvUHVnGBgMQhjYcNLL3/2WMu/d827he+vr/qlCGm9dOPc00/AlGr5YjbcSJW
pt8QyM3JW5yhFk1TIbQnm5tMi1aAo+gfN8UHBxiTHrwo/NeOYSaFVvUuVGvUl53X
wGA7SPj2naFr8lQxDc/5snko/8YUlDSyaS7dq3CDucmVqilqsHp+q7Q/+nOi29mY
wxc/ETkaGOdUez14VlTw2nJ5uffc6ttn7S4gPdTF2w1fn7Z8Cuo+0br2Af04qyzK
s617C7gjzQIDAQABo1MwUTAdBgNVHQ4EFgQUctctAsriI1VcIwjZrT+2cjG0jaAw
HwYDVR0jBBgwFoAUctctAsriI1VcIwjZrT+2cjG0jaAwDwYDVR0TAQH/BAUwAwEB
/zANBgkqhkiG9w0BAQsFAAOCAQEAmxLSVUO8a8CuF9+0/brOsg70nPbWEbONUBxQ
zZ5aXq87wgbHJLofpEFz80TtiCrDje97hDHD3B7xHXFdGjD6K1m5LvqsZgkublA7
7Uj7t2m1JbMVaQoLMqCZvQyznZxyOYqeIlH90me/aw0EZRrmbleIz2g7fDx7C52u
Ld3J4s5xwnEoT2D+ZNDrc1ROUc5Mnr8sz32/aZOhDGWOyhHmo4QCOoXbQ9gZ+uaV
gAwMI8o6CcL3epcd8QSPbajAN9WGAJa35utTpa/ts9Z7jmXZ20f7UceGbFHEpS8u
cWTAy5Sns6RGyCZVnVqYlkJtzWzZC7soFVHrP4WtRyMbbSMJTg==
-----END CERTIFICATE-----"""
EVIL_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCohn3YBsIbpAn8
f9SGSwG086XTvXS7MIWCRjmruGWGQCKEvDEdRDdKWhOWkjXuLs15App3INnj4Tqb
D/AS9QdWcYGAxCGNhw0svf/ZYy793zbuF76+v+qUIab1049zTT8CUavliNtxIlam
3xDIzclbnKEWTVMhtCebm0yLVoCj6B83xQcHGJMevCj8145hJoVW9S5Ua9SXndfA
YDtI+PadoWvyVDENz/myeSj/xhSUNLJpLt2rcIO5yZWqKWqwen6rtD/6c6Lb2ZjD
Fz8RORoY51R7PXhWVPDacnm599zq22ftLiA91MXbDV+ftnwK6j7RuvYB/TirLMqz
rXsLuCPNAgMBAAECggEAA9LhYhhtKRFkxJzl5pInHML2fUJsNp8YOGd9gX7ylsQ3
xEk82AwnMQGwNhdlL91R/i/n71IIf5opqUEIUnXKz9RNeu14UWzCCMTa3ETa2RnK
dkaFpnBWUzwcPLGrLJORHW1a+B9N01hTHQAsslGxAuof4ZCplTcwOuCgMP0qeA2P
zYFauc42eWoKC44feiiOPoCFzyblrRe8gPvBarPTnilQyyU9ojSwYDIbBQmqd2jK
JmbiBF59sDclyshVbXwfzCfU11SkvgDO5J0OgQUx52wnhT0IH2aUc2xOGEBEn72s
/4M4YqOS9Axn5viwZgwo4Sjqa8Qh+zpXIOdHmU1nBQKBgQDd6vulW3HCRxYaH/S+
UdHwg+5435wNVArLcZ5cx0Qx0VCocJQtjIBwhkk0f99JDQGnOZ75+d+kFWAdv1Q0
YD1blv3vfogVo7YWmE8bP42fs9hP0+goORToknCfpxQeU9nZf602fvKbrx3Bp1GP
NqXUfxeNP2s5V3l2MvTayvSiqwKBgQDCaE4Te6FCL+CvYnPDycXK30okNdojMs3S
2tmO4/eC3Qa+Q0AjRxDFGotVkox/P7WdqO2kz/NWp4oBT95M5b/t1fApCCViaaAr
U5eSKNV/dAbDrqQZdysN9kYcFkU1NKbfp3vEES6sY3s/C78Sk8ilUXfs3Ex9HOYO
OFghcagTZwKBgHRN0eMAwOcL8HZypwcTxI5j5phswNFvaVTkUBXZzVC6naYZkl8o
0qumhTlBhxk2+tXUahAit+W72irc+lmU0rNst9tLmjCVIzpGSrdCIIxBai20Jmjm
OaIGFYZmvzGBypulwXbdI3MaXOMAOMtw3Yo3rXU2dpCP2rVq0U7VrU6PAoGBAKkY
aLDxm/YiBuEGVYM7AdvQFIEihjaPfg+lZA6xoxwkfDUJ8cO9kIyg5gjsi2AzXhlg
UjRE3HfHCnbRrZ5dSG/q4hYOi9Xp4fNNpkzvT6SomymhwgKUcNKYH6tWg6Qfw/ZN
i42jFGHFtfHEmdHi0WdaUWGozK8Wb9R2ldGhNnyJAoGASE4jXr/TygfJXzI84IRG
f+vc29zSQ/0DoH3FlY8/YW4R/nJE7VzIpqIUAR7i/e6kUvEXHrn978htLv0fyWf1
+oJ3ossXZak87Ip7yTgFzYAn0mFuLPBybG71kA5U6WiargSp81ylIeY2BnPzhB6S
L9drCqTWeqZNWCQbFY6CILk=
-----END PRIVATE KEY-----"""
# --------------------------------------------------------------------------------------------

EMAIL = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
GIVEN = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"
SURNAME = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname"


def _t(offset_seconds=0):
    return (datetime.now(dt_timezone.utc) + timedelta(seconds=offset_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_response(*, request_id, acs, audience, attributes, name_id="user@vishakha.com",
                   key=IDP_KEY, cert=IDP_CERT, sign=True, not_on_or_after=300, in_response_to=None):
    attrs = "".join(
        f'<saml:Attribute Name="{name}"><saml:AttributeValue>{value}</saml:AttributeValue></saml:Attribute>'
        for name, value in attributes.items())
    irt = in_response_to or request_id
    assertion = (
        f'<saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_a{uuid.uuid4().hex}" '
        f'Version="2.0" IssueInstant="{_t()}"><saml:Issuer>{IDP_ENTITY}</saml:Issuer>'
        f'<saml:Subject><saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified">{name_id}</saml:NameID>'
        f'<saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">'
        f'<saml:SubjectConfirmationData InResponseTo="{irt}" NotOnOrAfter="{_t(not_on_or_after)}" Recipient="{acs}"/>'
        f'</saml:SubjectConfirmation></saml:Subject>'
        f'<saml:Conditions NotBefore="{_t(-60)}" NotOnOrAfter="{_t(not_on_or_after)}">'
        f'<saml:AudienceRestriction><saml:Audience>{audience}</saml:Audience></saml:AudienceRestriction></saml:Conditions>'
        f'<saml:AuthnStatement AuthnInstant="{_t()}" SessionIndex="_s1"><saml:AuthnContext>'
        f'<saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:Password</saml:AuthnContextClassRef>'
        f'</saml:AuthnContext></saml:AuthnStatement>'
        f'<saml:AttributeStatement>{attrs}</saml:AttributeStatement></saml:Assertion>')
    if sign:
        signed = OneLogin_Saml2_Utils.add_sign(assertion, key, cert)
        assertion = signed.decode() if isinstance(signed, bytes) else signed
        assertion = assertion.replace('<?xml version="1.0"?>', "").strip()
    response = (
        f'<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" '
        f'xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_r{uuid.uuid4().hex}" Version="2.0" '
        f'IssueInstant="{_t()}" Destination="{acs}" InResponseTo="{irt}">'
        f'<saml:Issuer>{IDP_ENTITY}</saml:Issuer><samlp:Status>'
        f'<samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/></samlp:Status>{assertion}</samlp:Response>')
    return base64.b64encode(response.encode()).decode()


import unittest


@unittest.skipUnless(HAVE_SAML, "python3-saml is not installed")
class SsoBase(TestCase):
    ACS = "http://testserver/sso/saml/acs/"
    AUDIENCE = "http://testserver/saml/metadata/"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._cert_file = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False)
        cls._cert_file.write(IDP_CERT)
        cls._cert_file.close()
        cls._override = override_settings(
            VONE_SAML_TENANT_ID=TENANT, VONE_SAML_IDP_CERT_FILE=cls._cert_file.name,
            VONE_SAML_SP_ENTITY_ID="", VONE_SSO_ENABLED=True)
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        Path(cls._cert_file.name).unlink(missing_ok=True)
        super().tearDownClass()

    def setUp(self):
        cache.clear()
        self.client = Client()

    def start(self, client=None, query=""):
        client = client or self.client
        response = client.get(reverse("accounts:sso") + query)
        self.assertEqual(response.status_code, 302, "SSO start should redirect to Microsoft")
        url = urlparse(response["Location"])
        params = parse_qs(url.query)
        return response, params["RelayState"][0]

    def post_response(self, state, attributes, client=None, **kwargs):
        client = client or self.client
        row = SsoLoginState.objects.get(state=state)
        payload = build_response(request_id=row.request_id, acs=self.ACS, audience=self.AUDIENCE,
                                 attributes=attributes, **kwargs)
        return client.post(reverse("sso_acs"), {"SAMLResponse": payload, "RelayState": state}), payload

    def full_login(self, attributes, **kwargs):
        _, state = self.start()
        response, payload = self.post_response(state, attributes, **kwargs)
        return state, response, payload

    def signed_in(self, client=None):
        return "_auth_user_id" in (client or self.client).session

    @staticmethod
    def claims(email, employee_id=None, first="Asha", last="Rao"):
        data = {EMAIL: email, GIVEN: first, SURNAME: last}
        if employee_id:
            data["employeeid"] = employee_id
        return data


class SsoStartTests(SsoBase):
    def test_start_redirects_to_microsoft_and_records_state(self):
        response, state = self.start(query="?next=/policies/")
        self.assertTrue(response["Location"].startswith(f"https://login.microsoftonline.com/{TENANT}/saml2?"))
        params = parse_qs(urlparse(response["Location"]).query)
        self.assertIn("SAMLRequest", params)
        row = SsoLoginState.objects.get(state=state)
        self.assertEqual(row.next_url, "/policies/")
        self.assertEqual(self.client.session["vone_sso_nonce"], row.nonce)
        self.assertLessEqual(len(state), 80)  # SAML RelayState limit

    def test_unsafe_next_url_is_ignored(self):
        _, state = self.start(query="?next=https://evil.example/steal")
        self.assertEqual(SsoLoginState.objects.get(state=state).next_url, "/")

    def test_not_configured_shows_info_page(self):
        with override_settings(VONE_SAML_IDP_CERT_FILE="/nonexistent/cert.pem"):
            response = self.client.get(reverse("accounts:sso"))
        self.assertContains(response, "SSO is being set up")
        self.assertEqual(SsoLoginState.objects.count(), 0)

    def test_metadata_describes_this_application(self):
        response = self.client.get(reverse("sso_metadata"))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn(f'entityID="{self.AUDIENCE}"', body)
        self.assertIn(f'Location="{self.ACS}"', body)
        self.assertIn('WantAssertionsSigned="true"', body)

    def test_endpoints_match_the_addresses_registered_in_entra(self):
        self.assertEqual(reverse("sso_acs"), "/sso/saml/acs/")
        self.assertEqual(reverse("sso_metadata"), "/saml/metadata/")
        self.assertEqual(self.client.get("/saml/metadata/").status_code, 200)  # public, no login needed
        self.assertEqual(self.client.post("/sso/saml/acs/", {}).status_code, 302)  # reaches the view, not the login wall

    def test_login_page_button_points_at_sso(self):
        self.assertContains(self.client.get(reverse("accounts:login")), reverse("accounts:sso"))


class SsoSignInTests(SsoBase):
    def make_employee(self, username="asha", employee_id="E1001", email="asha.rao@vishakha.com", **profile):
        user = User.objects.create_user(username, password="Existing-Password-7391-x")
        EmployeeProfile.objects.create(user=user, employee_id=employee_id, company_email=email, **profile)
        return user

    def test_existing_employee_signs_in_by_email_without_changes(self):
        user = self.make_employee()
        group = Group.objects.create(name="Administration")
        user.groups.add(group)
        state, response, _ = self.full_login(self.claims("Asha.Rao@vishakha.com", "e1001"))
        self.assertRedirects(response, f"{reverse('accounts:sso_complete')}?state={state}", fetch_redirect_response=False)
        self.assertFalse(self.signed_in())  # not signed in until the same-browser step
        done = self.client.get(response["Location"])
        self.assertRedirects(done, "/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["Administration"])  # untouched
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(self.client.get(reverse("portal:profile")).status_code, 200)

    def test_new_company_user_is_provisioned_as_plain_employee(self):
        state, response, _ = self.full_login(self.claims("new.person@vishakha.com", "90003001"))
        self.client.get(response["Location"])
        user = User.objects.get(email="new.person@vishakha.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertEqual(user.employee_profile.employee_id, "90003001")
        self.assertEqual((user.first_name, user.last_name), ("Asha", "Rao"))
        self.assertFalse(user.has_usable_password())  # can set one later via Forgot password
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertEqual(user.get_all_permissions(), set())
        self.assertEqual(user.groups.count(), 0)

    def test_sso_user_has_no_content_manager_access(self):
        _, response, _ = self.full_login(self.claims("cm.check@vishakha.com", "90003002"))
        self.client.get(response["Location"])
        self.assertEqual(self.client.get(reverse("content_manager:dashboard")).status_code, 403)
        other = Client()
        denied = other.post(reverse("content_manager:login"), {"username": "90003002", "password": "anything"})
        self.assertEqual(denied.status_code, 200)
        self.assertNotIn("_auth_user_id", other.session)

    def test_no_employee_id_claim_asks_for_it_once_then_creates_a_plain_account(self):
        state, response, _ = self.full_login(self.claims("noid@vishakha.com"))
        self.assertIn("accounts/sso/complete", response["Location"])
        form_page = self.client.get(response["Location"])
        self.assertContains(form_page, "One last step")
        self.assertContains(form_page, "noid@vishakha.com")  # verified by Microsoft, shown not typed
        self.assertFalse(User.objects.exists())
        self.assertFalse(self.signed_in())
        done = self.client.post(reverse("accounts:sso_complete"), {"state": state, "employee_id": "90004001"})
        self.assertRedirects(done, "/", fetch_redirect_response=False)
        user = User.objects.get(email="noid@vishakha.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertEqual(user.employee_profile.employee_id, "90004001")
        self.assertEqual((user.first_name, user.last_name), ("Asha", "Rao"))
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertEqual(user.get_all_permissions(), set())

    def test_employee_id_step_rejects_bad_or_taken_ids_without_creating_anything(self):
        other = User.objects.create_user("e5000", password="Existing-Password-7391-x")
        EmployeeProfile.objects.create(user=other, employee_id="E5000", company_email="other@vishakha.com")
        state, response, _ = self.full_login(self.claims("noid2@vishakha.com"))
        for bad in ("x", "bad id!", "E5000", "e5000"):
            page = self.client.post(reverse("accounts:sso_complete"), {"state": state, "employee_id": bad})
            self.assertEqual(page.status_code, 200, bad)
            self.assertContains(page, "auth-field-error")
            self.assertFalse(self.signed_in())
        self.assertEqual(User.objects.count(), 1)
        ok = self.client.post(reverse("accounts:sso_complete"), {"state": state, "employee_id": "90004002"})
        self.assertRedirects(ok, "/", fetch_redirect_response=False)

    def test_employee_id_step_cannot_be_used_from_another_browser(self):
        state, response, _ = self.full_login(self.claims("noid3@vishakha.com"))
        stranger = Client()
        for call in (lambda: stranger.get(response["Location"]),
                     lambda: stranger.post(reverse("accounts:sso_complete"), {"state": state, "employee_id": "90004003"})):
            result = call()
            self.assertRedirects(result, reverse("accounts:login"), fetch_redirect_response=False)
        self.assertFalse(User.objects.exists())

    def test_auto_provision_can_be_switched_off(self):
        with override_settings(VONE_SSO_AUTO_PROVISION=False):
            _, response, _ = self.full_login(self.claims("new2@vishakha.com", "90003003"))
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        self.assertFalse(User.objects.exists())

    def test_non_company_or_missing_email_is_refused(self):
        for claims in (self.claims("someone@gmail.com", "90003004"), {"employeeid": "90003005"}):
            _, response, _ = self.full_login(claims, name_id="nobody@example.com")
            self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        self.assertFalse(User.objects.exists())

    def test_inactive_profile_and_mismatching_employee_id_are_refused(self):
        self.make_employee(is_active=False)
        _, response, _ = self.full_login(self.claims("asha.rao@vishakha.com", "E1001"))
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        EmployeeProfile.objects.update(is_active=True)
        _, response, _ = self.full_login(self.claims("asha.rao@vishakha.com", "E9999"))
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)

    def test_account_without_profile_but_same_email_is_not_taken_over(self):
        User.objects.create_user("old_admin", email="boss@vishakha.com", password="Existing-Password-7391-x")
        _, response, _ = self.full_login(self.claims("boss@vishakha.com", "90003006"))
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        self.assertFalse(EmployeeProfile.objects.exists())

    def test_next_url_is_honoured_after_sign_in(self):
        self.make_employee()
        _, state = self.start(query="?next=/search/")
        response, _ = self.post_response(state, self.claims("asha.rao@vishakha.com", "E1001"))
        done = self.client.get(response["Location"])
        self.assertRedirects(done, "/search/", fetch_redirect_response=False)


class SsoAttackTests(SsoBase):
    LOGGER = "portal.auth_views"

    def setUp(self):
        super().setUp()
        user = User.objects.create_user("asha", password="Existing-Password-7391-x")
        EmployeeProfile.objects.create(user=user, employee_id="E1001", company_email="asha.rao@vishakha.com")
        self.good = self.claims("asha.rao@vishakha.com", "E1001")

    def assert_rejected(self, response, client=None):
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        self.assertFalse(self.signed_in(client))

    def rejected_because(self, reason, post):
        """Run `post()` and require that it is refused AND that the log names the expected reason."""
        with self.assertLogs(self.LOGGER, level="WARNING") as logs:
            response = post()
        self.assert_rejected(response)
        self.assertTrue(any(reason.lower() in line.lower() for line in logs.output),
                        f"expected '{reason}' in {logs.output}")

    def test_control_valid_response_is_accepted(self):
        """Same builder, no tampering: proves the rejections below are for the stated reason."""
        _, response, _ = self.full_login(self.good)
        self.assertIn("accounts/sso/complete", response["Location"])

    def test_response_signed_by_the_wrong_key_is_rejected(self):
        _, state = self.start()
        self.rejected_because("signature validation failed",
                              lambda: self.post_response(state, self.good, key=EVIL_KEY, cert=EVIL_CERT)[0])

    def test_unsigned_assertion_is_rejected(self):
        _, state = self.start()
        self.rejected_because("sign", lambda: self.post_response(state, self.good, sign=False)[0])

    def test_wrong_audience_is_rejected(self):
        _, state = self.start()
        row = SsoLoginState.objects.get(state=state)
        payload = build_response(request_id=row.request_id, acs=self.ACS, audience="https://other-app.example/",
                                 attributes=self.good)
        self.rejected_because("audience", lambda: self.client.post(
            reverse("sso_acs"), {"SAMLResponse": payload, "RelayState": state}))

    def test_expired_assertion_is_rejected(self):
        _, state = self.start()
        self.rejected_because("expired", lambda: self.post_response(state, self.good, not_on_or_after=-600)[0])

    def test_response_to_a_different_request_is_rejected(self):
        _, state = self.start()
        self.rejected_because("inresponseto", lambda: self.post_response(
            state, self.good, in_response_to="ONELOGIN_someone_elses_request")[0])

    def test_tampered_attributes_break_the_signature(self):
        _, state = self.start()
        row = SsoLoginState.objects.get(state=state)
        payload = build_response(request_id=row.request_id, acs=self.ACS, audience=self.AUDIENCE, attributes=self.good)
        xml = base64.b64decode(payload).decode().replace("asha.rao@vishakha.com", "ceo@vishakha.com")
        forged = base64.b64encode(xml.encode()).decode()
        self.rejected_because("signature", lambda: self.client.post(
            reverse("sso_acs"), {"SAMLResponse": forged, "RelayState": state}))
        self.assertFalse(User.objects.filter(email="ceo@vishakha.com").exists())

    def test_response_cannot_be_replayed(self):
        state, response, payload = self.full_login(self.good)
        self.client.get(response["Location"])
        self.assertTrue(self.signed_in())
        self.client.logout()
        self.rejected_because("already used", lambda: self.client.post(
            reverse("sso_acs"), {"SAMLResponse": payload, "RelayState": state}))
        self.assert_rejected(self.client.get(f"{reverse('accounts:sso_complete')}?state={state}"))

    def test_unknown_state_is_rejected(self):
        payload = build_response(request_id="x", acs=self.ACS, audience=self.AUDIENCE, attributes=self.good)
        self.rejected_because("unknown, expired or already used", lambda: self.client.post(
            reverse("sso_acs"), {"SAMLResponse": payload, "RelayState": "not-a-real-state"}))

    def test_unsolicited_response_from_my_apps_tile_starts_a_proper_sign_in_instead(self):
        """IdP-initiated responses are never trusted; the browser is sent to start SSO ourselves."""
        payload = build_response(request_id="x", acs=self.ACS, audience=self.AUDIENCE, attributes=self.good)
        for relay in ("", "https://one.vishakha.live/"):
            response = self.client.post(reverse("sso_acs"), {"SAMLResponse": payload, "RelayState": relay})
            self.assertRedirects(response, reverse("accounts:sso"), fetch_redirect_response=False)
            self.assertFalse(self.signed_in())
        self.assertFalse(User.objects.filter(email__icontains="ceo").exists())

    def test_expired_state_is_rejected(self):
        _, state = self.start()
        SsoLoginState.objects.filter(state=state).update(created_at=timezone.now() - timedelta(minutes=30))
        self.rejected_because("unknown, expired or already used", lambda: self.post_response(state, self.good)[0])

    def test_sign_in_cannot_be_forced_onto_another_browser(self):
        """Login CSRF: an attacker starts SSO, then tricks a victim's browser into finishing it."""
        attacker = Client()
        _, state = self.start(client=attacker)
        response, _ = self.post_response(state, self.good, client=attacker)
        complete_url = response["Location"]
        # Victim with no SSO started: no nonce at all.
        victim = Client()
        self.assert_rejected(victim.get(complete_url), victim)
        # Victim who started their own SSO: their nonce does not match the attacker's state.
        victim = Client()
        self.start(client=victim)
        self.assert_rejected(victim.get(complete_url), victim)
        # The attacker's own browser can still finish its own flow (nothing was consumed).
        attacker.get(complete_url)
        self.assertTrue(self.signed_in(attacker))

    def test_get_on_acs_is_not_allowed_and_post_without_saml_is_rejected(self):
        self.assertEqual(self.client.get(reverse("sso_acs")).status_code, 405)
        _, state = self.start()
        self.assert_rejected(self.client.post(reverse("sso_acs"), {"RelayState": state}))


class DiagnoseSsoCommandTests(SsoBase):
    def run_cmd(self, *args):
        import io
        from django.core.management import call_command
        out = io.StringIO()
        call_command("diagnose_sso", *args, stdout=out)
        return out.getvalue()

    def test_reports_the_values_to_register_for_the_chosen_host(self):
        text = self.run_cmd("--host", "localhost:8000")
        self.assertIn("http://localhost:8000/saml/metadata/", text)
        self.assertIn("http://localhost:8000/sso/saml/acs/", text)
        text = self.run_cmd("--host", "one.vishakha.live")
        self.assertIn("https://one.vishakha.live/saml/metadata/", text)
        self.assertIn("https://one.vishakha.live/sso/saml/acs/", text)

    def test_flags_an_override_that_still_uses_the_old_path(self):
        with override_settings(VONE_SAML_SP_ENTITY_ID="http://localhost:8000/accounts/sso/metadata/"):
            text = self.run_cmd("--host", "localhost:8000")
        self.assertIn("overrides the automatic value", text)
        self.assertIn("OLD path", text)
        self.assertIn("would be: http://localhost:8000/saml/metadata/", text)
