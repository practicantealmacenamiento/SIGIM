# app/migrations/0010_add_vision_monthly_usage.py
# Django 5.2 + SQL Server compatible
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("app", "0009_actor_uniq_actor_tipo_documento"),
    ]

    operations = [
        migrations.CreateModel(
            name="VisionMonthlyUsage",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("year", models.IntegerField()),
                ("month", models.IntegerField()),
                ("count", models.IntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                # Evita UniqueConstraint con condition/nulls_not_distinct/DEFERRABLE
                "unique_together": {("year", "month")},
                "indexes": [
                    models.Index(fields=["year", "month"], name="vision_month_idx"),
                ],
                "verbose_name": "Uso mensual Vision",
                "verbose_name_plural": "Usos mensuales Vision",
            },
        ),
    ]
