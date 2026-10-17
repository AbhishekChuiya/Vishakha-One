from django.urls import path
from . import views
app_name = 'portal'
urlpatterns = [path('', views.home, name='home'), path('search/', views.search, name='search'), path('<slug:slug>/', views.section, name='section')]
