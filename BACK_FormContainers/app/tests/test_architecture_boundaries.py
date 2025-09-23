"""
Pruebas arquitectónicas para verificar límites entre capas de Clean Architecture.

Estas pruebas aseguran que:
1. La capa de dominio no importe de capas externas
2. La capa de aplicación solo dependa de dominio
3. La capa de infraestructura implemente interfaces de dominio
4. Las dependencias fluyan hacia adentro (hacia el dominio)
"""
import ast
import os
import sys
from pathlib import Path
from typing import Set, List, Dict, Tuple
import unittest


class ArchitectureBoundaryTests(unittest.TestCase):
    """
    Pruebas que verifican los límites arquitectónicos entre capas.
    """

    def setUp(self):
        """Configuración inicial para las pruebas."""
        self.app_path = Path(__file__).parent.parent
        self.domain_path = self.app_path / "domain"
        self.application_path = self.app_path / "application"
        self.infrastructure_path = self.app_path / "infrastructure"
        self.interfaces_path = self.app_path / "interfaces"

    def test_domain_layer_has_no_external_dependencies(self):
        """
        Verifica que la capa de dominio no importe de capas externas.
        
        La capa de dominio debe ser completamente independiente de:
        - Django/DRF
        - Infraestructura
        - Interfaces
        - Aplicación
        """
        forbidden_imports = {
            'django',
            'rest_framework',
            'app.infrastructure',
            'app.interfaces',
            'app.application',
        }
        
        domain_files = self._get_python_files(self.domain_path)
        violations = []
        
        for file_path in domain_files:
            imports = self._extract_imports(file_path)
            for imp in imports:
                if any(imp.startswith(forbidden) for forbidden in forbidden_imports):
                    violations.append(f"{file_path.name}: imports {imp}")
        
        self.assertEqual(
            [], violations,
            f"Domain layer has forbidden imports:\n" + "\n".join(violations)
        )

    def test_application_layer_only_depends_on_domain(self):
        """
        Verifica que la capa de aplicación solo dependa de dominio.
        
        La capa de aplicación puede importar:
        - Módulos estándar de Python
        - Capa de dominio
        
        No puede importar:
        - Django/DRF (excepto tipos básicos como UUID)
        - Infraestructura
        - Interfaces
        """
        allowed_external_imports = {
            'datetime',
            'typing',
            'uuid',
            'os',
            'dataclasses',
            'enum',
            'abc',
            '__future__',
        }
        
        forbidden_imports = {
            'django',
            'rest_framework',
            'app.infrastructure',
            'app.interfaces',
        }
        
        application_files = self._get_python_files(self.application_path)
        violations = []
        
        for file_path in application_files:
            imports = self._extract_imports(file_path)
            for imp in imports:
                # Permitir imports de dominio
                if imp.startswith('app.domain'):
                    continue
                
                # Permitir imports estándar de Python
                if any(imp.startswith(allowed) for allowed in allowed_external_imports):
                    continue
                
                # Verificar imports prohibidos
                if any(imp.startswith(forbidden) for forbidden in forbidden_imports):
                    violations.append(f"{file_path.name}: imports {imp}")
                
                # Verificar imports de módulos estándar no listados
                if '.' not in imp or imp.split('.')[0] in sys.stdlib_module_names:
                    continue
                
                # Si llegamos aquí, es un import externo no permitido
                if not imp.startswith('app.domain'):
                    violations.append(f"{file_path.name}: imports external module {imp}")
        
        self.assertEqual(
            [], violations,
            f"Application layer has forbidden imports:\n" + "\n".join(violations)
        )

    def test_infrastructure_implements_domain_interfaces(self):
        """
        Verifica que la infraestructura implemente interfaces de dominio.
        
        Busca clases en infraestructura que implementen protocolos/interfaces
        definidos en el dominio.
        """
        # Extraer interfaces/protocolos del dominio
        domain_protocols = self._extract_protocols_from_domain()
        
        # Extraer implementaciones de infraestructura
        infrastructure_implementations = self._extract_implementations_from_infrastructure()
        
        # Verificar que las implementaciones realmente implementen los protocolos
        missing_implementations = []
        for protocol in domain_protocols:
            if not any(protocol in impl_protocols for impl_protocols in infrastructure_implementations.values()):
                missing_implementations.append(protocol)
        
        # Esta prueba es informativa - reporta qué protocolos no tienen implementación
        if missing_implementations:
            print(f"Warning: Domain protocols without infrastructure implementation: {missing_implementations}")
        
        # Verificar que las implementaciones existentes sean válidas
        invalid_implementations = []
        for impl_class, protocols in infrastructure_implementations.items():
            for protocol in protocols:
                if protocol not in domain_protocols:
                    invalid_implementations.append(f"{impl_class} claims to implement non-existent protocol {protocol}")
        
        self.assertEqual(
            [], invalid_implementations,
            f"Invalid protocol implementations:\n" + "\n".join(invalid_implementations)
        )

    def test_dependency_direction_flows_inward(self):
        """
        Verifica que las dependencias fluyan hacia adentro (hacia el dominio).
        
        Orden de dependencias permitido:
        Interfaces -> Application -> Domain
        Infrastructure -> Domain
        """
        dependency_violations = []
        
        # Interfaces puede depender de Application y Domain
        interfaces_files = self._get_python_files(self.interfaces_path)
        for file_path in interfaces_files:
            imports = self._extract_imports(file_path)
            for imp in imports:
                if imp.startswith('app.infrastructure'):
                    dependency_violations.append(
                        f"Interfaces layer ({file_path.name}) imports from Infrastructure: {imp}"
                    )
        
        # Infrastructure solo puede depender de Domain
        infrastructure_files = self._get_python_files(self.infrastructure_path)
        for file_path in infrastructure_files:
            imports = self._extract_imports(file_path)
            for imp in imports:
                if imp.startswith('app.application') or imp.startswith('app.interfaces'):
                    dependency_violations.append(
                        f"Infrastructure layer ({file_path.name}) imports from outer layer: {imp}"
                    )
        
        self.assertEqual(
            [], dependency_violations,
            f"Dependency direction violations:\n" + "\n".join(dependency_violations)
        )

    def test_no_circular_dependencies_between_layers(self):
        """
        Verifica que no existan dependencias circulares entre capas.
        """
        layer_dependencies = {
            'domain': set(),
            'application': set(),
            'infrastructure': set(),
            'interfaces': set(),
        }
        
        # Mapear archivos a capas
        layer_files = {
            'domain': self._get_python_files(self.domain_path),
            'application': self._get_python_files(self.application_path),
            'infrastructure': self._get_python_files(self.infrastructure_path),
            'interfaces': self._get_python_files(self.interfaces_path),
        }
        
        # Extraer dependencias entre capas
        for layer, files in layer_files.items():
            for file_path in files:
                imports = self._extract_imports(file_path)
                for imp in imports:
                    if imp.startswith('app.'):
                        target_layer = imp.split('.')[1]
                        if target_layer in layer_dependencies and target_layer != layer:
                            layer_dependencies[layer].add(target_layer)
        
        # Detectar ciclos
        circular_dependencies = self._detect_cycles(layer_dependencies)
        
        self.assertEqual(
            [], circular_dependencies,
            f"Circular dependencies detected:\n" + "\n".join(circular_dependencies)
        )

    # Helper methods
    
    def _get_python_files(self, directory: Path) -> List[Path]:
        """Obtiene todos los archivos Python en un directorio."""
        if not directory.exists():
            return []
        
        python_files = []
        for file_path in directory.rglob("*.py"):
            if file_path.name != "__init__.py":
                python_files.append(file_path)
        return python_files

    def _extract_imports(self, file_path: Path) -> Set[str]:
        """Extrae todos los imports de un archivo Python."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            imports = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
            
            return imports
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            return set()

    def _extract_protocols_from_domain(self) -> Set[str]:
        """Extrae nombres de protocolos/interfaces del dominio."""
        protocols = set()
        domain_files = self._get_python_files(self.domain_path)
        
        for file_path in domain_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Buscar clases que hereden de Protocol o ABC
                        for base in node.bases:
                            if isinstance(base, ast.Name) and base.id in ('Protocol', 'ABC'):
                                protocols.add(node.name)
                            elif isinstance(base, ast.Attribute) and base.attr in ('Protocol', 'ABC'):
                                protocols.add(node.name)
            except (SyntaxError, UnicodeDecodeError):
                continue
        
        return protocols

    def _extract_implementations_from_infrastructure(self) -> Dict[str, List[str]]:
        """Extrae implementaciones de protocolos de la infraestructura."""
        implementations = {}
        infrastructure_files = self._get_python_files(self.infrastructure_path)
        
        for file_path in infrastructure_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Buscar clases que implementen protocolos
                        implemented_protocols = []
                        for base in node.bases:
                            if isinstance(base, ast.Name):
                                implemented_protocols.append(base.id)
                            elif isinstance(base, ast.Attribute):
                                implemented_protocols.append(base.attr)
                        
                        if implemented_protocols:
                            implementations[node.name] = implemented_protocols
            except (SyntaxError, UnicodeDecodeError):
                continue
        
        return implementations

    def _detect_cycles(self, dependencies: Dict[str, Set[str]]) -> List[str]:
        """Detecta dependencias circulares usando DFS."""
        def dfs(node: str, visited: Set[str], rec_stack: Set[str], path: List[str]) -> List[str]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in dependencies.get(node, set()):
                if neighbor not in visited:
                    cycle = dfs(neighbor, visited, rec_stack, path)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Encontramos un ciclo
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
            
            rec_stack.remove(node)
            path.pop()
            return []
        
        visited = set()
        cycles = []
        
        for node in dependencies:
            if node not in visited:
                cycle = dfs(node, visited, set(), [])
                if cycle:
                    cycles.append(" -> ".join(cycle))
        
        return cycles


if __name__ == '__main__':
    unittest.main()