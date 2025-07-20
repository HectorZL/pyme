from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.urls import reverse_lazy

class HomeView(TemplateView):
    template_name = 'anime/index.html'

class CatalogView(TemplateView):
    template_name = 'catalog.html'

class ProfileView(TemplateView):
    template_name = 'profile.html'

class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('anime:home')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)  # Log the user in after registration
        return response

# Create your views here.
