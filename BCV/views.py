from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from BCV.services.bcv_scrapper import as_dashboard_rates, get_rate_for_date


@require_GET
def rates_api(request):
    try:
        date_param = request.GET.get("date")
        currency = request.GET.get("currency", "USD").upper()
        if date_param:
            target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
            rate = get_rate_for_date(target_date, currency=currency)
            if rate is None:
                return JsonResponse({"ok": False, "error": "No hay tasa para la fecha solicitada."}, status=404)
            return JsonResponse(
                {
                    "ok": True,
                    "rate": float(rate),
                    "currency": currency,
                    "date": target_date.isoformat(),
                }
            )

        rates = as_dashboard_rates()
        return JsonResponse(
            {
                "ok": True,
                "rates": rates,
            }
        )
    except Exception as exc:
        return JsonResponse(
            {
                "ok": False,
                "error": str(exc),
            },
            status=502,
        )
