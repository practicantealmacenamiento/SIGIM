"""
Factory para crear serializers apropiados según el contexto.
Facilita la migración gradual de ModelSerializer a serializers basados en entidades.
"""
from __future__ import annotations

from typing import Type, Any, Dict, Optional
from rest_framework import serializers

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
    Factory para crear serializers apropiados según el tipo de objeto y contexto.
    Permite migración gradual de serializers basados en modelos a serializers basados en entidades.
    """
    
    # Mapeo de serializers legacy (modelos) a serializers de entidades
    SERIALIZER_MAPPING = {
        'submission_read': {
            'model': SubmissionModelSerializer,
            'entity': DomainSubmissionReadSerializer,
        },
        'answer_read': {
            'model': AnswerReadSerializer,
            'entity': DomainAnswerReadSerializer,
        },
        'question_read': {
            'model': QuestionModelSerializer,
            'entity': DomainQuestionReadSerializer,
        },
        'questionnaire_read': {
            'model': QuestionnaireModelSerializer,
            'entity': DomainQuestionnaireReadSerializer,
        },
        'save_and_advance_response': {
            'model': SaveAndAdvanceResponseSerializer,
            'entity': SaveAndAdvanceEntityResponseSerializer,
        },
        'verification_response': {
            'model': VerificationResponseSerializer,
            'entity': VerificationEntityResponseSerializer,
        },
        'questionnaire_list': {
            'model': QuestionnaireListItemSerializer,
            'entity': QuestionnaireListEntitySerializer,
        },
        'actor': {
            'model': ActorModelSerializer,
            'entity': EntityBasedActorSerializer,
        },
    }

    @classmethod
    def get_serializer(
        cls,
        serializer_type: str,
        instance: Any,
        context: Optional[Dict[str, Any]] = None,
        prefer_entity: bool = True
    ) -> serializers.Serializer:
        """
        Retorna el serializer apropiado según el tipo de objeto.
        
        Args:
            serializer_type: Tipo de serializer ('submission_read', 'answer_read', etc.)
            instance: Objeto a serializar
            context: Contexto para el serializer
            prefer_entity: Si True, prefiere serializers de entidades cuando sea posible
        
        Returns:
            Instancia del serializer apropiado
        """
        if serializer_type not in cls.SERIALIZER_MAPPING:
            raise ValueError(f"Tipo de serializer no soportado: {serializer_type}")
        
        mapping = cls.SERIALIZER_MAPPING[serializer_type]
        
        # Determinar qué tipo de serializer usar
        if prefer_entity and cls._is_domain_entity(instance):
            serializer_class = mapping['entity']
        elif cls._is_django_model(instance):
            serializer_class = mapping['model']
        else:
            # Default: usar serializer de entidades si prefer_entity=True, sino modelo
            serializer_class = mapping['entity'] if prefer_entity else mapping['model']
        
        return serializer_class(instance, context=context or {})

    @classmethod
    def get_serializer_class(
        cls,
        serializer_type: str,
        prefer_entity: bool = True
    ) -> Type[serializers.Serializer]:
        """
        Retorna la clase del serializer apropiado.
        
        Args:
            serializer_type: Tipo de serializer
            prefer_entity: Si True, prefiere serializers de entidades
        
        Returns:
            Clase del serializer
        """
        if serializer_type not in cls.SERIALIZER_MAPPING:
            raise ValueError(f"Tipo de serializer no soportado: {serializer_type}")
        
        mapping = cls.SERIALIZER_MAPPING[serializer_type]
        return mapping['entity'] if prefer_entity else mapping['model']

    @classmethod
    def serialize_data(
        cls,
        serializer_type: str,
        data: Any,
        context: Optional[Dict[str, Any]] = None,
        many: bool = False,
        prefer_entity: bool = True
    ) -> Dict[str, Any]:
        """
        Serializa datos usando el serializer apropiado.
        
        Args:
            serializer_type: Tipo de serializer
            data: Datos a serializar
            context: Contexto para el serializer
            many: Si True, serializa múltiples objetos
            prefer_entity: Si True, prefiere serializers de entidades
        
        Returns:
            Datos serializados
        """
        serializer_class = cls.get_serializer_class(serializer_type, prefer_entity)
        serializer = serializer_class(data, many=many, context=context or {})
        return serializer.data

    @staticmethod
    def _is_django_model(obj) -> bool:
        """Verifica si el objeto es un modelo Django."""
        return hasattr(obj, '_state') and hasattr(obj._state, 'db')
    
    @staticmethod
    def _is_domain_entity(obj) -> bool:
        """Verifica si el objeto es una entidad de dominio (dataclass)."""
        return hasattr(obj, '__dataclass_fields__')


class ResponseSerializerFactory:
    """
    Factory específico para serializers de respuesta de API.
    Facilita la creación de respuestas consistentes.
    """
    
    @classmethod
    def create_submission_response(
        cls,
        submission,
        context: Optional[Dict[str, Any]] = None,
        include_answers: bool = False
    ) -> Dict[str, Any]:
        """Crea respuesta para submission."""
        serializer_type = 'submission_read'
        
        if include_answers:
            # Enriquecer contexto con respuestas si están disponibles
            if context is None:
                context = {}
            # Aquí se podría agregar lógica para cargar respuestas
        
        return SerializerFactory.serialize_data(
            serializer_type=serializer_type,
            data=submission,
            context=context
        )

    @classmethod
    def create_question_response(
        cls,
        question,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Crea respuesta para pregunta."""
        return SerializerFactory.serialize_data(
            serializer_type='question_read',
            data=question,
            context=context
        )

    @classmethod
    def create_save_and_advance_response(
        cls,
        result,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Crea respuesta para Save and Advance."""
        return SerializerFactory.serialize_data(
            serializer_type='save_and_advance_response',
            data=result,
            context=context
        )

    @classmethod
    def create_verification_response(
        cls,
        result,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Crea respuesta para verificación OCR."""
        return SerializerFactory.serialize_data(
            serializer_type='verification_response',
            data=result,
            context=context
        )

    @classmethod
    def create_list_response(
        cls,
        items,
        serializer_type: str,
        context: Optional[Dict[str, Any]] = None,
        pagination_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Crea respuesta para listados."""
        serialized_items = SerializerFactory.serialize_data(
            serializer_type=serializer_type,
            data=items,
            context=context,
            many=True
        )
        
        if pagination_data:
            return {
                'results': serialized_items,
                'count': pagination_data.get('count', len(serialized_items)),
                'next': pagination_data.get('next'),
                'previous': pagination_data.get('previous'),
            }
        
        return serialized_items


# Funciones de conveniencia para uso directo
def serialize_submission(submission, context=None, include_answers=False):
    """Función de conveniencia para serializar submissions."""
    return ResponseSerializerFactory.create_submission_response(
        submission, context, include_answers
    )

def serialize_question(question, context=None):
    """Función de conveniencia para serializar preguntas."""
    return ResponseSerializerFactory.create_question_response(question, context)

def serialize_save_and_advance_result(result, context=None):
    """Función de conveniencia para serializar resultados de Save and Advance."""
    return ResponseSerializerFactory.create_save_and_advance_response(result, context)

def serialize_verification_result(result, context=None):
    """Función de conveniencia para serializar resultados de verificación."""
    return ResponseSerializerFactory.create_verification_response(result, context)