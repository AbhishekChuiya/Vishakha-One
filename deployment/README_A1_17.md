# Vishakha One A1.17 – Staging deployment preparation

This is an **opt-in deployment template**, not an automatic production conversion.
It adds `config/settings_deploy.py` and examples under `deployment/`.
It **does not overwrite** `config/settings.py`, your development `.env`, SQLite DB, media, or templates.

## Local Windows checks (existing application)

```powershell
python manage.py check
python manage.py vone_preflight
python manage.py vone_audit
```

No migration or change to local runserver is needed. Do not activate `settings_deploy` on Windows until you have a staging PostgreSQL instance.

## Staging Linux – IT checklist

1. Allocate staging DNS name, TLS termination, dedicated Linux service account, storage and backups. Reserve port **8101** only as an example; IT must check port availability. Multiple Django apps can share one host using different Gunicorn ports and Nginx `server_name` routes.
2. Install Python/venv, PostgreSQL, Nginx. Copy application to `/srv/vishakha-one/app` without any local `.env.*`, SQLite databases, or private credentials. Install the project's existing `requirements.txt`, then `deployment/requirements-deploy.txt`.
3. Provision **separate** PostgreSQL database/user for staging; production needs another DB/user and service/hostname/port. Grant only needed permissions. Confirm data migration plan with IT; do not assume SQLite content is automatically copied.
4. Put environment values in `/etc/vishakha-one/staging.env` readable only by the service owner/root; use `deployment/staging.env.example` as a reference. Set `VONE_ENV=staging` and `DJANGO_SETTINGS_MODULE=config.settings_deploy` in the service unit.
5. Create static/media paths, ensure the service user can write uploads and collectstatic can populate staticfiles. Uploaded media requires an explicit **access-control policy**: the sample Nginx config blocks `/media/` to avoid unintended disclosure.
6. Run (with staging environment variables loaded):

```bash
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py vone_preflight
python manage.py vone_audit
```

7. Adjust the `.service.example` paths, username, port and worker count. Install the unit in systemd and the Nginx server block. Validate with `nginx -t`, start services, test actual staging hostname. The supplied Nginx config is **HTTP-only**, for initial internal staging. It is **not a finished production TLS configuration**.
8. Once IT configures and verifies HTTPS, change trusted origins to `https://...`, set `VONE_HTTPS_READY=true`, and set `VONE_TRUST_PROXY_HTTPS=true` **only if direct Gunicorn access is blocked** and the trusted proxy overwrites forwarded headers. HSTS should remain zero until IT approves its rollout.
9. Test uploads, media authorization, content-manager login, CSRF, sessions across browsers, announcements, and canteen editing. Review any third-party API endpoints and firewall rules before enabling Vishakha AI.
10. Arrange encrypted PostgreSQL and media backups, test restore in isolated staging, configure log rotation, monitoring, and patching. Confirm production access restrictions and a rollback plan.

## Shared-server rules

- Separate venv, Gunicorn service, Unix user where feasible, PostgreSQL database/user, logs, static/media directories, and environment secrets.
- Bind Gunicorn to `127.0.0.1:<unique-port>`; Nginx routes by hostname. Never expose Gunicorn directly to the network.
- Check CPU/RAM/storage with IT; start with three workers as a **test configuration**, not a validated sizing recommendation.
- Staging and production should have separate hostnames and secrets, even if IT hosts them on the same physical server.
- The Llama/agentic AI inference service should have separate capacity and access-control planning. Django web server capacity alone does not cover AI inference.

## Safety notes

- Never commit real `.env`, tokens, database dumps, certificates, or employee data.
- `config/settings_deploy.py` fails fast if staging/production configuration is missing; this is intentional.
- `VONE_HTTPS_READY=false` permits initial HTTP staging **only** on an approved restricted internal network. Production should use HTTPS.
- Nginx media is blocked by default. If your existing site expects public media, IT must explicitly review and configure safe media serving before acceptance.
- If the server uses SELinux/AppArmor, firewall rules, or an existing reverse proxy, IT must adapt the examples.
