# -*- coding: utf-8 -*-
"""
Comandos (DTOs inmutables) para la capa de aplicación.

Estos objetos encapsulan parámetros de entrada para casos de uso y servicios,
sin introducir dependencias de infraestructura ni lógica de negocio.

Convenciones:
- Los comandos son `@dataclass(frozen=True)` para favorecer inmutabilidad.
- `UNSET` diferencia entre "no enviado" y `None` (limpieza explícita).
- No alteres firmas ni nombres: otros módulos dependen de estos contratos.
"""

from __future__ import annotations

# ── Stdlib ─────────────────────────────────────────────────────────────────────
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID

# ── API pública ────────────────────────────────────────────────────────────────
__all__ = [
    "UNSET",
    "CreateAnswerCommand",
    "UpdateAnswerCommand",
    "SaveAndAdvanceCommand",
    "SaveAndAdvanceResult",
]

# Sentinel para diferenciar "no enviado" de "None"
UNSET = object()


# ==============================================================================
#   Commands básicos
# ==============================================================================

@dataclass(frozen=True)
class CreateAnswerCommand:
    """
    Crea una `Answer`.

    Compatibilidad:
      - `user_id` se permite en el comando (auditoría) pero NO forma parte de la entidad dominio.
      - `ocr_meta` quedó obsoleto a nivel de dominio; si llega, la aplicación debe ignorarlo.

    Aclaraciones:
      - `answer_file` es un objeto similar a `UploadedFile` (Django File-like).
      - `table_id`/`row_index` permiten crear una fila tabular (Opción B).
    """
    submission_id: UUID
    question_id: UUID
    user_id: Optional[UUID] = None  # sólo para auditoría/traza, NO en dominio

    # Contenido de la respuesta
    answer_text: Optional[str] = None
    answer_choice_id: Optional[UUID] = None
    answer_file: Optional[Any] = None  # UploadedFile/Django File-like

    # Metadatos abiertos
    meta: Optional[Dict[str, Any]] = None

    # Tabular (Opción B)
    table_id: Optional[str] = None
    row_index: Optional[int] = None

    # Compatibilidad (obsoleto en dominio)
    ocr_meta: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class UpdateAnswerCommand:
    """
    Actualiza parcialmente una `Answer` existente.

    Semántica de campos:
      - `UNSET` → no tocar.
      - `None`  → limpiar/poner a nulo.
      - valor   → asignar.

    Nota:
      - `table_id` y `row_index` no deberían cambiarse tras la creación.
      - Si se reemplaza `answer_file`, `delete_old_file_on_replace=True` indica
        que la infraestructura debe eliminar el archivo anterior.
    """
    id: UUID

    answer_text: Any = field(default=UNSET)
    answer_choice_id: Any = field(default=UNSET)
    answer_file: Any = field(default=UNSET)  # UploadedFile | None | UNSET
    meta: Any = field(default=UNSET)

    # Si reemplazas archivo, ¿eliminar el anterior del storage?
    delete_old_file_on_replace: bool = True

    # Compatibilidad (ignorar en aplicación/infra)
    ocr_meta: Any = field(default=UNSET)


# ==============================================================================
#   Guardar y Avanzar
# ==============================================================================

@dataclass(frozen=True)
class SaveAndAdvanceCommand:
    """
    Comando principal del flujo de cuestionario.

    Debe venir al menos uno:
      - `answer_text`, `answer_choice_id`, `uploads` (archivo), `meta` no vacío,
      - o `proveedores` (caso especial: se mapeará a filas tabulares).

    Tabular:
      - Si se envía `table_id` + `row_index`, se hace upsert de ESA fila.
      - Si se envía `proveedores`, la aplicación creará/actualizará múltiples filas con
        `table_id="proveedor"` (por convención) o el recibido en `table_id` si viene.
    """
    submission_id: UUID
    question_id: UUID
    user_id: Optional[UUID] = None  # sólo auditoría

    # Respuesta clásica
    answer_text: Optional[str] = None
    answer_choice_id: Optional[UUID] = None
    uploads: List[Any] = field(default_factory=list)  # soporta 0..n archivos
    actor_id: Optional[UUID] = None

    # Metadatos abiertos (para la fila o para la respuesta simple)
    meta: Optional[Dict[str, Any]] = None

    # Tabular (para operar una sola fila)
    table_id: Optional[str] = None
    row_index: Optional[int] = None

    # PROVEEDOR: lista completa (nombre, estibas, unidades, unidad, recipientes, orden_compra, ...)
    # Si viene poblado, se ignorará answer_text/choice y se hará operación en bloque por filas.
    proveedores: Optional[List[Dict[str, Any]]] = None

    # Estrategia de navegación
    force_truncate_future: bool = True  # truncar respuestas de preguntas futuras


@dataclass(frozen=True)
class SaveAndAdvanceResult:
    """
    Resultado del caso de uso Guardar y Avanzar.

    Attributes:
        saved_answer: Entidad `Answer` o `List[Answer]` si hubo operación en bloque.
        next_question_id: ID de la siguiente pregunta (o None si finalizó).
        is_finished: True si no hay más preguntas pendientes.
        derived_updates: Campos derivados/efectos secundarios (placa, contenedor, etc.).
        warnings: Mensajes no fatales generados durante el flujo.
    """
    saved_answer: Any  # Answer | List[Answer] según el caso
    next_question_id: Optional[UUID]
    is_finished: bool
    derived_updates: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)
