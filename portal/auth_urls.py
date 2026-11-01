from django.urls import path
from . import auth_views

app_name = "accounts"

urlpatterns = [
    path("login/", auth_views.employee_login, name="login"),
    path("signup/", auth_views.employee_signup, name="signup"),
    path("logout/", auth_views.employee_logout, name="logout"),
    path("switch-user/", auth_views.switch_user, name="switch_user"),
    path("sso/", auth_views.employee_sso, name="sso"),
]