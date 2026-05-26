from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from organizations.models import ExchangeRateHistory, Transaction
from organizations.services.bcv_scraper import store_bcv_rates


@pytest.fixture
def transaction_payload(account):
    def _payload(tx_date, manual_rate="0"):
        return {
            "date": tx_date.isoformat(),
            "account": str(account.id),
            "reference_number": "REF-01",
            "description": "Compra de prueba",
            "notes": "",
            "category": "",
            "project": "",
            "valuation": "",
            "status": "completado",
            "amount_bs": "530.00",
            "amount_usd": "1.00",
            "daily_rate": "530.0000",
            "manual_rate": manual_rate,
        }

    return _payload


@pytest.mark.django_db
def test_rechaza_transaccion_con_fecha_futura(authenticated_client, transaction_payload):
    future_date = timezone.localdate() + timedelta(days=1)
    authenticated_client.post(
        reverse("crear_transaccion"),
        transaction_payload(future_date),
        follow=True,
    )
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_fecha_pasada_sin_historico_requiere_tasa_manual(authenticated_client, transaction_payload):
    past_date = timezone.localdate() - timedelta(days=2)
    authenticated_client.post(
        reverse("crear_transaccion"),
        transaction_payload(past_date, manual_rate="0"),
        follow=True,
    )
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_fecha_pasada_sin_historico_permite_tasa_manual(authenticated_client, transaction_payload):
    past_date = timezone.localdate() - timedelta(days=3)
    authenticated_client.post(
        reverse("crear_transaccion"),
        transaction_payload(past_date, manual_rate="1"),
        follow=True,
    )
    assert Transaction.objects.count() == 1


@pytest.mark.django_db
def test_creacion_usa_tasa_historica_disponible(authenticated_client, transaction_payload):
    target_date = timezone.localdate() - timedelta(days=1)
    ExchangeRateHistory.objects.create(
        rate_date=target_date,
        source=ExchangeRateHistory.SOURCE_BCV,
        currency=ExchangeRateHistory.CURRENCY_USD,
        rate=Decimal("580.1234"),
        raw_label="BCV",
    )
    authenticated_client.post(
        reverse("crear_transaccion"),
        transaction_payload(target_date, manual_rate="0"),
        follow=True,
    )
    tx = Transaction.objects.first()
    assert tx is not None
    assert tx.daily_rate == Decimal("580.1234")


@pytest.mark.django_db
def test_pdf_endpoint_responde_con_application_pdf(authenticated_client, organization, account):
    Transaction.objects.create(
        organization=organization,
        account=account,
        date=timezone.localdate(),
        description="Ingreso QA",
        amount_bs=Decimal("1000.00"),
        amount_usd=Decimal("2.00"),
        daily_rate=Decimal("500.0000"),
        status="completado",
    )
    response = authenticated_client.get(reverse("exportar_pdf_transacciones"))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


@pytest.mark.django_db
def test_store_bcv_rates_es_idempotente():
    payload = {
        "rate_date": timezone.localdate(),
        "raw_label": "Tipo de Cambio",
        "rates": [
            (ExchangeRateHistory.CURRENCY_USD, Decimal("530.12340000")),
            (ExchangeRateHistory.CURRENCY_EUR, Decimal("620.00000000")),
        ],
    }
    result_1 = store_bcv_rates(payload)
    result_2 = store_bcv_rates(payload)

    assert len(result_1["created"]) == 2
    assert len(result_2["created"]) == 0
    assert ExchangeRateHistory.objects.count() == 2
