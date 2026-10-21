# Vishakha One — A1.2 Local User Acceptance Test (UAT) patch

## What this patch does
- Loads one final additive CSS stylesheet for mobile button spacing, focus visibility,
  popover boundaries and bottom-navigation/AI overlay spacing.
- Adds a favicon reference to the existing PWA icon (addresses `/favicon.ico` browser fallback in modern browsers).
- Includes a read-only preflight script and a manual UAT checklist.
- Does not change database models, permissions, routes or business logic.

## Installation
1. Back up `templates/base.html`. It is based on the A1 hardening patch, so
   **merge the two new `<link>` tags** if you customized this file after A1.
2. Extract into `D:\Projects\VishakhaOne`.
3. Run `python manage.py check`.
4. Run `python manage.py makemigrations --check --dry-run`.
5. Run `python manage.py shell < scripts/uat_preflight.py`.
6. Restart your local Django server and hard-refresh browser (`Ctrl+Shift+R`).

## Manual browser UAT (test at 360px, 390px, 768px, 1366px)
- [ ] No horizontal scrolling or clipped text in home, apps, policies, notifications
- [ ] Bell and profile menus fit inside viewport and close properly
- [ ] Mobile bottom nav doesn't cover form submit buttons
- [ ] Only one AI launcher is visible on mobile; AI panel doesn't cover bottom nav
- [ ] Back-to-top button doesn't overlap mobile nav
- [ ] Keyboard Tab shows a visible focus ring
- [ ] Dark mode text and buttons remain readable
- [ ] Announcement publish / read / dismiss / expire / unpublish works with two users
- [ ] Content Manager create/edit/approve/reject forms work
- [ ] Uploaded images, PDFs and videos open correctly
- [ ] No JavaScript errors in browser DevTools console

## Security / deployment gates (NOT solved by this UI patch)
- Use separate database/media/secret for development, staging, production.
- Ensure `DEBUG=False`, HTTPS, secure cookies, hostnames, backups, access policy.
- Use a strong unique secret (rotate any previously exposed key).
- Test `python manage.py check --deploy` under actual staging settings.
- Resolve all pending migrations, including model Meta options migration 0014.
- Conduct authenticated and unauthenticated access tests and load testing.
- Test on staging before enabling employee access.

## Known limitation
This is an incremental CSS pass, not a screenshot-driven complete UI audit.
Some overlapping controls may be page-specific; provide screenshots with device width
and page URL for targeted corrections. Browser UAT is still required.
