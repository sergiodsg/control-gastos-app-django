from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('nueva/', views.crear_organizacion, name='crear_organizacion'),
]
