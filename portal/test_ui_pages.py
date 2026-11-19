"""The redesigned employee portal: every page renders, one search, a visible menu, live suggestions."""
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from contenthub.models import Announcement, CanteenDay, Event, JobOpening, NewJoiner, Resource
from employees.models import EmployeeProfile
from .models import CompanyApplication

User = get_user_model()
PASSWORD = "ui-test-password-7391-x"


def pub(model, **kw):
    kw.setdefault("is_published", True)
    kw.setdefault("approval_status", "approved")
    kw.setdefault("published_at", timezone.now() - timedelta(hours=1))
    return model.objects.create(**kw)


class PortalUiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("90001111", password=PASSWORD, first_name="Meera", last_name="Shah")
        EmployeeProfile.objects.create(user=cls.user, employee_id="90001111", company_email="meera.shah@vishakha.com")
        CompanyApplication.objects.create(name="Zyxwcorp Travel Desk", description="Book trips", category="Travel", url="https://example.com")
        CompanyApplication.objects.create(name="Unconfigured Tool", category="Other")
        pub(Announcement, title="UI Test Notice", summary="Notice body", category="announcement", priority="important")
        pub(Announcement, title="UI Test News", summary="News body", category="news")
        pub(Event, title="UI Test Event", summary="Event", starts_at=timezone.now() + timedelta(days=2), location="Hall")
        pub(Resource, title="UI Test Policy", summary="Policy text", kind="policy", external_url="https://example.com/p")
        pub(Resource, title="UI Test Video", summary="Video", kind="video", external_url="https://example.com/v")
        pub(JobOpening, title="UI Test Engineer", summary="Job", department="Engineering", location="Ahmedabad", apply_url="https://example.com/a")
        pub(NewJoiner, employee_name="Zara Quraishi", designation="Analyst", department="Finance", location="Mumbai")
        monday = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        CanteenDay.objects.create(date=timezone.localdate(), lunch_veg_dal="UI Test Dal")
        CanteenDay.objects.create(date=monday if monday != timezone.localdate() else monday + timedelta(days=1), is_holiday=True)

    def setUp(self):
        self.client.force_login(self.user)

    PAGES = ["/", "/apps/", "/news/", "/policies/", "/documents/", "/careers/", "/joiners/", "/services/", "/help/",
             "/profile/", "/notifications/", "/canteen-menu/", "/search/", "/search/?q=travl"]

    def test_every_employee_page_renders(self):
        for url in self.PAGES:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_every_page_requires_sign_in(self):
        anonymous = Client()
        for url in self.PAGES + ["/search/suggest/?q=abc"]:
            with self.subTest(url=url):
                self.assertEqual(anonymous.get(url).status_code, 302)

    def test_pilot_feedback_menu_is_visible_and_search_is_single(self):
        html = self.client.get("/").content.decode()
        # Dedicated, always-visible menu: the items that used to hide in the profile menu are in the sidebar.
        sidebar = html[html.index('class="vx-side"'):html.index('</aside>')]
        for label in ("Home", "My Apps", "News &amp; Events", "Policies", "Documents", "Careers", "New Joiners",
                      "Canteen Menu", "Employee Services", "Help"):
            self.assertIn(label, sidebar)
        # One search box, plus the Quick find jump list and the helpful-links bar the business asked for.
        self.assertEqual(html.count('id="vx-q"'), 1)
        self.assertIn("Quick find", html)
        self.assertIn('class="vx-links"', html)
        menu = html[html.index('id="vx-user"'):]
        menu = menu[:menu.index("</header>")]
        for label in ("My profile", "Weekly canteen menu", "My applications", "Search all content",
                      "Help &amp; support", "Dark mode", "Switch account", "Sign out"):
            self.assertIn(label, menu)
        self.assertNotIn("Content Manager", menu)      # ordinary employee: no Content Manager link

    def test_assistant_entry_points_are_not_repeated(self):
        html = self.client.get("/").content.decode()
        self.assertEqual(html.count('id="vx-fab"'), 1)
        self.assertEqual(html.count('id="vx-fab"'), 1)
        self.assertEqual(html.count("data-open-ai"), 2)       # header button (desktop) and dock button (phones)
        self.assertIn('id="vx-totop"', html)                  # back-to-top sits above the floating button

    def test_nothing_is_loaded_from_outside_the_portal(self):
        for url in ("/", "/apps/", "/accounts/login/"):
            html = self.client.get(url).content.decode()
            # Files the browser fetches by itself (styles, scripts, images, fonts) must all be local.
            self.assertNotRegex(html, r'<(?:link|script|img)\b[^>]*\b(?:src|href)="(?:https?:)?//', url)
            self.assertNotIn("googleapis", html)
            self.assertNotIn("gstatic", html)

    def test_design_assets_exist(self):
        for path in ("css/vone_ui.css", "js/vone_ui.js", "css/vone_auth.css", "js/vone_auth.js", "fonts/inter-latin.woff2",
                     "fonts/sora-latin.woff2", "assets/brand/vishakha-mascot-640.webp"):
            self.assertIsNotNone(finders.find(path), path)

    def test_home_shows_content_stats_and_todays_menu(self):
        page = self.client.get("/")
        self.assertContains(page, "Meera")
        self.assertContains(page, "UI Test News")
        self.assertContains(page, "UI Test Event")
        self.assertContains(page, "UI Test Dal")
        self.assertContains(page, "Zara Quraishi")
        self.assertContains(page, "UI Test Notice")                       # company notice banner
        self.assertContains(page, '<span class="vx-dot">1</span>')        # one unread notice in the bell
        self.assertContains(page, reverse("portal:notifications"))        # bell and "View all" go to company notifications
        self.assertContains(page, "Company notice")

    def test_apps_page_filters_and_marks_unconfigured_apps(self):
        page = self.client.get("/apps/")
        self.assertContains(page, "Zyxwcorp Travel Desk")
        self.assertContains(page, "Not configured yet")
        self.assertContains(page, 'data-fav="Zyxwcorp Travel Desk"')
        only = self.client.get("/apps/?category=Travel")
        self.assertContains(only, "Zyxwcorp Travel Desk")
        self.assertNotContains(only, "Unconfigured Tool")
        self.assertContains(self.client.get("/apps/?q=zyxwcorp"), "Zyxwcorp Travel Desk")

    def test_library_pages_show_cards_and_filters(self):
        self.assertContains(self.client.get("/news/"), "UI Test News")
        self.assertContains(self.client.get("/policies/"), "UI Test Policy")
        self.assertContains(self.client.get("/documents/?category=video"), "UI Test Video")
        self.assertNotContains(self.client.get("/documents/?category=video"), "UI Test Policy")
        self.assertContains(self.client.get("/careers/"), "UI Test Engineer")
        self.assertContains(self.client.get("/joiners/?q=quraishi"), "Zara Quraishi")
        self.assertNotContains(self.client.get("/joiners/?q=nobody-here"), "Zara Quraishi")

    def test_help_links_to_the_ticketing_portal(self):
        self.assertContains(self.client.get("/help/"), "vresolved.vishakhapolyfab.com")

    def test_profile_page_shows_employee_details(self):
        page = self.client.get("/profile/")
        self.assertContains(page, "90001111")
        self.assertContains(page, "meera.shah@vishakha.com")

    def test_canteen_closed_and_open_days(self):
        page = self.client.get("/canteen-menu/")
        self.assertContains(page, "UI Test Dal")
        self.assertContains(page, "data-today")

    def test_content_manager_link_only_for_content_managers(self):
        self.assertNotContains(self.client.get("/"), "Content Manager")
        admin = User.objects.create_superuser("ui_admin", "ui_admin@vishakha.com", PASSWORD)
        EmployeeProfile.objects.create(user=admin, employee_id="UIADMIN1", company_email="ui_admin@vishakha.com")
        self.client.force_login(admin)
        self.assertContains(self.client.get("/"), "Content Manager")


class SuggestEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user("90002222", password=PASSWORD)
        EmployeeProfile.objects.create(user=user, employee_id="90002222", company_email="finder.two@vishakha.com")
        CompanyApplication.objects.update_or_create(name="Quest2Travel", defaults={"category": "Travel", "url": "https://example.com", "is_active": True})
        CompanyApplication.objects.create(name="Hidden Zyxw Tool", category="Travel", is_active=False)
        pub(Resource, title="Travel & Expense Policy", summary="Rules", kind="policy", external_url="https://example.com/t")
        pub(Resource, title="Draft Travel Memo", summary="x", kind="policy", is_published=False)
        pub(NewJoiner, employee_name="Travis Roy", designation="Driver", department="Logistics")

    def setUp(self):
        self.client.force_login(User.objects.get(username="90002222"))

    def groups(self, q):
        return {g["title"]: g["items"] for g in self.client.get("/search/suggest/", {"q": q}).json()["groups"]}

    def test_typo_finds_apps_policies_and_people(self):
        groups = self.groups("trvel")
        self.assertIn("Quest2Travel", [i["title"] for i in groups["Applications"]])
        self.assertIn("Travel & Expense Policy", [i["title"] for i in groups["Policies & documents"]])
        self.assertEqual([i["title"] for i in self.groups("travs")["People"]], ["Travis Roy"])

    def test_unpublished_and_inactive_items_never_appear(self):
        everything = " ".join(i["title"] for items in self.groups("travel").values() for i in items)
        self.assertNotIn("Draft Travel Memo", everything)
        self.assertNotIn("Hidden", " ".join(i["title"] for items in self.groups("zyxw").values() for i in items))

    def test_pages_are_suggested_too_and_short_queries_return_nothing(self):
        self.assertIn("Canteen Menu", [i["title"] for i in self.groups("cantn")["Pages"]])
        self.assertEqual(self.client.get("/search/suggest/", {"q": "a"}).json(), {"groups": []})
        self.assertEqual(self.client.get("/search/suggest/").json(), {"groups": []})

    def test_results_carry_what_the_menu_needs(self):
        item = self.groups("quest")["Applications"][0]
        self.assertEqual(set(item), {"title", "sub", "url", "icon"})
        self.assertTrue(item["icon"].startswith("<"))
