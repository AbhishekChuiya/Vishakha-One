"""Apply the snack wording change to current Vishakha One templates, preserving other changes."""
from pathlib import Path
import shutil
from datetime import datetime

base = Path(__file__).resolve().parent.parent
targets = [
    base / "templates/portal/home.html",
    base / "templates/portal/canteen_week.html",
]
old = "Evening snacks"
new = "Evening Chef's Special Snacks"
old_default = "day.menu.snacks|default:'Not scheduled'"
new_default = "day.menu.snacks|default:'Regular Snacks available'"
for target in targets:
    if not target.is_file():
        print(f"SKIP (missing): {target}")
        continue
    source = target.read_text(encoding="utf-8")
    updated = source.replace(old, new).replace(old_default, new_default)
    if updated == source:
        print(f"UNCHANGED: {target.relative_to(base)}")
        continue
    backup = target.with_name(target.name + ".bak_a1_6")
    if not backup.exists():
        shutil.copy2(target, backup)
    target.write_text(updated, encoding="utf-8")
    print(f"UPDATED: {target.relative_to(base)} (backup: {backup.name})")
print("Done. Restart Django and refresh the browser.")
