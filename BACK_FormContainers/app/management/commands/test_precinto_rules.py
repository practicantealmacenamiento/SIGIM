"""
Comando para probar y ajustar las reglas de detección de precintos.
Útil para debugging y mejora del sistema.

Uso:
python manage.py test_precinto_rules --texto "PRECINTO TDM38816"
python manage.py test_precinto_rules --file ejemplos_precintos.txt
python manage.py test_precinto_rules --interactive
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import os
import json
from typing import List, Dict, Any

from app.domain.precinto_rules import (
    PrecintoDetector, 
    limpiar_precinto_mejorado, 
    get_precinto_detection_info
)
from app.domain.rules import limpiar_precinto as limpiar_original


class Command(BaseCommand):
    help = 'Prueba y ajusta las reglas de detección de precintos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--texto',
            type=str,
            help='Texto específico para probar'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Archivo con ejemplos de texto OCR (uno por línea)'
        )
        parser.add_argument(
            '--interactive',
            action='store_true',
            help='Modo interactivo para probar múltiples textos'
        )
        parser.add_argument(
            '--compare',
            action='store_true',
            help='Comparar con la implementación original'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Archivo para guardar los resultados en JSON'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada'
        )

    def handle(self, *args, **options):
        self.verbose = options['verbose']
        self.compare = options['compare']
        
        if options['interactive']:
            self.run_interactive_mode()
        elif options['texto']:
            self.test_single_text(options['texto'])
        elif options['file']:
            self.test_from_file(options['file'], options.get('output'))
        else:
            self.show_examples()

    def run_interactive_mode(self):
        """Modo interactivo para probar múltiples textos."""
        self.stdout.write(
            self.style.SUCCESS("Modo interactivo - Ingresa textos para probar (Ctrl+C para salir)")
        )
        
        try:
            while True:
                texto = input("\nTexto OCR: ").strip()
                if not texto:
                    continue
                    
                self.test_single_text(texto)
                
        except KeyboardInterrupt:
            self.stdout.write("\n" + self.style.SUCCESS("¡Hasta luego!"))

    def test_single_text(self, texto: str):
        """Prueba un texto específico."""
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"TEXTO: '{texto}'")
        self.stdout.write('='*60)
        
        # Resultado mejorado
        info = get_precinto_detection_info(texto)
        resultado_mejorado = info["precinto"]
        
        self.stdout.write(
            f"🔍 RESULTADO MEJORADO: {self.style.SUCCESS(resultado_mejorado) if resultado_mejorado != 'NO DETECTADO' else self.style.ERROR(resultado_mejorado)}"
        )
        
        if self.verbose:
            self.stdout.write(f"   Confianza: {info['confianza']:.2f}")
            self.stdout.write(f"   Razón: {info['razon']}")
            
            if info['candidatos']:
                self.stdout.write("   Candidatos:")
                for i, candidato in enumerate(info['candidatos'][:3], 1):
                    self.stdout.write(
                        f"     {i}. '{candidato['texto']}' "
                        f"(confianza: {candidato['confianza']:.2f}, "
                        f"razones: {', '.join(candidato['razones'])})"
                    )
        
        # Comparar con implementación original si se solicita
        if self.compare:
            resultado_original = limpiar_original(texto)
            self.stdout.write(
                f"📊 RESULTADO ORIGINAL: {self.style.WARNING(resultado_original)}"
            )
            
            if resultado_mejorado != resultado_original:
                self.stdout.write(
                    self.style.NOTICE("⚠️  DIFERENCIA DETECTADA entre implementaciones")
                )

    def test_from_file(self, file_path: str, output_path: str = None):
        """Prueba textos desde un archivo."""
        if not os.path.exists(file_path):
            raise CommandError(f"Archivo no encontrado: {file_path}")
        
        results = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        self.stdout.write(f"Probando {len(lines)} textos desde {file_path}...")
        
        for i, texto in enumerate(lines, 1):
            self.stdout.write(f"\n[{i}/{len(lines)}] Procesando: '{texto[:50]}{'...' if len(texto) > 50 else ''}'")
            
            info = get_precinto_detection_info(texto)
            resultado_mejorado = info["precinto"]
            
            result = {
                "texto": texto,
                "resultado_mejorado": resultado_mejorado,
                "confianza": info["confianza"],
                "razon": info["razon"],
                "candidatos": info["candidatos"][:3]  # Top 3
            }
            
            if self.compare:
                resultado_original = limpiar_original(texto)
                result["resultado_original"] = resultado_original
                result["diferencia"] = resultado_mejorado != resultado_original
            
            results.append(result)
            
            # Mostrar resultado
            status = self.style.SUCCESS("✓") if resultado_mejorado != "NO DETECTADO" else self.style.ERROR("✗")
            self.stdout.write(f"   {status} {resultado_mejorado}")
        
        # Estadísticas
        detectados = sum(1 for r in results if r["resultado_mejorado"] != "NO DETECTADO")
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"ESTADÍSTICAS:")
        self.stdout.write(f"  Total textos: {len(results)}")
        self.stdout.write(f"  Precintos detectados: {detectados}")
        self.stdout.write(f"  Tasa de detección: {detectados/len(results)*100:.1f}%")
        
        if self.compare:
            diferencias = sum(1 for r in results if r.get("diferencia", False))
            self.stdout.write(f"  Diferencias con original: {diferencias}")
        
        # Guardar resultados si se especifica
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            self.stdout.write(f"Resultados guardados en: {output_path}")

    def show_examples(self):
        """Muestra ejemplos de uso."""
        examples = [
            "PRECINTO DE SEGURIDAD: TDM38816",
            "SEAL NUMBER: ABC12345",
            "TDM 388 16",
            "NUMERO: TDM-388-16",
            "PLACA ABC123 PRECINTO TDM38816",
            "CONTENEDOR ABCD1234567 SELLO XYZ789",
            "123ABC456DEF",
            "SOLO TEXTO SIN NUMEROS",
        ]
        
        self.stdout.write(self.style.SUCCESS("Ejemplos de detección de precintos:"))
        self.stdout.write("="*60)
        
        for ejemplo in examples:
            info = get_precinto_detection_info(ejemplo)
            resultado = info["precinto"]
            
            status = "✓" if resultado != "NO DETECTADO" else "✗"
            color = self.style.SUCCESS if resultado != "NO DETECTADO" else self.style.ERROR
            
            self.stdout.write(f"{status} '{ejemplo}'")
            self.stdout.write(f"   → {color(resultado)}")
            
            if self.verbose and info["confianza"] > 0:
                self.stdout.write(f"   → Confianza: {info['confianza']:.2f}")
        
        self.stdout.write("\n" + self.style.NOTICE("Usa --help para ver todas las opciones disponibles"))


# Función auxiliar para crear archivo de ejemplos
def create_example_file():
    """Crea un archivo de ejemplo para testing."""
    examples = [
        "PRECINTO DE SEGURIDAD: TDM38816",
        "SEAL NUMBER: ABC12345", 
        "TDM 388 16",
        "NUMERO: TDM-388-16",
        "PLACA ABC123 PRECINTO TDM38816",
        "CONTENEDOR ABCD1234567 SELLO XYZ789",
        "123ABC456DEF",
        "PRECINTO: XYZ123456",
        "SELLO NUMERO 789ABC123",
        "SECURITY SEAL: DEF456789",
        "SOLO TEXTO SIN NUMEROS",
        "123456789",
        "ABCDEFGH",
        "",
    ]
    
    with open("ejemplos_precintos.txt", "w", encoding="utf-8") as f:
        for example in examples:
            f.write(example + "\n")
    
    print("Archivo 'ejemplos_precintos.txt' creado con ejemplos de prueba")


if __name__ == "__main__":
    # Si se ejecuta directamente, crear archivo de ejemplos
    create_example_file()
