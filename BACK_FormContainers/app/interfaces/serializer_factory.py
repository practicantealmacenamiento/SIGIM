"""
Factory para crear serializers apropiados según el contexto (interfaces layer).

Objetivos:
- Facilitar la migración gradual desde serializers basados en modelos (infra)
  hacia serializers basados en ENTIDADES de dominio (interfaces/entity_serializers.py).
- Elegir automáticamente el serializer correcto según:
    * tipo declarado (clave del mapping)
    * el objeto recibido (entidad de dominio vs modelo Django)
    * preferencia (prefer_entity=True por defecto)
- Soporta instancias únicas y colecciones (list/tuple/set/QuerySet).

IMPORTANTE:
- Este módulo pertenece a la CAPA DE INTERFACES, ya que orquesta serializers DRF
  (presentación HTTP). No se usa en dominio ni en aplicación.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type, Sequence

from rest_framework import serializers

# —— Serializers basados en ENTIDADES (interfaces) ——
from app.interfaces.entity_serializers import (
    DomainSubmissionReadSerializer,
    DomainAnswerReadSerializer,
    DomainQuestionReadSerializer,
    DomainQuestionnaireReadSerializer,
    SaveAndAdvanceEntityResponseSerializer,
    VerificationEntityResponseSerializer,
    QuestionnaireListEntitySerializer,
    EntityBasedActorSerializer,
)

# —— Serializers legacy basados en MODELOS (infraestructura) ——
from app.infrastructure.serializers import (
    SubmissionModelSerializer,
    AnswerReadSerializer,
    QuestionModelSerializer,
    QuestionnaireModelSerializer,
    SaveAndAdvanceResponseSerializer,
    VerificationResponseSerializer,
    QuestionnaireListItemSerializer,
    ActorModelSerializer,
)


class SerializerFactory:
    """
    Factory para crear serializers apropiados según el tipo de dato y contexto.
    Permite migración gradual a serializers basados en ENTIDADES de dominio.
    """

    # Mapeo de claves lógicas -> clases de serializers (modelo vs entidad)
    SERIALIZER_MAPPING: Dict[str, Dict[str, Type[serializers.Serializer]]] = {
        # Lecturas
        "submission_read": {"model": SubmissionModelSerializer, "entity": DomainSubmissionReadSerializer},
        "answer_read": {"model": AnswerReadSerializer, "entity": DomainAnswerReadSerializer},
        "question_read": {"model": QuestionModelSerializer, "entity": DomainQuestionReadSerializer},
        "questionnaire_read": {"model": QuestionnaireModelSerializer, "entity": DomainQuestionnaireReadSerializer},
        "questionnaire_list": {"model": QuestionnaireListItemSerializer, "entity": QuestionnaireListEntitySerializer},
        "actor": {"model": ActorModelSerializer, "entity": EntityBasedActorSerializer},
        # Respuestas de casos de uso
        "save_and_advance_response": {"model": SaveAndAdvanceResponseSerializer, "entity": SaveAndAdvanceEntityResponseSerializer},
        "verification_response": {"model": VerificationResponseSerializer, "entity": VerificationEntityResponseSerializer},
    }

    # ----------------------------
    # API principal (single/many)
    # ----------------------------
    @classmethod
    def get_serializer(
        cls,
        serializer_type: str,
        instance: Any = None,
        *,
        context: Optional[Dict[str, Any]] = None,
        many: bool = False,
        prefer_entity: bool = True,
    ) -> serializers.Serializer:
        """
        Retorna una INSTANCIA de serializer adecuada al tipo y a la naturaleza del objeto.

        Args:
            serializer_type: clave definida en SERIALIZER_MAPPING
            instance: objeto(s) a serializar (entidad de dominio o modelo Django; o lista/QuerySet)
            context: contexto DRF
            many: True si instance es secuencia
            prefer_entity: preferir serializers de ENTIDAD cuando sea posible

        Returns:
            Serializer inicializado (listo para .data).
        """
        serializer_class = cls._select_serializer_class(serializer_type, instance, many=many, prefer_entity=prefer_entity)
        return serializer_class(instance, many=many, context=context or {})

    @classmethod
    def get_serializer_class(
        cls,
        serializer_type: str,
        *,
        prefer_entity: bool = True,
    ) -> Type[serializers.Serializer]:
        """
        Obtiene la CLASE de serializer (no inicializa).
        Útil si quieres construirlo manualmente luego.

        Nota: Esta versión ignora el tipo de instancia y retorna la preferida.
        """
        mapping = cls._get_mapping(serializer_type)
        return mapping["entity"] if prefer_entity else mapping["model"]

    @classmethod
    def serialize_data(
        cls,
        serializer_type: str,
        data: Any,
        *,
        context: Optional[Dict[str, Any]] = None,
        many: bool = False,
        prefer_entity: bool = True,
    ):
        """
        Serializa datos (single o many) devolviendo dict/list nativo listo para respuesta.

        Args:
            serializer_type: clave definida en SERIALIZER_MAPPING
            data: entidad/modelo o secuencia de éstas
            context: contexto DRF (p. ej. caches de preguntas/opciones para enriquecidos)
            many: True si data es colección
            prefer_entity: preferir serializers de ENTIDAD cuando sea posible
        """
        serializer = cls.get_serializer(
            serializer_type=serializer_type,
            instance=data,
            context=context,
            many=many,
            prefer_entity=prefer_entity,
        )
        return serializer.data

    # ----------------------------
    # Internos: selección/clasificación
    # ----------------------------
    @classmethod
    def _get_mapping(cls, serializer_type: str) -> Dict[str, Type[serializers.Serializer]]:
        try:
            return cls.SERIALIZER_MAPPING[serializer_type]
        except KeyError as e:
            raise ValueError(f"Tipo de serializer no soportado: {serializer_type}") from e

    @staticmethod
    def _is_django_model(obj: Any) -> bool:
        """
        Heurística ligera: modelos Django tienen _state.db.
        Evita imports pesados o acoplar a infra.
        """
        return hasattr(obj, "_state") and hasattr(getattr(obj, "_state"), "db")

    @staticmethod
    def _is_domain_entity(obj: Any) -> bool:
        """Entidades del dominio basadas en dataclasses tienen __dataclass_fields__."""
        return hasattr(obj, "__dataclass_fields__")

    @classmethod
    def _peek_sample(cls, instance: Any, many: bool) -> Any:
        """
        Devuelve un elemento representativo cuando 'instance' es una colección.
        Soporta list/tuple/set/QuerySet. Si está vacío, retorna None.
        """
        if not many:
            return instance

        if instance is None:
            return None

        # QuerySet-friendly y colecciones comunes
        try:
            iterator = iter(instance)
        except TypeError:
            return None

        try:
            return next(iterator)
        except StopIteration:
            return None

    @classmethod
    def _detect_nature(cls, instance: Any, many: bool) -> str:
        """
        Determina 'entity' | 'model' | 'unknown' a partir del objeto (o sample si many=True).
        """
        sample = cls._peek_sample(instance, many=many)
        if sample is None:
            return "unknown"
        if cls._is_domain_entity(sample):
            return "entity"
        if cls._is_django_model(sample):
            return "model"
        return "unknown"

    @classmethod
    def _select_serializer_class(
        cls,
        serializer_type: str,
        instance: Any,
        *,
        many: bool,
        prefer_entity: bool,
    ) -> Type[serializers.Serializer]:
        """
        Selecciona la CLASE de serializer más apropiada considerando:
        - prefer_entity
        - naturaleza detectada de la instancia (entity/model)
        - fallback seguro si es 'unknown'
        """
        mapping = cls._get_mapping(serializer_type)
        nature = cls._detect_nature(instance, many=many)

        if nature == "entity":
            return mapping["entity"]
        if nature == "model":
            return mapping["model"]

        # Desconocido (None/colección vacía/tipos mixtos): honrar preferencia
        return mapping["entity"] if prefer_entity else mapping["model"]


# =============================================================================
# Factory específica de RESPUESTAS para endpoints
# =============================================================================

class ResponseSerializerFactory:
    """
    Factory de atajos para construir respuestas consistentes en vistas HTTP.
    """

    @classmethod
    def create_submission_response(
        cls,
        submission: Any,
        *,
        context: Optional[Dict[str, Any]] = None,
        include_answers: bool = False,  # placeholder: contexto enriquecido si hace falta
        prefer_entity: bool = True,
    ):
        # Si deseas enriquecer 'answers_data' en context, hazlo aquí antes.
        return SerializerFactory.serialize_data(
            serializer_type="submission_read",
            data=submission,
            context=context,
            many=False,
            prefer_entity=prefer_entity,
        )

    @classmethod
    def create_question_response(
        cls,
        question: Any,
        *,
        context: Optional[Dict[str, Any]] = None,
        prefer_entity: bool = True,
    ):
        return SerializerFactory.serialize_data(
            serializer_type="question_read",
            data=question,
            context=context,
            many=False,
            prefer_entity=prefer_entity,
        )

    @classmethod
    def create_save_and_advance_response(
        cls,
        result: Any,
        *,
        context: Optional[Dict[str, Any]] = None,
        prefer_entity: bool = True,
    ):
        return SerializerFactory.serialize_data(
            serializer_type="save_and_advance_response",
            data=result,
            context=context,
            many=False,
            prefer_entity=prefer_entity,
        )

    @classmethod
    def create_verification_response(
        cls,
        result: Any,
        *,
        context: Optional[Dict[str, Any]] = None,
        prefer_entity: bool = True,
    ):
        return SerializerFactory.serialize_data(
            serializer_type="verification_response",
            data=result,
            context=context,
            many=False,
            prefer_entity=prefer_entity,
        )

    @classmethod
    def create_list_response(
        cls,
        items: Any,
        *,
        serializer_type: str,
        context: Optional[Dict[str, Any]] = None,
        pagination_data: Optional[Dict[str, Any]] = None,
        prefer_entity: bool = True,
    ):
        serialized_items = SerializerFactory.serialize_data(
            serializer_type=serializer_type,
            data=items,
            context=context,
            many=True,
            prefer_entity=prefer_entity,
        )

        if pagination_data is not None:
            return {
                "results": serialized_items,
                "count": pagination_data.get("count", len(serialized_items)),
                "next": pagination_data.get("next"),
                "previous": pagination_data.get("previous"),
            }

        return serialized_items


# =============================================================================
# Funciones de conveniencia (atajos)
# =============================================================================

def serialize_submission(submission, context=None, include_answers: bool = False, prefer_entity: bool = True):
    return ResponseSerializerFactory.create_submission_response(
        submission=submission,
        context=context,
        include_answers=include_answers,
        prefer_entity=prefer_entity,
    )


def serialize_question(question, context=None, prefer_entity: bool = True):
    return ResponseSerializerFactory.create_question_response(
        question=question, context=context, prefer_entity=prefer_entity
    )


def serialize_save_and_advance_result(result, context=None, prefer_entity: bool = True):
    return ResponseSerializerFactory.create_save_and_advance_response(
        result=result, context=context, prefer_entity=prefer_entity
    )


def serialize_verification_result(result, context=None, prefer_entity: bool = True):
    return ResponseSerializerFactory.create_verification_response(
        result=result, context=context, prefer_entity=prefer_entity
    )
