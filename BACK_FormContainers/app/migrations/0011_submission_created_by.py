from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("app", "0010_add_vision_monthly_usage"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="submissions_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

