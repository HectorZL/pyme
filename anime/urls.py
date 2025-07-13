from django.urls import path
from . import views

app_name = 'anime'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('catalog/', views.CatalogView.as_view(), name='catalog'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
]
