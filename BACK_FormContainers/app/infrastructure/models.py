# -*- coding: utf-8 -*-
"""
Modelos de infraestructura (Django ORM).

Objetivo:
- Representar tablas y relaciones persistentes sin lógica de negocio.
- Mantener compatibilidad con migraciones existentes (nombres de campos, tipos y
  opciones de `Meta`), sin introducir cambios de esquema.

Convenciones:
- No mover reglas de negocio aquí; limitarse a detalles de persistencia.
- `__str__` devuelve una representación legible para el admin y logs.
- Índices y constraints documentados para facilitar mantenimiento.
"""

from django.db import models
from django.contrib.auth.models import User  # Compat con migraciones/tablas previas
from django.db.models import Q
import uuid


# ==============================================================================
#   Catálogo maestro de actores
# ==============================================================================

class Actor(models.Model):
    """
    Catálogo de actores operativos (proveedor, transportista, receptor).

    Campos:
        tipo: clasifica el actor (TextChoices).
        nombre: texto indexado para búsquedas.
        documento: identificador opcional (RUC/NIT/otro), con unicidad por tipo.
        activo: habilita/deshabilita el actor en la UI.
        meta: JSON libre para datos adicionales.
        creado: timestamp de creación.
    """

    class Tipo(models.TextChoices):
        PROVEEDOR = "PROVEEDOR", "Proveedor"
        TRANSPORTISTA = "TRANSPORTISTA", "Transportista"
        RECEPTOR = "RECEPTOR", "Usuario que recibe"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, db_index=True)
    nombre = models.CharField(max_length=255, db_index=True)
    documento = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text="RUC/NIT u otro identificador si aplica",
    )
    activo = models.BooleanField(default=True)
    meta = models.JSONField(default=dict, blank=True)  # Campo libre para datos extra
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "actor"
        indexes = [
            models.Index(fields=["tipo", "nombre"]),
        ]
        # Unicidad condicional por (tipo, documento) cuando documento no es vacío.
        # Requiere PostgreSQL.
        constraints = [
            models.UniqueConstraint(
                fields=["tipo", "documento"],
                name="uniq_actor_tipo_documento",
                condition=Q(documento__isnull=False) & ~Q(documento=""),
            )
        ]

    def __str__(self):
        base = f"{self.get_tipo_display()}: {self.nombre}"
        return f"{base} ({self.documento})" if self.documento else base


# ==============================================================================
#   Cuestionario
# ==============================================================================

class Questionnaire(models.Model):
    """
    Configuración general del cuestionario (catálogo de versiones).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    version = models.CharField(max_length=50)
    timezone = models.CharField(max_length=100)

    class Meta:
        db_table = "questionnaire"
        constraints = [
            models.UniqueConstraint(
                fields=["title", "version"],
                name="uniq_questionnaire_title_version",
            )
        ]

    def __str__(self):
        return f"{self.title} v{self.version}"


# ==============================================================================
#   Submission (llenado)
# ==============================================================================

class Submission(models.Model):
    """
    Instancia de llenado de un cuestionario por un usuario/vehículo.

    Notas:
        - `placa_vehiculo`, `contenedor`, `precinto` se usan para filtros y vistas.
        - FKs hacia `Actor` se limitan por tipo para coherencia.
        - `finalizado` + `fecha_cierre` permiten listar historiales por fase/estado.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire = models.ForeignKey("Questionnaire", on_delete=models.CASCADE)
    regulador_id = models.UUIDField(null=True, blank=True, db_index=True)

    tipo_fase = models.CharField(
        max_length=20,
        choices=[("entrada", "Entrada"), ("salida", "Salida")],
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Datos clave ya existentes
    placa_vehiculo = models.CharField(
        max_length=20, blank=True, null=True, db_index=True
    )  # Visual + búsquedas
    nombre_conductor = models.CharField(max_length=100, blank=True, null=True)  # Visual

    # Logística visibles/filtrables
    contenedor = models.CharField(max_length=40, blank=True, null=True, db_index=True)
    precinto = models.CharField(max_length=40, blank=True, null=True, db_index=True)

    # FKs a catálogos
    proveedor = models.ForeignKey(
        "Actor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissions_proveedor",
        limit_choices_to={"tipo": Actor.Tipo.PROVEEDOR},
    )
    transportista = models.ForeignKey(
        "Actor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissions_transportista",
        limit_choices_to={"tipo": Actor.Tipo.TRANSPORTISTA},
    )
    receptor = models.ForeignKey(
        "Actor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissions_receptor",
        limit_choices_to={"tipo": Actor.Tipo.RECEPTOR},
    )

    finalizado = models.BooleanField(default=False)
    fecha_cierre = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "submission"
        indexes = [
            models.Index(fields=["finalizado", "tipo_fase"]),
            models.Index(fields=["tipo_fase", "fecha_cierre"]),
            # Acelera consultas por regulador + estado/fase
            models.Index(fields=["regulador_id", "tipo_fase", "finalizado"]),
        ]
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.tipo_fase.upper()} - {self.questionnaire.title} - {self.id}"


# ==============================================================================
#   Preguntas
# ==============================================================================

class Question(models.Model):
    """
    Pregunta individual dentro de un cuestionario.

    `semantic_tag` enlaza con reglas de negocio sin depender del texto visible.
    """
    TYPE_CHOICES = [
        ("text", "Texto"),
        ("choice", "Selección"),
        ("number", "Número"),
        ("date", "Fecha"),
        ("file", "Archivo"),
    ]

    # Etiqueta semántica para enlazar con lógica de negocio (sin depender del texto)
    SEMANTIC_CHOICES = [
        ("none", "Ninguna"),
        ("placa", "Placa vehicular"),
        ("proveedor", "Proveedor"),
        ("transportista", "Transportista"),
        ("receptor", "Usuario que recibe"),
        ("contenedor", "Contenedor"),
        ("precinto", "Precinto"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire = models.ForeignKey(
        "Questionnaire",
        related_name="questions",
        on_delete=models.CASCADE,
    )
    text = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(db_index=True)

    file_mode = models.CharField(
        max_length=20,
        choices=[
            ("image_only", "Solo imagen"),
            ("image_ocr", "Imagen + OCR"),
            ("ocr_only", "Solo OCR (requiere texto extraído)"),
        ],
        default="image_only",
        blank=True,
    )

    # Etiqueta semántica
    semantic_tag = models.CharField(
        max_length=20, choices=SEMANTIC_CHOICES, default="none", db_index=True
    )

    class Meta:
        db_table = "question"
        ordering = ["order"]
        # Evita duplicar el orden dentro del mismo cuestionario
        unique_together = [("questionnaire", "order")]

    def __str__(self):
        return f"Pregunta {self.order}: {self.text[:50]}..."


# ==============================================================================
#   Opciones para preguntas choice
# ==============================================================================

class Choice(models.Model):
    """
    Opción de respuesta para preguntas de tipo selección.

    `branch_to` permite ramificación condicional hacia otra pregunta.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        "Question",
        related_name="choices",
        on_delete=models.CASCADE,
    )
    text = models.CharField(max_length=200)
    branch_to = models.ForeignKey(
        "Question",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Pregunta destino para ramificación",
    )

    class Meta:
        db_table = "choice"

    def __str__(self):
        return self.text


# ==============================================================================
#   Respuestas
# ==============================================================================

class Answer(models.Model):
    """
    Respuesta a una pregunta (esquema original compatible).

    Compatibilidad con migraciones iniciales:
        - `answer_file` (FileField con `upload_to`).
        - `timestamp` (auto_now_add).
        - `user` (FK a AUTH_USER).
        - `ocr_meta` y `meta` como JSON libres.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(
        "Submission", on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey("Question", on_delete=models.CASCADE)

    # Contenido
    answer_text = models.TextField(null=True, blank=True)
    answer_choice = models.ForeignKey(
        "Choice", null=True, blank=True, on_delete=models.SET_NULL
    )
    answer_file = models.FileField(upload_to="uploads/%Y/%m/%d/", null=True, blank=True)

    # Metadatos libres
    ocr_meta = models.JSONField(default=dict, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    # Tiempos
    timestamp = models.DateTimeField(auto_now_add=True)

    # Auditoría opcional
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "answer"
        ordering = ["timestamp"]
        indexes = [
            models.Index(fields=["submission", "question"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"Respuesta {self.id} a pregunta {self.question_id}"

    # Eliminación de archivo físico si se borra la respuesta
    def delete(self, *args, **kwargs):
        """
        Override de `delete` para asegurar que, si existe, el archivo asociado
        se elimine del storage antes de borrar la fila.
        """
        if self.answer_file:
            self.answer_file.delete(save=False)
        super().delete(*args, **kwargs)
