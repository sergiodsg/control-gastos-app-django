from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import LoginForm

urlpatterns = [
    path('registro/', views.registro, name='registro'),
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html',
        form_class=LoginForm,
        extra_context={'hide_navbar': True, 'hide_sidebar': True}
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
