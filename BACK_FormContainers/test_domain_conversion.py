#!/usr/bin/env python3
"""
Test script to verify domain conversion functions handle missing IDs correctly.
"""
import os
import sys
import django
from uuid import uuid4

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from app.interfaces.admin_views import _to_domain_questionnaire, _to_domain_question, _to_domain_choice

def test_domain_conversion():
    print("Testing domain conversion functions...")

    # Test data without IDs (simulating new entities from frontend)
    choice_data = {
        "text": "Opción 1",
        "branch_to": None
    }

    question_data = {
        "text": "¿Cuál es tu nombre?",
        "type": "text",
        "required": True,
        "order": 1,
        "choices": [],
        "semantic_tag": None,
        "file_mode": None
    }

    questionnaire_data = {
        "title": "Cuestionario de Prueba",
        "version": "1.0",
        "timezone": "America/Bogota",
        "questions": [question_data]
    }

    try:
        # Test choice conversion
        choice = _to_domain_choice(choice_data)
        print(f"✅ Choice created with ID: {choice.id}")
        assert choice.id is not None, "Choice ID should be generated"

        # Test question conversion
        question = _to_domain_question(question_data)
        print(f"✅ Question created with ID: {question.id}")
        assert question.id is not None, "Question ID should be generated"

        # Test questionnaire conversion
        questionnaire = _to_domain_questionnaire(questionnaire_data)
        print(f"✅ Questionnaire created with ID: {questionnaire.id}")
        assert questionnaire.id is not None, "Questionnaire ID should be generated"

        print("✅ All domain conversion functions work correctly!")
        return True

    except Exception as e:
        print(f"❌ Error in domain conversion: {e}")
        return False

if __name__ == "__main__":
    success = test_domain_conversion()
    sys.exit(0 if success else 1)
