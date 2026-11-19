Vishakha One - Update 13
========================
1. Content Manager now matches the new Shiksha-style portal UI (all pages + sign-in).
2. Application logos: upload sharper logos (Django admin, or Content Manager > Application logos).
3. Home page again carries everything the earlier home had (full What's Cooking week, Employee resources,
   all applications with "Show all", bigger lists of Insider / Bank benefits / Videos / Brochures / Joiners).
4. Copy documents and content: new commands  export_content  and  import_content  (see chat instructions).

Apply (PC):
  pip install -r requirements.txt        (nothing new in this update, safe to run)
  python manage.py migrate               (adds portal 0004 - application logo field)
  python manage.py test                  (expect 165 tests OK)
Server:  migrate, collectstatic --noinput, restart gunicorn.
