from datetime import date
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from BCV.models import ExchangeRateHistory
from organizations.models import Account, Organization, Transaction
from organizations.views import get_bcv_rate


class BCVHistoryAndTransactionsIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.org = Organization.objects.create(name="Org Test")
        self.account = Account.objects.create(organization=self.org, name="Caja")

    def test_get_rate_for_date_api_uses_history_table(self):
        target_date = date(2026, 6, 2)
        ExchangeRateHistory.objects.create(
            rate_date=target_date,
            source=ExchangeRateHistory.SOURCE_BCV,
            currency=ExchangeRateHistory.CURRENCY_USD,
            rate=Decimal("557.9741"),
            raw_label="BCV",
        )

        response = self.client.get(
            reverse("bcv_rates_api"),
            {"date": target_date.isoformat(), "currency": "USD"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["date"], target_date.isoformat())
        self.assertEqual(payload["currency"], "USD")
        self.assertEqual(payload["rate"], 557.9741)

    def test_organizations_get_bcv_rate_prefers_bcv_over_dolarapi(self):
        target_date = date(2026, 6, 2)
        ExchangeRateHistory.objects.create(
            rate_date=target_date,
            source=ExchangeRateHistory.SOURCE_DOLARAPI,
            currency=ExchangeRateHistory.CURRENCY_USD,
            rate=Decimal("551.0000"),
            raw_label="DolarAPI",
        )
        ExchangeRateHistory.objects.create(
            rate_date=target_date,
            source=ExchangeRateHistory.SOURCE_BCV,
            currency=ExchangeRateHistory.CURRENCY_USD,
            rate=Decimal("557.9741"),
            raw_label="BCV",
        )

        rate = get_bcv_rate(target_date=target_date)
        self.assertEqual(rate, 557.9741)

    def test_transaction_can_use_historic_rate_for_selected_date(self):
        target_date = date(2026, 6, 2)
        ExchangeRateHistory.objects.create(
            rate_date=target_date,
            source=ExchangeRateHistory.SOURCE_BCV,
            currency=ExchangeRateHistory.CURRENCY_USD,
            rate=Decimal("557.9741"),
            raw_label="BCV",
        )

        rate = Decimal(str(get_bcv_rate(target_date=target_date)))
        transaction = Transaction.objects.create(
            date=target_date,
            organization=self.org,
            account=self.account,
            description="Pago prueba",
            amount_usd=Decimal("10.00"),
            amount_bs=(Decimal("10.00") * rate).quantize(Decimal("0.01")),
            daily_rate=rate,
            status="completado",
        )

        self.assertEqual(transaction.date, target_date)
        self.assertEqual(transaction.daily_rate, Decimal("557.9741"))
        self.assertEqual(transaction.amount_bs, Decimal("5579.74"))
