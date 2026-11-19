"""Weekly canteen menu: sample file, upload parsing, and the fill-for-review flow."""
import io
import zipfile
from datetime import date, datetime
from unittest import mock

import openpyxl
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from . import canteen_import as ci
from .models import CanteenDay

User = get_user_model()
PASSWORD = "Canteen-Test-Pass-7391-x"
MONDAY = date(2026, 11, 23)


def xlsx_bytes(rows, header=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(header or [h for h, _ in ci.SAMPLE_COLUMNS])
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def csv_bytes(text):
    return text.encode("utf-8")


class ParserTests(SimpleTestCase):
    def test_sample_round_trips_through_the_parser(self):
        data, name, _ = ci.build_sample(MONDAY)
        result = ci.parse_upload(name, data)
        self.assertEqual(result.monday, MONDAY)
        self.assertEqual(len(result.rows), 12)                                  # this week + next week
        self.assertEqual(result.rows[date(2026, 11, 23)]["lunch_veg_dal"], "Aloo Gobi, Dal Tadka")
        self.assertEqual((result.rows[date(2026, 11, 23)]["snack_type"], result.rows[date(2026, 11, 23)]["snacks"]), ("regular", "Maggie"))
        self.assertEqual(result.rows[date(2026, 11, 26)]["snack_type"], "special")
        self.assertTrue(result.rows[date(2026, 11, 28)]["is_holiday"])
        self.assertTrue(result.rows[date(2026, 12, 5)]["is_holiday"])
        self.assertEqual(result.warnings, [])

    def test_csv_with_semicolons_other_date_styles_and_synonym_headings(self):
        text = ("Date;Closed;Sabzi / Dal;Roti;Rice;Sweet;Snacks\n"
                "24/11/2026;No;Mix Veg;Phulka;Rice;Kheer;Tea\n"
                "25-Nov-2026;;Chole;;;;-\n"
                "26 Nov 2026;yes;ignored dish;;;;\n")
        result = ci.parse_upload("week.csv", csv_bytes(text))
        self.assertEqual(result.monday, MONDAY)
        self.assertEqual(result.rows[date(2026, 11, 24)]["lunch_curd"], "Kheer")
        self.assertEqual(result.rows[date(2026, 11, 25)]["snacks"], "")          # '-' means nothing served
        self.assertTrue(result.rows[date(2026, 11, 26)]["is_holiday"])
        self.assertEqual(result.rows[date(2026, 11, 26)]["lunch_veg_dal"], "")   # holiday clears the menu

    def test_real_excel_dates_and_serial_numbers(self):
        data = xlsx_bytes([[datetime(2026, 11, 23), "No", "Dal", "Roti", "Rice", "Curd", "Tea"],
                           [46350, "No", "Sabzi", "", "", "", ""]])   # 46350 = 2026-11-24 as a plain number
        result = ci.parse_upload("w.xlsx", data)
        self.assertEqual(sorted(result.rows), [date(2026, 11, 23), date(2026, 11, 24)])

    def test_warnings_for_sunday_bad_dates_duplicates_and_long_text(self):
        long_text = "x" * 400
        data = xlsx_bytes([
            [date(2026, 11, 29), "No", "Sunday dish", "", "", "", ""],
            ["not a date", "No", "Mystery", "", "", "", ""],
            [date(2026, 11, 23), "No", long_text, "", "", "", ""],
            [date(2026, 11, 23), "No", "Second row wins", "", "", "", ""],
        ])
        result = ci.parse_upload("w.xlsx", data)
        text = " ".join(result.warnings)
        self.assertIn("Sunday", text)
        self.assertIn("not understood", text)
        self.assertIn("more than once", text)
        self.assertEqual(result.rows[MONDAY]["lunch_veg_dal"], "Second row wins")
        long_row = ci.parse_upload("w.csv", csv_bytes("Date,Veg / Dal\n2026-11-23," + long_text + "\n"))
        self.assertEqual(len(long_row.rows[MONDAY]["lunch_veg_dal"]), 300)
        self.assertIn("shortened", " ".join(long_row.warnings))

    def test_two_weeks_are_loaded_and_later_dates_are_left_out(self):
        result = ci.parse_upload("w.csv", csv_bytes("Date,Veg / Dal\n2026-11-24,A\n2026-12-01,B\n2026-12-08,C\n"))
        self.assertEqual(list(result.rows), [date(2026, 11, 24), date(2026, 12, 1)])
        self.assertIn("more than two weeks", " ".join(result.warnings))

    def test_snack_type_column_and_prefix_styles_are_understood(self):
        text = ("Date,Snack Type,Snack Name\n"
                "2026-11-23,Regular,Maggie\n"
                "2026-11-24,Chef's Special,Pasta\n"
                "2026-11-25,,Chef's Special - Pizza\n"
                "2026-11-26,,Regular snack - Bhel\n"
                "2026-11-27,,Sandwich\n")
        rows = ci.parse_upload("w.csv", csv_bytes(text)).rows
        got = {d.day: (v["snack_type"], v["snacks"]) for d, v in rows.items()}
        self.assertEqual(got, {23: ("regular", "Maggie"), 24: ("special", "Pasta"), 25: ("special", "Pizza"),
                               26: ("regular", "Bhel"), 27: ("regular", "Sandwich")})

    def test_unusable_files_give_clear_messages(self):
        bad = {
            ("menu.txt", b"hello"): "Excel (.xlsx) or CSV",
            ("menu.csv", b""): "Could not find the menu table",
            ("menu.csv", b"Name,Age\nA,1\n"): "Could not find the menu table",
            ("menu.csv", b"Date,Veg / Dal\n"): "No menu rows",
            ("menu.xlsx", b"this is not a zip"): "valid Excel",
            ("menu.csv", b"x" * (ci.MAX_UPLOAD_BYTES + 1)): "larger than 1 MB",
        }
        for (name, data), expected in bad.items():
            with self.assertRaises(ci.ImportProblem, msg=name) as caught:
                ci.parse_upload(name, data)
            self.assertIn(expected, str(caught.exception), name)

    def test_zip_bomb_is_refused(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("xl/big.bin", b"\0" * (25 * 1024 * 1024))
        self.assertLess(len(buffer.getvalue()), ci.MAX_UPLOAD_BYTES)
        with self.assertRaises(ci.ImportProblem) as caught:
            ci.parse_upload("bomb.xlsx", buffer.getvalue())
        self.assertIn("unexpectedly large", str(caught.exception))

    def test_without_excel_support_csv_still_works(self):
        with mock.patch.object(ci, "openpyxl", None):
            data, name, ctype = ci.build_sample(MONDAY)
            self.assertTrue(name.endswith(".csv"))
            self.assertEqual(len(ci.parse_upload(name, data).rows), 12)
            with self.assertRaises(ci.ImportProblem) as caught:
                ci.parse_upload("w.xlsx", b"PK")
            self.assertIn("save the file as CSV", str(caught.exception))


class CanteenUploadFlowTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user("cm_manager", password=PASSWORD)
        self.manager.user_permissions.add(Permission.objects.get(codename="manage_canteen_menu"))
        User.objects.create_user("plain_user", password=PASSWORD)

    def login(self, username="cm_manager"):
        self.assertTrue(self.client.login(username=username, password=PASSWORD))

    def upload(self, name, data, week="2026-11-23"):
        return self.client.post(reverse("content_manager:canteen_upload"),
                                {"week": week, "menu_file": SimpleUploadedFile(name, data)})

    def messages(self, response):
        return [str(m) for m in get_messages(response.wsgi_request)]

    def test_sample_download(self):
        self.login()
        response = self.client.get(reverse("content_manager:canteen_sample"), {"week": "2026-11-25"})  # a Wednesday
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])
        self.assertIn("canteen_menu_sample_2026-11-23.xlsx", response["Content-Disposition"])
        wb = openpyxl.load_workbook(io.BytesIO(response.content))
        self.assertEqual(wb.sheetnames, ["Menu", "How to fill"])
        ws = wb["Menu"]
        self.assertEqual([c.value for c in ws[1]], [h for h, _ in ci.SAMPLE_COLUMNS])
        self.assertEqual([ws.cell(row=r, column=1).value.date() for r in range(2, 14)],
                         [date(2026, 11, 23) + __import__("datetime").timedelta(days=i) for i in (0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12)])
        self.assertEqual(len(ws.data_validations.dataValidation), 2)

    def test_only_canteen_managers_can_use_the_feature(self):
        for url in ("content_manager:canteen_sample",):
            self.assertEqual(self.client.get(reverse(url)).status_code, 302)  # anonymous -> sign in
        self.login("plain_user")
        self.assertEqual(self.client.get(reverse("content_manager:canteen_sample")).status_code, 403)
        self.assertEqual(self.upload("w.csv", b"Date,Veg / Dal\n2026-11-23,A\n").status_code, 403)
        self.assertEqual(CanteenDay.objects.count(), 0)

    def test_upload_fills_the_form_but_saves_nothing_until_save_is_pressed(self):
        self.login()
        data, name, _ = ci.build_sample(MONDAY)
        response = self.upload(name, data)
        self.assertRedirects(response, f"{reverse('content_manager:canteen_menu')}?week=2026-11-23", fetch_redirect_response=False)
        self.assertEqual(CanteenDay.objects.count(), 0)                       # nothing saved yet
        page = self.client.get(response["Location"])
        self.assertContains(page, "Loaded 12 days from")
        self.assertContains(page, "Aloo Gobi, Dal Tadka")                     # form is filled in
        self.assertContains(page, "Pasta in white sauce")
        # Admin presses Save with the values shown.
        post = {"week": "2026-11-23"}
        for day, values in ci.parse_upload(name, data).rows.items():
            prefix = day.isoformat()
            if values["is_holiday"]:
                post[f"{prefix}-is_holiday"] = "on"
            for field in ci.MENU_FIELDS + ("snack_type",):
                post[f"{prefix}-{field}"] = values[field]
        saved = self.client.post(reverse("content_manager:canteen_menu"), post)
        self.assertEqual(saved.status_code, 302)
        self.assertEqual(CanteenDay.objects.count(), 12)
        self.assertEqual(CanteenDay.objects.get(date=date(2026, 11, 24)).lunch_veg_dal, "Paneer Butter Masala, Dal Fry")
        self.assertTrue(CanteenDay.objects.get(date=date(2026, 11, 28)).is_holiday)
        self.assertNotContains(self.client.get(saved["Location"]), "Loaded 12 days")  # cleared after saving

    def test_upload_for_another_week_opens_that_week_and_existing_days_are_kept(self):
        self.login()
        CanteenDay.objects.create(date=date(2026, 12, 1), lunch_veg_dal="Already saved dish")
        response = self.upload("next.csv", csv_bytes("Date,Veg / Dal\n2026-12-02,Uploaded dish\n"), week="2026-11-23")
        self.assertIn("week=2026-11-30", response["Location"])
        page = self.client.get(response["Location"])
        self.assertContains(page, "Uploaded dish")
        self.assertContains(page, "Already saved dish")                       # untouched day keeps saved value

    def test_discard_removes_the_loaded_values(self):
        self.login()
        response = self.upload("w.csv", csv_bytes("Date,Veg / Dal\n2026-11-23,Temp dish\n"))
        self.assertContains(self.client.get(response["Location"]), "Temp dish")
        gone = self.client.get(reverse("content_manager:canteen_menu"), {"week": "2026-11-23", "discard": "1"})
        self.assertNotContains(gone, "Temp dish")

    def test_bad_uploads_show_a_message_and_change_nothing(self):
        self.login()
        for name, data, expected in [("menu.txt", b"x", "Excel (.xlsx) or CSV"), ("m.csv", b"Name\nA\n", "Could not find"),
                                     ("m.xlsx", b"nope", "valid Excel")]:
            response = self.upload(name, data)
            self.assertEqual(response.status_code, 302)
            self.assertIn(expected, " ".join(self.messages(response)))
        no_file = self.client.post(reverse("content_manager:canteen_upload"), {"week": "2026-11-23"})
        self.assertIn("choose a file", " ".join(self.messages(no_file)))
        self.assertEqual(CanteenDay.objects.count(), 0)

    def test_upload_requires_post(self):
        self.login()
        self.assertEqual(self.client.get(reverse("content_manager:canteen_upload")).status_code, 405)

    def test_editor_page_offers_the_sample_and_upload(self):
        self.login()
        page = self.client.get(reverse("content_manager:canteen_menu"), {"week": "2026-11-23"})
        self.assertContains(page, "Download sample file")
        self.assertContains(page, "enctype=\"multipart/form-data\"")
        self.assertContains(page, reverse("content_manager:canteen_sample"))
