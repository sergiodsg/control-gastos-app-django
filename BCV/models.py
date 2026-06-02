from django.db import models


class ExchangeRateHistory(models.Model):
    SOURCE_BCV = "bcv"
    SOURCE_DOLARAPI = "dolarapi"
    SOURCE_CHOICES = [
        (SOURCE_BCV, "BCV"),
        (SOURCE_DOLARAPI, "DolarAPI"),
    ]

    CURRENCY_USD = "USD"
    CURRENCY_EUR = "EUR"
    CURRENCY_CHOICES = [
        (CURRENCY_USD, "Dolar"),
        (CURRENCY_EUR, "Euro"),
    ]

    rate_date = models.DateField(verbose_name="Fecha valor")
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_BCV,
        verbose_name="Fuente",
    )
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, verbose_name="Moneda")
    rate = models.DecimalField(max_digits=20, decimal_places=8, verbose_name="Tasa")
    fetched_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualizacion")
    raw_label = models.CharField(max_length=120, blank=True, verbose_name="Etiqueta original")

    class Meta:
        verbose_name = "Historico de tasa"
        verbose_name_plural = "Historicos de tasas"
        ordering = ("-rate_date", "currency")
        unique_together = ("rate_date", "source", "currency")

    def __str__(self):
        return f"{self.rate_date} {self.currency} {self.source}: {self.rate}"
