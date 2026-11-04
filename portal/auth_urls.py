from django.urls import path
from . import auth_views

app_name = "accounts"

urlpatterns = [
    path("login/", auth_views.employee_login, name="login"),
    path("logout/", auth_views.employee_logout, name="logout"),
    path("switch-user/", auth_views.switch_user, name="switch_user"),
    path("sso/", auth_views.employee_sso, name="sso"),
    path("register/", auth_views.register, name="register"),
    path("register/sent/", auth_views.register_done, name="register_done"),
    path("activate/<str:token>/", auth_views.activate, name="activate"),
    path("password-reset/", auth_views.EmployeePasswordResetView.as_view(), name="password_reset"),
    path("password-reset/sent/", auth_views.EmployeePasswordResetDoneView.as_view(), name="password_reset_done"),
    path("password-reset/complete/", auth_views.EmployeePasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("password-reset/<uidb64>/<token>/", auth_views.EmployeePasswordResetConfirmView.as_view(), name="password_reset_confirm"),
]
