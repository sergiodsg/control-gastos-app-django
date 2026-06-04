import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from BCV.services.bcv_scrapper import get_bcv_rates_cached

logger = logging.getLogger('cashflow.cron.bcv')


class Command(BaseCommand):
    help = "Obtiene y guarda las tasas BCV del dia desde https://www.bcv.org.ve/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--window-hours",
            default="09,15",
            help="Horas permitidas (24h, separadas por coma) para ejecución automática. Ej: 09,15",
        )
        parser.add_argument(
            "--strict-window",
            action="store_true",
            help="Si se activa, solo ejecuta dentro de las horas configuradas en --window-hours.",
        )

    def _parse_window_hours(self, raw_hours):
        hours = set()
        for chunk in raw_hours.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            hour = int(chunk)
            if hour < 0 or hour > 23:
                raise ValueError(f"Hora inválida: {hour}. Debe estar entre 0 y 23.")
            hours.add(hour)
        if not hours:
            raise ValueError("Debes indicar al menos una hora válida en --window-hours.")
        return hours

    def handle(self, *args, **options):
        started_at = timezone.localtime()
        logger.info("Inicio sincronización BCV (cron)")

        try:
            window_hours = self._parse_window_hours(options["window_hours"])
        except Exception as exc:
            logger.exception("Parámetros inválidos en comando bcv")
            raise CommandError(str(exc)) from exc

        current_hour = timezone.localtime().hour
        if options["strict_window"] and current_hour not in window_hours:
            allowed = ",".join(f"{hour:02d}:00" for hour in sorted(window_hours))
            message = (
                f"Saltado: hora actual {current_hour:02d}:00 fuera de ventana ({allowed})."
            )
            logger.info(message)
            self.stdout.write(self.style.WARNING(message))
            return

        try:
            result = get_bcv_rates_cached(ttl_seconds=3600, force_refresh=True)
        except Exception as exc:
            logger.exception("Error al sincronizar tasas BCV")
            raise CommandError(f"No se pudo sincronizar tasas BCV: {exc}") from exc

        rate_date = result["rate_date"]
        usd = result["rates"].get("USD")
        eur = result["rates"].get("EUR")
        message = (
            f"Tasas BCV sincronizadas para {rate_date}. USD: {usd} | EUR: {eur}."
        )
        elapsed = (timezone.localtime() - started_at).total_seconds()
        logger.info("%s Duración: %.1fs", message, elapsed)
        self.stdout.write(self.style.SUCCESS(message))
