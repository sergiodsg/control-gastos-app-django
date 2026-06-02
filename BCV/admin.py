from django.contrib import admin
from BCV.models import ExchangeRateHistory


@admin.register(ExchangeRateHistory)
class ExchangeRateHistoryAdmin(admin.ModelAdmin):
    list_display = ("rate_date", "currency", "source", "rate", "fetched_at")
    list_filter = ("currency", "source", "rate_date")
    search_fields = ("rate_date", "raw_label")
