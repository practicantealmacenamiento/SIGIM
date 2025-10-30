# Roles y Permisos

## Roles reconocidos
- **Operador**: usuario autenticado sin privilegios de staff. Puede acceder a `/formulario`, `/historial`, `/panel` (solo lectura para continuidad), descargar CSV y consumir funciones OCR.
- **Staff**: usuario con `is_staff=1`. Accede a todas las vistas del operador y ademas a `/admin/*` (cuestionarios, actores, usuarios) y acciones de creacion/edicion en el panel (fase 2).
- **Superusuario**: rol extendido (sin gestion directa en frontend). Hereda permisos de staff y mantiene acceso total mediante el backend; en la UI se comporta como staff.

## Matriz de acceso
| Modulo / Ruta | Operador | Staff / Superusuario |
|---------------|----------|----------------------|
| `/login` | Acceso | Acceso (redirecciona a `/` si ya esta autenticado) |
| `/formulario` | Crear/reanudar submissions, usar OCR, finalizar | Idem operador |
| `/historial` | Consultar, filtrar, exportar CSV | Idem operador + ver datos administrativos |
| `/panel` | Ver lista fase 1 (solo lectura) | Crear/continuar fase 2, navegar a formulario |
| `/admin/cuestionarios` | No | CRUD completo |
| `/admin/actores` | No | CRUD completo |
| `/admin/usuarios` | No | CRUD completo |

## Controles implementados
- **Middleware**: redirige a `/login` cuando no hay sesion y bloquea `/admin/*` si la cookie `is_staff` es distinta de `1`.
- **Header**: muestra enlaces del panel y admin segun `user.is_staff`.
- **Componentes**: botones administrativos se deshabilitan automaticamente si el usuario pierde permisos durante la sesion (`AuthProvider.refresh`).

## Provision y offboarding
- La creacion de usuarios se realiza en el backend (panel administrativo o Django Admin). El frontend refleja los cambios via `api.admin.ts`.
- Ante offboarding, eliminar token (`localStorage`) y cookies (`auth_token`, `sessionid`, `is_staff`) cerrando la sesion desde `AuthProvider.logout`.
- Staff debe renovar credenciales en el backend; el frontend solo actua como consumidor.

## Recomendaciones operativas
- Revisar trimestralmente usuarios con `is_staff` y revocar accesos inactivos.
- Evitar compartir sesiones entre usuarios; cerrar sesion al finalizar turno.
- Documentar altas/bajas en la herramienta ITSM y notificar al equipo backend para asegurar sincronizacion.

