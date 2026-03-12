from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LoginView, LogoutView
from users import views as users_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('helpcard.urls')),
    path('users/', include('users.urls')),
    path('accounts/login/', LoginView.as_view(
        template_name='users/login.html'
    ), name='login'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),  # Добавьте эту строку
    path('register/', users_views.register, name='register'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
