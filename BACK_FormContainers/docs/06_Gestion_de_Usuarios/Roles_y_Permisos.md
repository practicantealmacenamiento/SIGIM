# Roles y Permisos

## Roles definidos
- **Operador**: usuario autenticado sin privilegios de staff. Accede a flujos operativos (`/api/v1/*`), Guardar y Avanzar, historial y verificaciones OCR.
- **Staff**: usuario con `is_staff=True`. Hereda permisos de operador y accede a endpoints administrativos (`/api/v1/management/*`, `/api/v1/schema`, `/api/v1/docs`).
- **Superusuario**: `is_superuser=True`. Control total del backend, incluido panel Django (`/admin/`), manejo de usuarios y ejecucion de comandos sensibles.

## Matriz de permisos
| Funcion / Endpoint | Operador | Staff | Superusuario |
|--------------------|----------|-------|--------------|
| `POST /api/v1/login`, `POST /api/v1/logout`, `GET /api/v1/whoami` | Si | Si | Si |
| Guardar y Avanzar (`/api/v1/cuestionario/*`) | Si | Si | Si |
| Verificacion OCR (`/api/v1/verificar`) | Si | Si | Si |
| Submissions (`/api/v1/submissions/*`) | Si | Si | Si |
| Historial (`/api/v1/historial/reguladores`) | Si | Si | Si |
| Catalogo de actores (`/api/v1/catalogos/actores`) | Si | Si | Si |
| Endpoints administrativos (`/api/v1/management/actors|questionnaires|users`) | No | Si | Si |
| Documentacion privada (`/api/v1/schema`, `/api/v1/docs`, `/api/v1/redoc`) | No | Si | Si |
| Panel Django admin (`/admin/`) | No | Opcional (segun permisos asignados) | Si |
| Ejecucion de comandos de soporte (`report_vision_usage`, migraciones) | No | Bajo supervision | Si |

> Nota: los permisos adicionales pueden gestionarse mediante grupos y asignaciones especificas en el administrador de Django.

## Politicas de autenticacion
- Credenciales validadas via `POST /api/v1/login` con usuario, correo o identificador. Respuesta incluye token DRF y cookies auxiliares (`csrftoken`, `is_staff`, `auth_username`).
- Las sesiones se revalidan usando `GET /api/v1/whoami`. El frontend debe forzar logout al recibir 401.
- `BearerOrTokenAuthentication` acepta tokens DRF (`Authorization: Token <key>`) o tokens bearer generados durante el login.
- Para integraciones directas (sin usuario interactivo) se puede activar `TokenRequiredForWrite` y compartir `API_SECRET_TOKEN`.

## Provision y offboarding
- `AdminUserViewSet` permite crear usuarios, activar/desactivar cuentas y asignar flags `is_staff`, `is_superuser`.
- Contrasenas se almacenan cifradas; se recomienda forzar cambio inicial y politica de rotacion corporativa.
- Durante offboarding se deben revocar tokens, deshabilitar el usuario y retirar accesos a sistemas externos.

## Recomendaciones operativas
- Revisar trimestralmente usuarios con `is_staff` o `is_superuser` y revocar accesos inactivos.
- Documentar altas/bajas de usuarios y cambios de rol en el sistema ITSM.
- Usar cuentas de servicio independientes para integraciones automatizadas y proteger el `API_SECRET_TOKEN`.
