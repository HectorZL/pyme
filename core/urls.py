from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('anime.urls', namespace='anime')),  # Main anime app URLs
    
    # Redirect Django's default /accounts/profile/ to our custom profile page
    path('accounts/profile/', RedirectView.as_view(pattern_name='anime:profile', permanent=False)),
    
    # Redirect root URL to the home page
    path('', RedirectView.as_view(url='/', permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + \
    static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
