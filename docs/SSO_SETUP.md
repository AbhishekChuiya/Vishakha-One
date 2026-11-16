# Company SSO (Microsoft Entra ID, SAML 2.0)

"Continue with company SSO" signs an employee in with their Microsoft work account.
Password login, registration and Forgot password keep working. SSO never grants Content Manager
access; that stays on its own login and permissions.

## How a sign-in works
1. `/accounts/sso/` sends the browser to Microsoft with a sign-in request.
2. Microsoft authenticates the employee and posts a **signed** response to `/accounts/sso/acs/`.
3. The app verifies signature, issuer, audience, recipient, timing and that the response answers
   *this* request, then maps the person by company email (and Employee ID).
4. `/accounts/sso/complete/` finishes the sign-in **only in the browser that started it**.

Existing employee profile (matched by email): signed in. No profile yet: a plain employee account
is created (`VONE_SSO_AUTO_PROVISION=true`), using the Employee ID from Microsoft or, if none is sent,
the one the person types on a one-time step; with the setting off they are told to register. An account that exists without an employee profile (e.g. an admin) is never
taken over.

## Values registered in Entra (set by IT)
| Entra field | Value |
|---|---|
| Identifier (Entity ID) | `https://one.vishakha.live/saml/metadata/` |
| Reply URL (ACS) | `https://one.vishakha.live/sso/saml/acs/` |
| Sign-on URL / Relay State | `https://one.vishakha.live/` |

The application serves exactly these paths (`/saml/metadata/` and `/sso/saml/acs/`); do not rename
them. The browser must reach the portal at the same address, scheme and port that Entra has.
Claims sent by Entra: email address (`user.mail`), name (UPN), given name, surname, display name.
**No Employee ID claim is sent**, so a first-time SSO user is asked once to type their Employee ID.
(If IT later adds an `employeeid` claim, the question is skipped automatically.)

### Local testing
Entra only knows the `one.vishakha.live` addresses, so for local testing add a second Identifier and
Reply URL to the same application (Entra allows several), or test on the server:
`http://localhost:8000/saml/metadata/` and `http://localhost:8000/sso/saml/acs/`. Browse the portal as
exactly `http://localhost:8000`. Do not set `VONE_SAML_SP_ENTITY_ID` locally (it is then built from the address).

### Production checklist for `https://one.vishakha.live/`
- DNS record for `one.vishakha.live` pointing at the server, and a valid certificate for that name.
- Nginx serving that host on port 443, passing `Host` and `X-Forwarded-Proto` to the app.
- `.env.production`: add the host to `DJANGO_ALLOWED_HOSTS` and `https://one.vishakha.live` to
  `DJANGO_CSRF_TRUSTED_ORIGINS`; set `VONE_SAML_SP_ENTITY_ID=https://one.vishakha.live/saml/metadata/`.
- `pip install -r requirements.txt` on the server (adds python3-saml), then `migrate` and restart.

## Signing certificate
Stored in `config/saml/entra_signing_cert.pem` (public certificate, valid to 3 Nov 2029).
Entra shows its thumbprint under SAML Certificates; it must be the **active** certificate:
SHA-1 `FD:FD:99:76:D4:36:44:69:AB:6E:13:8F:BA:A5:48:C6:BF:67:14:52`.
If the certificate is rotated in Entra, replace this file (or point `VONE_SAML_IDP_CERT_FILE` at the new one).

## Environment settings (all optional except the Entity ID)
`VONE_SAML_SP_ENTITY_ID`, `VONE_SSO_ENABLED` (button on/off), `VONE_SSO_AUTO_PROVISION`,
`VONE_SAML_TENANT_ID`, `VONE_SAML_IDP_CERT_FILE`, `VONE_SAML_EMAIL_ATTRS`,
`VONE_SAML_EMPLOYEE_ID_ATTRS`, `VONE_SSO_DEBUG` (development only, needs DJANGO_DEBUG=true).

## Troubleshooting
| Symptom | Likely cause |
|---|---|
| Microsoft: `AADSTS700016` application not found | The Identifier in Entra differs from `VONE_SAML_SP_ENTITY_ID` / the address you browse. |
| Microsoft: `AADSTS50011` reply URL does not match | The Reply URL in Entra is missing or differs (check port, http/https, trailing slash). |
| Back on the login page: "Company sign-in did not work" + log `Signature validation failed` | Entra is signing with a different certificate than `config/saml/entra_signing_cert.pem`. |
| Log `Invalid audience` / `Recipient` / `Destination` | Entity ID or the host/port/scheme seen by Django differs from what Entra has (check Nginx `Host` and `X-Forwarded-Proto`). |
| Message about Employee ID | Microsoft did not send the Employee ID claim. With `VONE_SSO_DEBUG=true` locally, the failure shows the attribute names received. |
| Button opens "SSO is being set up" | `python3-saml` is not installed, or the certificate file is missing. |

To switch SSO off quickly: `VONE_SSO_ENABLED=false`.
