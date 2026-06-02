import html
import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation

import certifi
import requests
import urllib3
from django.core.cache import cache
from django.utils import timezone
from BCV.models import ExchangeRateHistory

BCV_URL = "https://www.bcv.org.ve/"
DOLARAPI_USD_URL = "https://ve.dolarapi.com/v1/dolares"
DOLARAPI_EUR_URL = "https://ve.dolarapi.com/v1/euros"
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
    value = re.sub(r"[^\d,\.]", "", value)
    if not value:
        return None

    # Soporta formatos: 557,9741 | 557.9741 | 1.234,5678 | 1,234.5678
    if "," in value and "." in value:
        # El ultimo separador suele ser el decimal.
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        value = value.replace(",", ".")

    try:
        return Decimal(value).quantize(Decimal("0.0001"))
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

    if not usd_rate and not eur_rate:
        raise ValueError("No se pudieron extraer tasas BCV de la pagina principal.")

    return {
        "rate_date": rate_date,
        "rates": {
            "USD": usd_rate,
            "EUR": eur_rate,
        },
        "raw_label": "Tipo de Cambio de Referencia",
        "source_url": BCV_URL,
        "fetched_at": timezone.now(),
        "source": ExchangeRateHistory.SOURCE_BCV,
    }


def _fetch_dolarapi_rates():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CDG/1.0; +https://github.com)"}
    usd_res = requests.get(DOLARAPI_USD_URL, headers=headers, timeout=20)
    eur_res = requests.get(DOLARAPI_EUR_URL, headers=headers, timeout=20)
    usd_res.raise_for_status()
    eur_res.raise_for_status()

    dolares = usd_res.json()
    euros = eur_res.json()

    def _find_official(items):
        for item in items:
            if str(item.get("fuente", "")).lower() == "oficial":
                return _decimal_from_ve_number(str(item.get("promedio", "")))
        return None

    usd_rate = _find_official(dolares if isinstance(dolares, list) else [])
    eur_rate = _find_official(euros if isinstance(euros, list) else [])
    if not usd_rate and not eur_rate:
        raise ValueError("DolarAPI no devolvio tasas oficiales validas.")

    return {
        "rate_date": timezone.localdate(),
        "rates": {
            "USD": usd_rate,
            "EUR": eur_rate,
        },
        "raw_label": "Tasa oficial fallback DolarAPI",
        "source_url": "https://ve.dolarapi.com",
        "fetched_at": timezone.now(),
        "source": ExchangeRateHistory.SOURCE_DOLARAPI,
    }


def get_dolarapi_parallel_rates_cached(ttl_seconds=1800, force_refresh=False):
    cache_key = "dolarapi_parallel_rates"
    if not force_refresh:
        cached = cache.get(cache_key)
    else:
        cached = None
    if cached:
        return cached

    headers = {"User-Agent": "Mozilla/5.0 (compatible; CDG/1.0; +https://github.com)"}
    usd_res = requests.get(DOLARAPI_USD_URL, headers=headers, timeout=20)
    eur_res = requests.get(DOLARAPI_EUR_URL, headers=headers, timeout=20)
    usd_res.raise_for_status()
    eur_res.raise_for_status()

    dolares_raw = usd_res.json()
    euros_raw = eur_res.json()
    dolares = dolares_raw if isinstance(dolares_raw, list) else []
    euros = euros_raw if isinstance(euros_raw, list) else []

    def _find_rate(items, source_slug):
        for item in items:
            if str(item.get("fuente", "")).lower() == source_slug:
                promedio = _decimal_from_ve_number(str(item.get("promedio", "")))
                if promedio is None:
                    return None
                return {
                    "promedio": float(promedio),
                    "fuente": item.get("fuente"),
                }
        return None

    payload = {
        "usd_paralelo": _find_rate(dolares, "paralelo"),
        "eur_paralelo": _find_rate(euros, "paralelo"),
    }
    cache.set(cache_key, payload, ttl_seconds)
    return payload


def _store_rates(payload):
    rate_date = payload["rate_date"]
    source = payload["source"]
    raw_label = payload.get("raw_label", "")
    for currency, rate in payload.get("rates", {}).items():
        if rate is None:
            continue
        ExchangeRateHistory.objects.update_or_create(
            rate_date=rate_date,
            source=source,
            currency=currency,
            defaults={
                "rate": rate,
                "raw_label": raw_label,
            },
        )


def scrape_with_fallback():
    try:
        return scrape_bcv_rates()
    except Exception:
        return _fetch_dolarapi_rates()


def get_bcv_rates_cached(ttl_seconds=3600, force_refresh=False):
    cache_key = "bcv_latest_rates"
    if not force_refresh:
        cached = cache.get(cache_key)
    else:
        cached = None
    if cached:
        return cached

    payload = scrape_with_fallback()
    _store_rates(payload)
    cache.set(cache_key, payload, ttl_seconds)
    return payload


def get_bcv_currency_rate(currency, default=None):
    payload = get_bcv_rates_cached()
    return payload.get("rates", {}).get(currency.upper(), default)


def get_rate_for_date(target_date, currency="USD", default=None):
    currency = currency.upper()
    preferred_sources = [ExchangeRateHistory.SOURCE_BCV, ExchangeRateHistory.SOURCE_DOLARAPI]
    for source in preferred_sources:
        obj = (
            ExchangeRateHistory.objects.filter(
                rate_date=target_date,
                source=source,
                currency=currency,
            )
            .order_by("-fetched_at")
            .first()
        )
        if obj:
            return obj.rate

    # Solo intentamos scrape en vivo para hoy.
    if target_date == timezone.localdate():
        payload = get_bcv_rates_cached(force_refresh=True)
        return payload.get("rates", {}).get(currency, default)

    return default


def as_dashboard_rates():
    """
    Convierte el payload BCV a la estructura usada por templates existentes.
    """
    payload = get_bcv_rates_cached()
    parallel_rates = get_dolarapi_parallel_rates_cached()
    usd = payload.get("rates", {}).get("USD")
    eur = payload.get("rates", {}).get("EUR")
    return {
        "usd_bcv": {"promedio": float(usd), "fuente": "BCV"} if usd is not None else None,
        "usd_paralelo": parallel_rates.get("usd_paralelo"),
        "eur_bcv": {"promedio": float(eur), "fuente": "BCV"} if eur is not None else None,
        "eur_paralelo": parallel_rates.get("eur_paralelo"),
        "rate_date": payload.get("rate_date"),
        "source": payload.get("source"),
    }