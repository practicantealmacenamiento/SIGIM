from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q

class Migration(migrations.Migration):

    dependencies = [
        ('app', '0005_alter_submission_options_alter_question_file_mode_and_more'),
    ]

    operations = [
        # --- Catálogo: Actor ---
        migrations.CreateModel(
            name='Actor',
            fields=[
                ('id', models.UUIDField(primary_key=True, editable=False, serialize=False)),
                ('tipo', models.CharField(choices=[('PROVEEDOR', 'Proveedor'), ('TRANSPORTISTA', 'Transportista'), ('RECEPTOR', 'Usuario que recibe')], db_index=True, max_length=20)),
                ('nombre', models.CharField(db_index=True, max_length=255)),
                ('documento', models.CharField(blank=True, db_index=True, max_length=50, null=True)),
                ('activo', models.BooleanField(default=True)),
                ('meta', models.JSONField(blank=True, default=dict)),
                ('creado', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'actor'},
        ),
        migrations.AddIndex(
            model_name='actor',
            index=models.Index(fields=['tipo', 'nombre'], name='actor_tipo_nombre_idx'),
        ),
        migrations.AddConstraint(
            model_name='actor',
            constraint=models.UniqueConstraint(
                fields=('tipo', 'documento'),
                name='uniq_actor_tipo_documento',
                condition=Q(('documento__isnull', False)) & ~Q(('documento', ''))
            ),
        ),

        # --- Questionnaire: unicidad (title, version) ---
        migrations.AddConstraint(
            model_name='questionnaire',
            constraint=models.UniqueConstraint(
                fields=('title', 'version'),
                name='uniq_questionnaire_title_version'
            ),
        ),

        # --- Submission: nuevos campos y FKs ---
        migrations.AddField(
            model_name='submission',
            name='contenedor',
            field=models.CharField(blank=True, null=True, db_index=True, max_length=40),
        ),
        migrations.AddField(
            model_name='submission',
            name='precinto',
            field=models.CharField(blank=True, null=True, db_index=True, max_length=40),
        ),
        migrations.AddField(
            model_name='submission',
            name='proveedor',
            field=models.ForeignKey(
                blank=True, null=True, to='app.actor',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='submissions_proveedor'
            ),
        ),
        migrations.AddField(
            model_name='submission',
            name='transportista',
            field=models.ForeignKey(
                blank=True, null=True, to='app.actor',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='submissions_transportista'
            ),
        ),
        migrations.AddField(
            model_name='submission',
            name='receptor',
            field=models.ForeignKey(
                blank=True, null=True, to='app.actor',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='submissions_receptor'
            ),
        ),
        migrations.AddIndex(
            model_name='submission',
            index=models.Index(fields=['regulador_id', 'tipo_fase', 'finalizado'], name='sub_reg_fase_fin_idx'),
        ),

        # --- Question: semantic_tag ---
        migrations.AddField(
            model_name='question',
            name='semantic_tag',
            field=models.CharField(
                choices=[
                    ('none', 'Ninguna'),
                    ('placa', 'Placa vehicular'),
                    ('proveedor', 'Proveedor'),
                    ('transportista', 'Transportista'),
                    ('receptor', 'Usuario que recibe'),
                    ('contenedor', 'Contenedor'),
                    ('precinto', 'Precinto'),
                ],
                default='none', db_index=True, max_length=20
            ),
        ),

        # --- Answer: metadatos ---
        migrations.AddField(
            model_name='answer',
            name='ocr_meta',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='answer',
            name='meta',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]

