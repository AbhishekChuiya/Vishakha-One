"""Regular vs chef's special snacks, the two-week editor, and what employees see."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from employees.models import EmployeeProfile
from .canteen_views import week_start
from .models import CanteenDay

User = get_user_model()
PW = "Snack-Test-Pass-4410-x"


class SnackTests(TestCase):
    def setUp(self):
        self.mgr = User.objects.create_user("snackmgr", password=PW)
        self.mgr.user_permissions.add(Permission.objects.get(codename="manage_canteen_menu"))
        self.emp = User.objects.create_user("90006000", password=PW, email="e.m@vishakha.com")
        EmployeeProfile.objects.create(user=self.emp, employee_id="90006000", company_email="e.m@vishakha.com")
        self.monday = week_start(None)

    def _post(self, extra):
        c = Client(); c.force_login(self.mgr)
        post = {"week": self.monday.isoformat()}
        post.update(extra)
        return c.post(reverse("content_manager:canteen_menu"), post)

    def test_editor_shows_this_week_and_next_week(self):
        c = Client(); c.force_login(self.mgr)
        page = c.get(reverse("content_manager:canteen_menu")).content.decode()
        self.assertIn("This week", page); self.assertIn("Next week", page)
        self.assertEqual(page.count('class="day-form'), 12)
        self.assertIn("Chef&#x27;s special", page)

    def test_saving_snack_types_and_skipping_untouched_days(self):
        wed, thu = self.monday + timedelta(days=2), self.monday + timedelta(days=3)
        nxt = self.monday + timedelta(days=8)
        self._post({f"{wed}-snack_type": "regular", f"{wed}-snacks": "Maggie",
                    f"{thu}-snack_type": "special", f"{thu}-snacks": "Pasta",
                    f"{nxt}-snack_type": "regular", f"{nxt}-snacks": "Bhel"})
        self.assertEqual(CanteenDay.objects.count(), 3)                    # blank days were not created
        self.assertEqual(CanteenDay.objects.get(date=thu).snack_type, "special")
        self.assertEqual(CanteenDay.objects.get(date=wed).snack_type, "regular")
        self.assertTrue(CanteenDay.objects.get(date=nxt).snacks == "Bhel")

    def test_holiday_clears_everything_including_snack(self):
        d = self.monday
        self._post({f"{d}-is_holiday": "on", f"{d}-snack_type": "special", f"{d}-snacks": "ignored", f"{d}-lunch_roti": "ignored"})
        row = CanteenDay.objects.get(date=d)
        self.assertEqual((row.snacks, row.lunch_roti, row.snack_type), ("", "", "regular"))

    def test_employees_see_special_highlighted_and_regular_plain(self):
        CanteenDay.objects.create(date=self.monday, lunch_veg_dal="Dal", snack_type="special", snacks="Wood-fired pizza")
        CanteenDay.objects.create(date=self.monday + timedelta(days=1), lunch_veg_dal="Dal", snack_type="regular", snacks="Maggie")
        c = Client(); c.force_login(self.emp)
        page = c.get("/canteen-menu/").content.decode()
        self.assertIn("Wood-fired pizza", page); self.assertIn("badge-special", page)
        self.assertIn("Maggie", page); self.assertIn("Regular snacks", page)
        self.assertEqual(page.count("badge-special"), 1)

    def test_employees_never_see_next_weeks_menu(self):
        nxt = self.monday + timedelta(days=7)
        CanteenDay.objects.create(date=nxt, lunch_veg_dal="SECRET NEXT WEEK DISH")
        c = Client(); c.force_login(self.emp)
        self.assertNotIn("SECRET NEXT WEEK DISH", c.get("/").content.decode())
        self.assertNotIn("SECRET NEXT WEEK DISH", c.get("/canteen-menu/").content.decode())
        self.assertNotIn("SECRET NEXT WEEK DISH", c.get(f"/canteen-menu/?week={nxt.isoformat()}").content.decode())

    def test_old_filled_snacks_became_specials_by_the_migration_rule(self):
        # (documented rule: before this feature a filled-in snack was shown as the chef's special)
        CanteenDay.objects.create(date=self.monday, snacks="Old entry")
        self.assertEqual(CanteenDay.objects.get().snack_type, "regular")    # new rows default to regular
