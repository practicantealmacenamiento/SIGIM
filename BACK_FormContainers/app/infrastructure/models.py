from django.db import models
from django.contrib.auth.models import User  # lo conservo por compat en otras tablas
from django.db.models import Q
import uuid


# -----------------------------
# Catálogo maestro de actores
# -----------------------------
class Actor(models.Model):
    class Tipo(models.TextChoices):
        PROVEEDOR = "PROVEEDOR", "Proveedor"
        TRANSPORTISTA = "TRANSPORTISTA", "Transportista"
        RECEPTOR = "RECEPTOR", "Usuario que recibe"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, db_index=True)
    nombre = models.CharField(max_length=255, db_index=True)
    documento = models.CharField(
        max_length=50, null=True, blank=True, db_index=True,
        help_text="RUC/NIT u otro identificador si aplica"
    )
    activo = models.BooleanField(default=True)
    meta = models.JSONField(default=dict, blank=True)  # campo libre para datos extra
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "actor"
        indexes = [
            models.Index(fields=["tipo", "nombre"]),
        ]
        # Nota: la constraint condicional requiere PostgreSQL
        constraints = [
            models.UniqueConstraint(
                fields=["tipo", "documento"],
                name="uniq_actor_tipo_documento",
                condition=Q(documento__isnull=False) & ~Q(documento="")
            )
        ]

    def __str__(self):
        base = f"{self.get_tipo_display()}: {self.nombre}"
        return f"{base} ({self.documento})" if self.documento else base


# -----------------------------
# Cuestionario
# -----------------------------
class Questionnaire(models.Model):
    """Configuración general del cuestionario."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    version = models.CharField(max_length=50)
    timezone = models.CharField(max_length=100)

    class Meta:
        db_table = "questionnaire"
        constraints = [
            models.UniqueConstraint(
                fields=["title", "version"], name="uniq_questionnaire_title_version"
            )
        ]

    def __str__(self):
        return f"{self.title} v{self.version}"


# -----------------------------
# Submission (llenado)
# -----------------------------
class Submission(models.Model):
    """Instancia de llenado de un cuestionario por un usuario/vehículo."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire = models.ForeignKey("Questionnaire", on_delete=models.CASCADE)
    regulador_id = models.UUIDField(null=True, blank=True, db_index=True)

    tipo_fase = models.CharField(
        max_length=20,
        choices=[("entrada", "Entrada"), ("salida", "Salida")],
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Datos clave ya existentes
    placa_vehiculo = models.CharField(max_length=20, blank=True, null=True, db_index=True)  # Visual + búsquedas
    nombre_conductor = models.CharField(max_length=100, blank=True, null=True)  # Visual

    # NUEVO: campos logísticos visibles/filtrables
    contenedor = models.CharField(max_length=40, blank=True, null=True, db_index=True)
    precinto = models.CharField(max_length=40, blank=True, null=True, db_index=True)

    # NUEVO: FKs a catálogos
    proveedor = models.ForeignKey(
        "Actor", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="submissions_proveedor",
        limit_choices_to={"tipo": Actor.Tipo.PROVEEDOR}
    )
    transportista = models.ForeignKey(
        "Actor", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="submissions_transportista",
        limit_choices_to={"tipo": Actor.Tipo.TRANSPORTISTA}
    )
    receptor = models.ForeignKey(
        "Actor", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="submissions_receptor",
        limit_choices_to={"tipo": Actor.Tipo.RECEPTOR}
    )

    finalizado = models.BooleanField(default=False)
    fecha_cierre = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "submission"
        indexes = [
            models.Index(fields=["finalizado", "tipo_fase"]),
            models.Index(fields=["tipo_fase", "fecha_cierre"]),
            # acelera consultas por regulador + estado/fase
            models.Index(fields=["regulador_id", "tipo_fase", "finalizado"]),
        ]
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.tipo_fase.upper()} - {self.questionnaire.title} - {self.id}"


# -----------------------------
# Preguntas
# -----------------------------
class Question(models.Model):
    """Pregunta individual dentro de un cuestionario."""
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

    # NUEVO: etiqueta semántica
    semantic_tag = models.CharField(
        max_length=20, choices=SEMANTIC_CHOICES, default="none", db_index=True
    )

    class Meta:
        db_table = "question"
        ordering = ["order"]
        unique_together = [("questionnaire", "order")]  # evita duplicar el orden dentro del cuestionario

    def __str__(self):
        return f"Pregunta {self.order}: {self.text[:50]}..."


# -----------------------------
# Opciones para preguntas choice
# -----------------------------
class Choice(models.Model):
    """Opción de respuesta para preguntas de tipo selección."""
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


# -----------------------------
# Respuestas
# -----------------------------
class Answer(models.Model):
    """
    Respuesta a una pregunta (esquema original).

    Mantiene compatibilidad con migraciones iniciales:
      - answer_file (FileField)
      - timestamp (auto_now_add)
      - user (FK a AUTH_USER)
      - ocr_meta y meta (JSON)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey("Submission", on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey("Question", on_delete=models.CASCADE)

    # contenido
    answer_text = models.TextField(null=True, blank=True)
    answer_choice = models.ForeignKey("Choice", null=True, blank=True, on_delete=models.SET_NULL)
    answer_file = models.FileField(upload_to="uploads/%Y/%m/%d/", null=True, blank=True)

    # metadatos libres
    ocr_meta = models.JSONField(default=dict, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    # tiempos
    timestamp = models.DateTimeField(auto_now_add=True)

    # auditoría opcional
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

    # Eliminar archivo físico si se borra la respuesta
    def delete(self, *args, **kwargs):
        if self.answer_file:
            self.answer_file.delete(save=False)
        super().delete(*args, **kwargs)

