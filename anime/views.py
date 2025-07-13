from django.shortcuts import render, redirect
from django.views.generic import TemplateView

class HomeView(TemplateView):
    template_name = 'anime/index.html'

class CatalogView(TemplateView):
    template_name = 'catalog.html'

class ProfileView(TemplateView):
    template_name = 'profile.html'

# Create your views here.
