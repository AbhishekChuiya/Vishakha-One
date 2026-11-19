"""Typo-tolerant search: ranking rules and the employee search page."""
import random
import time

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from employees.models import EmployeeProfile
from . import fuzzy
from .models import CompanyApplication

ROWS = [
    {"t": "Quest2Travel", "s": "Travel booking"},
    {"t": "PeopleStrong", "s": "HR and people"},
    {"t": "Leave Policy", "s": "Annual and sick leave rules"},
    {"t": "Canteen Menu", "s": "Weekly lunch"},
    {"t": "SAP Fiori", "s": "ERP and Finance"},
    {"t": "Service Excellence Portal", "s": "Raise IT tickets"},
]
FIELDS = [("t", 1.0), ("s", 0.5)]


def titles(query):
    return [r["t"] for r in fuzzy.rank(query, ROWS, FIELDS)[0]]


class FuzzyRankingTests(SimpleTestCase):
    def test_exact_prefix_and_partial_words(self):
        self.assertEqual(titles("canteen"), ["Canteen Menu"])
        self.assertEqual(titles("peop")[0], "PeopleStrong")          # typing in progress
        self.assertIn("Quest2Travel", titles("travel"))               # word inside a longer name
        self.assertEqual(titles("SAP")[0], "SAP Fiori")               # case-insensitive, short exact word

    def test_typos_are_tolerated(self):
        self.assertEqual(titles("trvel")[0], "Quest2Travel")          # missing letter
        self.assertEqual(titles("peplestrong")[0], "PeopleStrong")    # wrong letter
        self.assertEqual(titles("canten")[0], "Canteen Menu")
        self.assertEqual(titles("excelence portal")[0], "Service Excellence Portal")
        self.assertEqual(titles("leav polcy")[0], "Leave Policy")     # two words, both misspelt
        self.assertEqual(titles("ticekts")[0], "Service Excellence Portal")  # swapped letters (summary)

    def test_unrelated_and_very_short_queries_do_not_match_noise(self):
        self.assertEqual(titles("zzzqq"), [])
        self.assertEqual(titles("xq"), [])
        self.assertNotIn("Leave Policy", titles("manu"))              # 'annual' is not a typo of 'manu'

    def test_every_word_must_match(self):
        self.assertEqual(titles("leave travel"), [])

    def test_suggestion_only_when_a_spelling_was_corrected(self):
        self.assertEqual(fuzzy.rank("trvel", ROWS, FIELDS)[1], "travel")
        self.assertEqual(fuzzy.rank("travel", ROWS, FIELDS)[1], "")
        self.assertEqual(fuzzy.rank("zzzqq", ROWS, FIELDS)[1], "")

    def test_title_matches_outrank_summary_matches(self):
        rows = [{"t": "Holiday list", "s": "Includes the leave calendar"}, {"t": "Leave Policy", "s": "Rules"}]
        self.assertEqual(fuzzy.rank("leave", rows, FIELDS)[0][0]["t"], "Leave Policy")

    def test_large_content_set_is_fast(self):
        rnd = random.Random(7)
        words = ["".join(rnd.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rnd.randint(4, 10))) for _ in range(1500)]
        rows = [{"t": " ".join(rnd.sample(words, 3)), "s": " ".join(rnd.sample(words, 8))} for _ in range(2000)]
        start = time.perf_counter()
        fuzzy.rank("travle polcy", rows, FIELDS)
        self.assertLess(time.perf_counter() - start, 3.0)


class SearchPageTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("90007777", password="Search-Test-Pass-7391-x")
        EmployeeProfile.objects.create(user=user, employee_id="90007777", company_email="finder@vishakha.com")
        self.client.login(username="90007777", password="Search-Test-Pass-7391-x")
        CompanyApplication.objects.create(name="Zyxwcorp Travel Desk", description="Book trips", category="Travel")
        CompanyApplication.objects.create(name="Hidden Zyxwcorp Tool", is_active=False)

    def search(self, q, **extra):
        return self.client.get(reverse("portal:search"), {"q": q, **extra})

    def test_exact_search_finds_it_without_a_correction_note(self):
        page = self.search("zyxwcorp")
        self.assertContains(page, "Zyxwcorp Travel Desk")
        self.assertNotContains(page, "Showing results for")

    def test_typo_search_finds_it_and_says_what_was_searched(self):
        page = self.search("zyxwcrp")
        self.assertContains(page, "Zyxwcorp Travel Desk")
        self.assertContains(page, "Showing results for")
        self.assertContains(page, "zyxwcorp")

    def test_inactive_applications_never_appear(self):
        self.assertNotContains(self.search("hidden zyxwcorp tool"), "Hidden Zyxwcorp Tool")

    def test_no_match_and_too_short_queries(self):
        self.assertContains(self.search("qqqqqqq"), "No matching published content found")
        self.assertContains(self.search("a"), "at least two characters")

    def test_type_filter_still_limits_the_results(self):
        self.assertContains(self.search("zyxwcrp", type="apps"), "Zyxwcorp Travel Desk")
        self.assertNotContains(self.search("zyxwcrp", type="news"), "Zyxwcorp Travel Desk")

    def test_search_requires_sign_in(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("portal:search"), {"q": "zyxwcorp"}).status_code, 302)
