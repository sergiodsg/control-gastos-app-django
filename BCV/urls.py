from django.urls import path

from . import views

urlpatterns = [
    path("rates/", views.rates_api, name="bcv_rates_api"),
]
