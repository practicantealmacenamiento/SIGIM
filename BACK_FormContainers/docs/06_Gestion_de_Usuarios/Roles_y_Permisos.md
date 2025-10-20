# Roles y Permisos

## Roles definidos
- **Operador** (usuario autenticado sin `is_staff`): accede a endpoints operativos del prefijo `api/v1/`, puede crear submissions, guardar respuestas, consultar catalogos y ejecutar verificaciones OCR.
- **Staff** (`is_staff=True`): hereda permisos de Operador y adicionalmente gestiona recursos administrativos (`/api/v1/management/*`), accede a `/api/schema` y `/api/docs`.
- **Superusuario** (`is_superuser=True`): controla todo el backend incluyendo panel de administracion Django y cambios criticos.

## Permisos por funcionalidad
| Funcion | Operador | Staff | Superusuario |
|---------|----------|-------|--------------|
| Login/Logout | ✅ | ✅ | ✅ |
| Guardar y Avanzar | ✅ | ✅ | ✅ |
| Consulta de historial | ✅ | ✅ | ✅ |
| Catalogo de actores (lectura) | ✅ | ✅ | ✅ |
| CRUD de actors (management) | ❌ | ✅ | ✅ |
| CRUD de cuestionarios | ❌ | ✅ | ✅ |
| CRUD de usuarios internos | ❌ | ✅ | ✅ |
| Acceso schema Swagger privado | ❌ | ✅ | ✅ |
| Panel Django Admin (`/admin/`) | ❌ | ✅ (segun permisos) | ✅ |

## Politicas de autenticacion
- Las credenciales se validan via `POST /api/v1/login` usando usuario o correo y contrasenia.
- Tras el login exitoso se emite token DRF y se setean cookies auxiliares (`csrftoken`, `is_staff`).
- El endpoint `whoami` se utiliza para refrescar la sesion en el frontend.
- Para revocar credenciales, `POST /api/v1/logout` invalida la sesion y limpia cookies.

## Provision de usuarios
- El modulo `AdminUserViewSet` permite crear usuarios internos, asignar estado activo e indicator de staff/superusuario.
- Las contrasenias se cifran con `make_password` y se exige confirmacion antes de activar cuentas.
- Se recomienda habilitar rotacion periodica de contrasenias via politicas corporativas.

## Recomendaciones operativas
- Mantener cuentas de servicio separadas para integraciones automaticas (si aplica).
- Revocar accesos de staff que no hayan ingresado en los ultimos 90 dias.
- Registrar en bitacora cualquier cambio de rol o creacion de usuarios administrativos.
