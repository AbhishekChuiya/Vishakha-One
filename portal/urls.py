from django.urls import path
from . import views
from contenthub import canteen_views
app_name = 'portal'
urlpatterns = [path('', views.home, name='home'), path('search/', views.search, name='search'), path('profile/', views.profile, name='profile'), path('canteen-menu/', canteen_views.employee_week, name='canteen_menu'), path('notifications/', views.notifications, name='notifications'), path('notifications/feed/', views.announcement_notification_feed, name='notification_feed'), path('notifications/read-all/', views.mark_all_announcements_read, name='notifications_read_all'), path('notifications/<int:pk>/read/', views.mark_announcement_read, name='notification_read'), path('<slug:slug>/', views.section, name='section')]
