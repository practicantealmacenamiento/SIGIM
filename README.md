# Sistema de Formularios - Proyecto Completo

Este proyecto consiste en un backend Django con Clean Architecture y un frontend Next.js.

## Estructura del Proyecto

```
├── BACK_FormContainers/     # Backend Django
├── FRONT_FormContainers/    # Frontend Next.js
└── README.md               # Este archivo
```

## Requisitos Previos

- Python 3.11+
- Node.js 18+
- npm o yarn

## Configuración y Ejecución

### 1. Backend (Django)

```bash
cd BACK_FormContainers

# Instalar dependencias
pip install -r requirements.txt

# Verificar configuración
python manage.py check

# Ejecutar migraciones (si es necesario)
python manage.py migrate

# Ejecutar servidor de desarrollo
python manage.py runserver 0.0.0.0:8000
```

El backend estará disponible en: http://localhost:8000

### 2. Frontend (Next.js)

```bash
cd FRONT_FormContainers

# Instalar dependencias
npm install

# Verificar build
npm run build

# Ejecutar servidor de desarrollo
npm run dev
```

El frontend estará disponible en: http://localhost:3000

## Verificación de Funcionamiento

### Backend
- ✅ Arquitectura Clean implementada
- ✅ Separación de capas (Domain, Application, Infrastructure, Interfaces)
- ✅ Dependency injection con Factory pattern
- ✅ Validación de dependencias con import-linter
- ✅ Tests unitarios funcionando
- ✅ Mock de Google Vision para desarrollo

### Frontend
- ✅ Next.js 15 con App Router
- ✅ TypeScript configurado
- ✅ Suspense boundaries implementados
- ✅ Build exitoso
- ✅ Conexión configurada con backend

## Endpoints Principales

### API Backend
- `GET /api/cuestionarios/` - Lista de cuestionarios
- `POST /api/submissions/` - Crear submission
- `POST /api/cuestionario/guardar_avanzar/` - Guardar respuesta y avanzar
- `POST /api/verificar/` - Verificación OCR
- `GET /api/admin/whoami/` - Información de usuario

### Páginas Frontend
- `/` - Dashboard principal
- `/formulario` - Formulario dinámico
- `/historial` - Historial de submissions
- `/admin` - Panel de administración
- `/login` - Inicio de sesión

## Arquitectura

### Backend - Clean Architecture
```
app/
├── domain/          # Entidades, reglas de negocio, puertos
├── application/     # Casos de uso, servicios de aplicación
├── infrastructure/  # Implementaciones, adaptadores, BD
└── interfaces/      # Controladores HTTP, serializers
```

### Frontend - Estructura Modular
```
src/
├── app/            # Next.js App Router
├── components/     # Componentes reutilizables
├── lib/           # Clientes API, utilidades
└── types/         # Definiciones de tipos TypeScript
```

## Características Implementadas

- **Formularios Dinámicos**: Carga de preguntas desde backend
- **OCR Integration**: Procesamiento de imágenes (con mock para desarrollo)
- **Autenticación**: Sistema de login con tokens
- **Responsive Design**: Interfaz adaptable
- **Dark Mode**: Soporte para tema oscuro
- **Validación**: Validación en frontend y backend
- **Error Handling**: Manejo robusto de errores
- **Testing**: Tests unitarios en backend

## Solución de Problemas

### Backend no inicia
1. Verificar que Python 3.11+ esté instalado
2. Instalar dependencias: `pip install -r requirements.txt`
3. Verificar configuración: `python manage.py check`

### Frontend no compila
1. Verificar que Node.js 18+ esté instalado
2. Limpiar node_modules: `rm -rf node_modules && npm install`
3. Verificar build: `npm run build`

### Conexión Backend-Frontend
1. Verificar que el backend esté ejecutándose en puerto 8000
2. Verificar variables de entorno en `.env.local`
3. Verificar CORS configurado en Django

## Desarrollo

Para desarrollo local:

1. Ejecutar backend en una terminal: `cd BACK_FormContainers && python manage.py runserver`
2. Ejecutar frontend en otra terminal: `cd FRONT_FormContainers && npm run dev`
3. Abrir http://localhost:3000 en el navegador

## Notas Técnicas

- El sistema usa Google Vision API para OCR, pero incluye un mock para desarrollo
- La autenticación usa tokens de Django REST Framework
- El frontend usa Suspense boundaries para mejor UX
- El backend implementa Clean Architecture con validación de dependencias