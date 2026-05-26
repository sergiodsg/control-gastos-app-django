import html
import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation

import certifi
import requests
import urllib3
from django.utils import timezone

from organizations.models import ExchangeRateHistory

BCV_URL = "https://www.bcv.org.ve/"
SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def _decimal_from_ve_number(raw_value):
    value = (raw_value or "").strip()
    value = value.replace(".", "").replace(",", ".")
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _clean_html_to_text(raw_html):
    no_scripts = re.sub(r"<script[\s\S]*?</script>", " ", raw_html, flags=re.IGNORECASE)
    no_styles = re.sub(r"<style[\s\S]*?</style>", " ", no_scripts, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "\n", no_styles)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text


def _parse_bcv_value_date(text):
    match = re.search(r"Fecha\s*Valor:\s*([^\n\r]+)", text, flags=re.IGNORECASE)
    if not match:
        return timezone.localdate()

    label = match.group(1).strip()
    label = label.split(",", 1)[-1].strip() if "," in label else label
    date_match = re.search(r"(\d{1,2})\s+([A-Za-zÁÉÍÓÚáéíóú]+)\s+(\d{4})", label)
    if not date_match:
        return timezone.localdate()

    day = int(date_match.group(1))
    month_name = date_match.group(2).lower()
    month_name = (
        month_name.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
    year = int(date_match.group(3))
    month = SPANISH_MONTHS.get(month_name)
    if not month:
        return timezone.localdate()
    return date(year, month, day)


def _parse_rate_value(text, currency):
    match = re.search(rf"\b{currency}\b\s*([\d\.,]+)", text, flags=re.IGNORECASE)
    if not match:
        return None
    return _decimal_from_ve_number(match.group(1))


def scrape_bcv_rates():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CDG/1.0; +https://github.com)"}
    verify = os.environ.get("BCV_SSL_VERIFY", "true").lower() not in ("0", "false", "no")
    if verify:
        verify = certifi.where()
    else:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.get(
        BCV_URL,
        headers=headers,
        timeout=30,
        verify=verify,
    )
    response.raise_for_status()
    raw_html = response.text

    text = _clean_html_to_text(raw_html)
    rate_date = _parse_bcv_value_date(text)
    usd_rate = _parse_rate_value(text, "USD")
    eur_rate = _parse_rate_value(text, "EUR")

    rates = []
    if usd_rate:
        rates.append((ExchangeRateHistory.CURRENCY_USD, usd_rate))
    if eur_rate:
        rates.append((ExchangeRateHistory.CURRENCY_EUR, eur_rate))

    if not rates:
        raise ValueError("No se pudieron extraer tasas BCV de la pagina principal.")

    return {
        "rate_date": rate_date,
        "rates": rates,
        "raw_label": "Tipo de Cambio de Referencia",
    }


def store_bcv_rates(scraped_payload):
    stored = []
    updated = []
    rate_date = scraped_payload["rate_date"]
    raw_label = scraped_payload.get("raw_label", "")

    for currency, rate in scraped_payload["rates"]:
        obj, created = ExchangeRateHistory.objects.update_or_create(
            rate_date=rate_date,
            source=ExchangeRateHistory.SOURCE_BCV,
            currency=currency,
            defaults={"rate": rate, "raw_label": raw_label},
        )
        if created:
            stored.append(obj)
        else:
            updated.append(obj)

    return {"created": stored, "updated": updated, "rate_date": rate_date}


def scrape_and_store_bcv_rates():
    payload = scrape_bcv_rates()
    return store_bcv_rates(payload)


def get_bcv_rate_for_date(target_date):
    rate_obj = (
        ExchangeRateHistory.objects.filter(
            rate_date=target_date,
            source=ExchangeRateHistory.SOURCE_BCV,
            currency=ExchangeRateHistory.CURRENCY_USD,
        )
        .order_by("-fetched_at")
        .first()
    )
    return rate_obj.rate if rate_obj else None


def get_bcv_currency_rate_for_date(target_date, currency):
    rate_obj = (
        ExchangeRateHistory.objects.filter(
            rate_date=target_date,
            source=ExchangeRateHistory.SOURCE_BCV,
            currency=currency,
        )
        .order_by("-fetched_at")
        .first()
    )
    return rate_obj.rate if rate_obj else None
