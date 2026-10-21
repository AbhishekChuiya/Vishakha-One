Vishakha One A1.6 — Evening snack label update

This is a targeted patch script (not a replacement of your whole homepage).
It changes on both homepage and /canteen-menu/:
- "Evening snacks" -> "Evening Chef's Special Snacks"
- Blank snack field: "Not scheduled" -> "Regular Snacks available"

Other lunch-field "Not scheduled" labels remain unchanged.
Holidays still show "Canteen closed". Days without a saved menu still
show "Menu not updated yet" (the fallback only applies to an existing menu
whose snacks field is blank).

Installation in Windows PowerShell:
1. Extract this ZIP into D:\Projects\VishakhaOne\scripts\a1_6\
2. In D:\Projects\VishakhaOne, run:
   python scripts/a1_6/apply_snack_labels.py
3. Run: python manage.py check
4. Restart the server and hard-refresh (Ctrl+Shift+R).

The script makes one .bak_a1_6 backup per modified template and can be
run again safely. No migration is required.
