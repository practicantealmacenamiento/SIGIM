"""Limitador para uso mensual de Cloud Vision OCR.

Funcionamiento: Se limita el número de llamadas OCR mensuales a un máximo de 1999 (configurable).
Cada vez que se realiza una extracción OCR, se incrementa el contador del mes actual.
Si se supera el límite, se lanza una excepción `UsageLimitExceededError`.

El limite se establece en `core.settings.VISION_MAX_PER_MONTH`."""
from __future__ import annotations
from django.db import models

class VisionMonthlyUsage(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()
    count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("year", "month"),)
        indexes = [
            models.Index(fields=["year", "month"], name="vision_month_idx"),
        ]
        verbose_name = "Uso mensual Vision"
        verbose_name_plural = "Usos mensuales Vision"

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d} => {self.count}"
