from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict
from uuid import UUID

# Sentinel para diferenciar "no enviado" de "None"
UNSET = object()


# =========================
#   Commands básicos
# =========================
@dataclass(frozen=True)
class CreateAnswerCommand:
    """
    Crea una Answer.

    Compatibilidad:
    - `user_id` se permite en el comando (auditoría) pero NO forma parte de la entidad dominio.
    - `ocr_meta` quedó obsoleto en dominio: si llega, la capa de aplicación debe ignorarlo.
    """
    submission_id: UUID
    question_id: UUID
    user_id: Optional[UUID] = None  # sólo para auditoría/traza, NO en dominio

    # Contenido
    answer_text: Optional[str] = None
    answer_choice_id: Optional[UUID] = None
    answer_file: Optional[Any] = None  # UploadedFile/Django File-like

    # Metadatos abiertos
    meta: Optional[Dict[str, Any]] = None

    # Tabular (Opción B)
    table_id: Optional[str] = None
    row_index: Optional[int] = None

    # ⚠️ Dejado por compat (obsoleto en dominio)
    ocr_meta: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class UpdateAnswerCommand:
    """
    Actualiza parcialmente una Answer existente.
    UNSET → no tocar; None → limpiar; valor → asignar.

    Nota: `table_id` y `row_index` no deberían cambiarse tras la creación.
    """
    id: UUID

    answer_text: Any = field(default=UNSET)
    answer_choice_id: Any = field(default=UNSET)
    answer_file: Any = field(default=UNSET)  # UploadedFile | None | UNSET
    meta: Any = field(default=UNSET)

    # Si reemplazas archivo, ¿eliminar el anterior del storage?
    delete_old_file_on_replace: bool = True

    # ⚠️ Compat (ignorar en aplicación/infra)
    ocr_meta: Any = field(default=UNSET)


# =========================
#   Guardar y Avanzar
# =========================
@dataclass(frozen=True)
class SaveAndAdvanceCommand:
    """
    Command principal del flujo de cuestionario.

    Debe venir al menos uno:
      - answer_text, answer_choice_id, uploads (archivo), meta no vacío,
      - ó `proveedores` (caso especial: se mapeará a filas tabulares).

    Tabular:
      - Si se envía `table_id` + `row_index`, se hace upsert de ESA fila.
      - Si se envía `proveedores`, la aplicación creará/actualizará múltiples filas con
        table_id="proveedor" (por convención) o el recibido en `table_id` si viene.
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
    """
    saved_answer: Any  # entidad de dominio Answer o lista de Answers cuando hay operación en bloque
    next_question_id: Optional[UUID]
    is_finished: bool
    derived_updates: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)
