# app/management/commands/report_vision_usage.py
from django.core.management.base import BaseCommand
from app.infrastructure.usage_limits import VisionMonthlyUsage

class Command(BaseCommand):
    help = "Muestra el uso mensual de Cloud Vision OCR"

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int)
        parser.add_argument("--month", type=int)

    def handle(self, *args, **opts):
        qs = VisionMonthlyUsage.objects.all().order_by("-year", "-month")
        if opts.get("year"):
            qs = qs.filter(year=opts["year"])
        if opts.get("month"):
            qs = qs.filter(month=opts["month"])
        if not qs.exists():
            self.stdout.write("Sin datos.")
            return
        for r in qs:
            self.stdout.write(f"{r.year:04d}-{r.month:02d}\t{r.count}\t(updated {r.updated_at})")
