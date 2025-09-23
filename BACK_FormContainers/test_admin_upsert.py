#!/usr/bin/env python
"""
Script de prueba para diagnosticar el error 400 en /api/admin/questionnaires/upsert/
"""

import os
import sys
import django
import json
import requests
from uuid import uuid4

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from app.infrastructure.serializers import DomainQuestionnaireSerializer

def test_serializer_validation():
    """Prueba la validación del serializer con datos de ejemplo."""
    
    print("=== PRUEBA DE VALIDACIÓN DEL SERIALIZER ===")
    
    # Datos de ejemplo que podrían estar enviándose desde el frontend
    sample_data = {
        "id": str(uuid4()),
        "title": "Cuestionario de Prueba",
        "version": "1.0",
        "timezone": "America/Bogota",
        "questions": [
            {
                "id": str(uuid4()),
                "text": "¿Cuál es tu nombre?",
                "type": "text",
                "required": True,
                "order": 1,
                "choices": [],
                "semantic_tag": None,
                "file_mode": None
            },
            {
                "id": str(uuid4()),
                "text": "Selecciona una opción",
                "type": "choice",
                "required": True,
                "order": 2,
                "choices": [
                    {
                        "id": str(uuid4()),
                        "text": "Opción 1",
                        "branch_to": None
                    },
                    {
                        "id": str(uuid4()),
                        "text": "Opción 2", 
                        "branch_to": None
                    }
                ],
                "semantic_tag": None,
                "file_mode": None
            }
        ]
    }
    
    print("Datos de entrada:")
    print(json.dumps(sample_data, indent=2))
    print()
    
    # Probar validación
    serializer = DomainQuestionnaireSerializer(data=sample_data)
    
    if serializer.is_valid():
        print("✅ ÉXITO: Los datos son válidos")
        print("Datos validados:")
        print(json.dumps(serializer.validated_data, indent=2, default=str))
        return True
    else:
        print("❌ ERROR: Los datos no son válidos")
        print("Errores de validación:")
        print(json.dumps(serializer.errors, indent=2))
        return False

def test_api_call():
    """Prueba la llamada real al API."""
    
    print("\n=== PRUEBA DE LLAMADA AL API ===")
    
    # Datos mínimos para probar
    test_data = {
        "id": str(uuid4()),
        "title": "Test Questionnaire",
        "version": "1.0",
        "timezone": "America/Bogota",
        "questions": []
    }
    
    try:
        # Hacer llamada al endpoint local
        url = "http://localhost:8000/api/admin/questionnaires/upsert/"
        
        # Necesitarías un token válido aquí
        headers = {
            "Content-Type": "application/json",
            # "Authorization": "Token YOUR_TOKEN_HERE"
        }
        
        print(f"Enviando POST a: {url}")
        print("Datos:")
        print(json.dumps(test_data, indent=2))
        
        # Comentado porque necesita autenticación
        # response = requests.post(url, json=test_data, headers=headers)
        # print(f"Status: {response.status_code}")
        # print(f"Response: {response.text}")
        
        print("⚠️  Llamada al API omitida (requiere token de autenticación)")
        
    except Exception as e:
        print(f"❌ ERROR en llamada al API: {e}")

if __name__ == "__main__":
    print("Iniciando diagnóstico del error de upsert...\n")
    
    success = test_serializer_validation()
    test_api_call()
    
    if success:
        print("\n✅ El serializer funciona correctamente.")
        print("El problema podría estar en:")
        print("1. Datos mal formateados desde el frontend")
        print("2. Falta de autenticación/permisos")
        print("3. Problema en la conversión de datos")
    else:
        print("\n❌ Hay problemas con la validación del serializer")
