from django.contrib import admin
from .models import (
    Organization,
    OrganizationAccess,
    Account,
    Category,
    Project,
    Valuation,
    Transaction,
    ExchangeRateHistory,
)

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(OrganizationAccess)
class OrganizationAccessAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'organization')
    list_filter = ('organization', 'user')
    search_fields = ('user__username', 'organization__name')

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'organization', 'created_at')
    list_filter = ('organization',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'organization', 'color')
    list_filter = ('organization',)
    search_fields = ('name',)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'organization')
    list_filter = ('organization',)
    search_fields = ('name',)

@admin.register(Valuation)
class ValuationAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'name', 'amount_usd', 'amount_bs')
    list_filter = ('project__organization',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'organization', 'account', 'amount_bs', 'amount_usd', 'status')
    list_filter = ('organization', 'status', 'date')
    search_fields = ('description', 'reference_number')
    date_hierarchy = 'date'


@admin.register(ExchangeRateHistory)
class ExchangeRateHistoryAdmin(admin.ModelAdmin):
    list_display = ("rate_date", "currency", "source", "rate", "fetched_at")
    list_filter = ("currency", "source", "rate_date")
    search_fields = ("raw_label",)
    date_hierarchy = "rate_date"
