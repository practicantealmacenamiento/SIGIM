# Plan de Soporte

## Objetivos
- Garantizar disponibilidad del frontend en horarios criticos de ingreso de mercancia.
- Detectar y resolver incidentes de UI o integracion antes de que afecten al personal operativo.
- Mantener sincronizacion entre releases de frontend y backend.

## Niveles de soporte
- **Nivel 1 (Mesa de ayuda)**: atiende reportes, valida estado del servicio (`/login`, `/formulario`), captura evidencias (capturas, HAR).
- **Nivel 2 (Equipo frontend)**: reproduce incidencias, inspecciona consola/Network, revisa despliegues recientes y coordina rollbacks.
- **Nivel 3 (Equipo de plataforma/DevOps)**: gestiona infraestructura de despliegue (Vercel, contenedores, CDN) y soporte externo (Sentry, CDN provider).

## Flujo de atencion
1. Registrar incidente con hora, usuario afectado, URL y navegador.
2. Nivel 1 revisa consola del navegador y estado de la red (HAR) para descartar problemas locales.
3. Nivel 2 reproduce el caso en staging, inspecciona logs del backend relacionados y revisa integraciones (`NEXT_PUBLIC_*`).
4. Si es bug de frontend, se genera hotfix (rama a partir de `main`), se ejecutan `npm run lint` + `npm run build` y se despliega tras validacion.
5. Documentar solucion, version desplegada y lecciones aprendidas en la base de conocimiento.

## Mantenimiento preventivo
- Ejecutar `npm run lint` y `npm run build` en cada merge.
- Revisar dependencias con `npm outdated` y `npm audit` mensualmente.
- Verificar accesos de usuarios staff en `/admin` y limpiar tokens persistentes (`localStorage`) durante auditorias.
- Confirmar que las variables `NEXT_PUBLIC_*` en produccion coinciden con la configuracion del backend.
- Validar renderizado responsivo en breakpoints principales cada release.

## Indicadores de soporte
- Tiempo medio de resolucion (MTTR) por severidad.
- Numero de incidencias causadas por configuracion (`NEXT_PUBLIC_*` incorrectas).
- Tasa de regresiones detectadas tras despliegues.
- Porcentaje de errores de red atribuibles al backend (coordinar con equipo backend).

## Comunicaciones
- Notificar despliegues y incidentes relevantes via correo o canales de chat corporativos (Teams/Slack).
- Mantener calendario compartido de ventanas de mantenimiento (minimo 48 horas de aviso).
- Publicar resumen de incidentes mayores y acciones preventivas posteriores.

