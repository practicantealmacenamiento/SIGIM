"""Modelo de control de uso mensual para Vision OCR."""

from __future__ import annotations

from django.db import models


class VisionMonthlyUsage(models.Model):
    """Almacena el contador mensual de llamadas al servicio de Vision."""

    year = models.IntegerField()
    month = models.IntegerField()
    count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("year", "month"),)
        indexes = [models.Index(fields=["year", "month"], name="vision_month_idx")]
        verbose_name = "Uso mensual Vision"
        verbose_name_plural = "Usos mensuales Vision"

    def __str__(self) -> str:  # pragma: no cover - representacion basica
        return f"{self.year:04d}-{self.month:02d} => {self.count}"
