#!/usr/bin/env python
"""
Script de prueba para verificar que el fix del precinto funciona correctamente.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from app.domain.precinto_simple import get_precinto_info_simple

def test_precinto_detection():
    """Prueba la detección de precintos con el texto del error original."""
    
    # Texto del error original
    texto_prueba = "0048684\n0048684"
    
    print("=== PRUEBA DE DETECCIÓN DE PRECINTOS ===")
    print(f"Texto de entrada: '{texto_prueba}'")
    print()
    
    # Ejecutar detección
    resultado = get_precinto_info_simple(texto_prueba)
    
    print("Resultado de la detección:")
    for clave, valor in resultado.items():
        print(f"  {clave}: {valor}")
    
    print()
    
    # Verificar que no hay KeyError
    claves_esperadas = ["precinto", "confianza", "razon", "texto_limpio", "candidatos"]
    claves_faltantes = [clave for clave in claves_esperadas if clave not in resultado]
    
    if claves_faltantes:
        print(f"❌ ERROR: Faltan las claves: {claves_faltantes}")
        return False
    else:
        print("✅ ÉXITO: Todas las claves esperadas están presentes")
    
    # Verificar detección
    if resultado["precinto"] != "NO DETECTADO":
        print(f"✅ ÉXITO: Precinto detectado: {resultado['precinto']}")
    else:
        print("⚠️  ADVERTENCIA: No se detectó precinto")
    
    return True

def test_edge_cases():
    """Prueba casos extremos."""
    
    print("\n=== PRUEBAS DE CASOS EXTREMOS ===")
    
    casos = [
        ("", "texto vacío"),
        (None, "texto None"),
        ("texto sin números", "sin patrones válidos"),
        ("WK01305", "formato alfanumérico"),
        ("123456", "solo números cortos"),
        ("1234567", "solo números largos")
    ]
    
    for texto, descripcion in casos:
        print(f"\nProbando: {descripcion}")
        print(f"Entrada: {repr(texto)}")
        
        try:
            resultado = get_precinto_info_simple(texto)
            print(f"✅ OK - Precinto: {resultado['precinto']}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("Iniciando pruebas del fix de precintos...\n")
    
    success1 = test_precinto_detection()
    success2 = test_edge_cases()
    
    if success1 and success2:
        print("\n🎉 TODAS LAS PRUEBAS PASARON - El fix está funcionando correctamente!")
        sys.exit(0)
    else:
        print("\n💥 ALGUNAS PRUEBAS FALLARON - Revisar el código")
        sys.exit(1)
