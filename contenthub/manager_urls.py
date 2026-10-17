from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache
from . import manager_views as views

app_name = 'content_manager'
urlpatterns = [
    path(
        "login/",
        ensure_csrf_cookie(LoginView.as_view(
            template_name="content_manager/login.html",
            next_page="/content-manager/",
        )),
        name="login",
    ),
    path('logout/', never_cache(LogoutView.as_view(next_page='content_manager:login')), name='logout'),
    path('notifications/', views.notification_center, name='notification_center'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='notifications_read_all'),
    path('approval-queue/', views.approval_queue, name='approval_queue'),
    path('approval-analytics/', views.approval_analytics, name='approval_analytics'),
    path('approval-analytics/export/', views.approval_analytics_export, name='approval_analytics_export'),
    path('approval-queue/export/', views.approval_queue_export, name='approval_queue_export'),
    path('', views.dashboard, name='dashboard'),
    path('notifications/<int:pk>/open/', views.mark_notification_read, name='notification_open'),
    path('<slug:slug>/', views.listing, name='list'),
    path('<slug:slug>/new/', views.edit, name='new'),
    path('<slug:slug>/<int:pk>/history/', views.approval_history, name='approval_history'),
    path('<slug:slug>/<int:pk>/edit/', views.edit, name='edit'),
    path('<slug:slug>/<int:pk>/delete/', views.delete, name='delete'),
    path('<slug:slug>/<int:pk>/review/', views.review, name='review'),
    path('<slug:slug>/<int:pk>/publish/', views.toggle_publish, name='publish'),
]
