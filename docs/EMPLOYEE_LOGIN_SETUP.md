# Vishakha One Employee Login — Local Setup

This update adds employee authentication to the complete Vishakha One portal.

## Login behaviour

- Employees sign in with their **Employee ID** or their registered full company email address.
- Only an active employee profile with an email ending exactly in `@vishakha.com` can sign in.
- Employee IDs and company email addresses are unique.
- Public self-registration is disabled. HR/IT administrators create employee accounts.
- Anonymous users are redirected to `/accounts/login/` before they can access employee portal pages.
- Content Manager keeps its separate `/content-manager/login/` page and username/password experience. Its login now also checks that the account email belongs to `@vishakha.com`.
- Django Admin, static assets, PWA readiness/manifest/service-worker endpoints and the two login entry points remain reachable without an employee portal session.
- Logout and account switching use POST forms with CSRF protection.

## 1. Prepare the local environment

If this is a fresh checkout, copy `.env.example` to `.env.development` and replace `DJANGO_SECRET_KEY` with a long random development-only value. Keep `.env.development` private; it is ignored by Git. Install dependencies if required:

```powershell
Copy-Item .env.example .env.development
python -m pip install -r requirements.txt
```

If your existing local `.env.development` is already configured, keep using it.

## 2. Apply the database migration

From the project folder, with the project's virtual environment activated:

```powershell
python manage.py migrate
```

The migration creates the `EmployeeProfile` table. It does not alter or delete existing users or content.

## 3. Create the three test accounts

Run:

```powershell
python manage.py setup_vishakha_test_accounts
```

The command creates the three test accounts in the local database and interactively asks you to enter and confirm a password for each one. They are not inserted into the ZIP or created automatically by the database migration. Passwords are not stored in source code, printed to the terminal, or included in this ZIP. Use strong, unique passwords and keep them in your approved password manager.

| Username for Content Manager | Employee ID for employee login | Registered email | Access |
|---|---|---|---|
| `employee_test` | `TESTEMP001` | `employee_test@vishakha.com` | Employee portal only |
| `content_manager_test` | `TESTCM001` | `content_manager_test@vishakha.com` | Employee portal + Administration content creator |
| `content_manager_approver` | `TESTAPP001` | `content_manager_approver@vishakha.com` | Employee portal + Administration Approver |

Employee login accepts the Employee ID or full email. Content Manager login continues to accept the Django username (`employee_test` is not assigned Content Manager permissions; the other two are assigned the roles above).

The command is safe to rerun for these three test accounts, but it resets their passwords and re-applies their test-role group memberships. It does not create superusers or grant Django Admin access.

## 4. Create a real employee account

1. Create a Django user in **Django Admin → Users** with a unique username and a strong password.
2. Set the user's email to the employee's company email address.
3. Open **Employee profiles → Add employee profile**.
4. Select the user and enter the unique Employee ID and the same `@vishakha.com` email address.
5. Keep **Is active** enabled, then save.
6. If the employee needs Content Manager access, assign the appropriate existing Content Manager group through Django Admin → Users → Groups. Do not grant superuser unless separately authorized.

The Employee Profile save operation validates the domain and synchronizes the Django user's email address.

## 5. Local checks

```powershell
python manage.py check
python manage.py test employees portal
```

Then start the development server:

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/accounts/login/`.

## 6. Suggested acceptance tests

- Anonymous visit to `/` redirects to employee login.
- Employee can sign in using `TESTEMP001` and the password set in Step 3.
- Employee can sign in using `employee_test@vishakha.com` and the same password.
- A Gmail or other non-company email cannot be used to authenticate.
- An incorrect password is rejected.
- Inactive users or inactive employee profiles cannot access the portal.
- Employee logout and switch-account forms end the current session.
- `content_manager_test` can open the Content Manager dashboard and create content within the Administration role's permissions.
- `content_manager_approver` can access approval functions allowed by the Administration Approvers group.
- `employee_test` receives a permission-denied response when opening Content Manager.
- Content Manager login remains separate from employee login.

## Important deployment notes

- Develop and test locally first, then commit/push to GitHub, and only then pull the approved commit on the production server.
- The production database must receive the `employees.0001_initial` migration before the new code is deployed. Do not copy the local SQLite database to production; production uses PostgreSQL.
- Existing Content Manager users will need a valid `@vishakha.com` email address to continue using the Content Manager login. To access the employee portal, each user also needs an active Employee Profile.
- The application middleware protects portal pages. Uploaded files served directly by the production web server (for example, Nginx `/media/` URLs) are outside Django page middleware. Before placing confidential employee-only files in media storage, separately configure authenticated media delivery at the web-server layer.
- Corporate SSO is only a placeholder until IT supplies the identity provider, client, redirect URI and signing/certificate configuration.
