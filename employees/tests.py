from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from .models import EmployeeProfile, is_company_email


class EmployeeProfileTests(TestCase):
    def test_only_vishakha_domain_is_accepted(self):
        self.assertTrue(is_company_email("person@vishakha.com"))
        self.assertTrue(is_company_email("PERSON@VISHAKHA.COM"))
        self.assertFalse(is_company_email("person@gmail.com"))
        self.assertFalse(is_company_email("person@sub.vishakha.com"))

    def test_profile_syncs_user_email(self):
        user = get_user_model().objects.create_user(username="profile-test", password="Strong-Test-Password-2026")
        profile = EmployeeProfile.objects.create(
            user=user,
            employee_id=" emp-100 ",
            company_email="PROFILE-TEST@VISHAKHA.COM",
        )
        user.refresh_from_db()
        self.assertEqual(profile.employee_id, "EMP-100")
        self.assertEqual(profile.company_email, "profile-test@vishakha.com")
        self.assertEqual(user.email, profile.company_email)

    def test_non_company_email_profile_is_rejected(self):
        user = get_user_model().objects.create_user(username="bad-domain", password="Strong-Test-Password-2026")
        with self.assertRaises(Exception):
            EmployeeProfile.objects.create(
                user=user,
                employee_id="BAD-100",
                company_email="person@gmail.com",
            )


class EmployeeLoginTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="employee-login-test",
            email="employee-login-test@vishakha.com",
            password="Valid-Test-Password-2026!",
        )
        EmployeeProfile.objects.create(
            user=self.user,
            employee_id="90002500",
            company_email=self.user.email,
        )
        self.client = Client()

    def test_login_by_employee_id(self):
        response = self.client.post(reverse("accounts:login"), {
            "identifier": "90002500",
            "password": "Valid-Test-Password-2026!",
        })
        self.assertRedirects(response, reverse("portal:home"), fetch_redirect_response=False)

    def test_login_by_company_email(self):
        response = self.client.post(reverse("accounts:login"), {
            "identifier": "employee-login-test@vishakha.com",
            "password": "Valid-Test-Password-2026!",
        })
        self.assertRedirects(response, reverse("portal:home"), fetch_redirect_response=False)

    def test_non_company_email_is_rejected(self):
        response = self.client.post(reverse("accounts:login"), {
            "identifier": "employee-login-test@gmail.com",
            "password": "Valid-Test-Password-2026!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())

    def test_anonymous_portal_redirects_to_employee_login(self):
        response = self.client.get(reverse("portal:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_inactive_employee_profile_cannot_access_portal(self):
        EmployeeProfile.objects.filter(user=self.user).update(is_active=False)
        self.client.force_login(self.user)
        response = self.client.get(reverse("portal:home"))
        self.assertEqual(response.status_code, 403)

    def test_employee_logout_ends_session(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_employee_account_has_no_content_manager_permissions(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("content_manager:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_employee_only_account_cannot_sign_in_to_content_manager(self):
        response = self.client.post(reverse("content_manager:login"), {
            "username": self.user.username,
            "password": "Valid-Test-Password-2026!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())

    def test_sso_and_content_manager_login_remain_public(self):
        self.assertEqual(self.client.get(reverse("accounts:sso")).status_code, 200)
        self.assertEqual(self.client.get(reverse("content_manager:login")).status_code, 200)

    def test_admin_login_is_not_redirected_to_employee_login(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)

    def test_admin_root_without_trailing_slash_is_not_intercepted(self):
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response["Location"].endswith("/admin/"))

    def test_superuser_can_authenticate_through_django_admin(self):
        admin_user = get_user_model().objects.create_superuser(
            username="admin-login-test",
            email="admin-login-test@vishakha.com",
            password="Valid-Admin-Password-2026!",
        )
        response = self.client.post("/admin/login/", {
            "username": admin_user.username,
            "password": "Valid-Admin-Password-2026!",
            "next": "/admin/",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].endswith("/admin/"))
