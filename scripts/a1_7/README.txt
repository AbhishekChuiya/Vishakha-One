A1.7 — notification + snack corrections

Extract into D:\Projects\VishakhaOne, then run in PowerShell:
  python scripts/a1_7/apply_fixes.py
  python manage.py check
  python manage.py runserver 0.0.0.0:8000

Fixes:
- Homepage notice dismiss submits a POST to existing read endpoint, saves read status per employee, and redirects home.
- Notification page no longer hides cards from sessionStorage while still counting them (All 2 / visible 1).
- Bell company announcement link styled visible and elevated on mobile/tablet; link points to /notifications/.
- When custom snacks exist: ✦ CHEF'S SPECIAL and snack name. Otherwise ☕ Regular Snacks.
- No database migration. Backups saved as .bak_a1_7 next to changed files.

Test on PC/tablet/mobile: mark as read; dismiss homepage notice; bell link; notification counts; snack labels.
If mobile bell still redirects to Content Manager, share screenshot of the opened bell panel; another click overlay may be involved.

The patch was syntax checked but NOT executed against your Django project or tested in a browser.
