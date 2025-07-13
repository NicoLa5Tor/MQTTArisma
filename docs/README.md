# Documentación del Sistema MQTT

## Introducción

Este sistema permite la gestión y monitoreo de alertas MQTT para tu infraestructura. Proporciona herramientas robustas de logging, métricas en tiempo real, y un dashboard interactivo.

## Componentes Principales

1. **Servidor MQTT**
   - Gestiona las conexiones y mensajes MQTT, asegurándose de validar el hardware antes de procesar alertas de empresa y sede.

2. **Backend REST**
   - Proporciona endpoints para el registro y validación de alertas. Integra con una base de datos para persistir información crítica.
   
3. **Cliente MQTT**
   - Envía mensajes al backend y maneja respuestas según las condiciones predefinidas.

4. **Logger y Monitoreo**
   - Logs distribuidos para mensajes del sistema, alertas y errores.
   - Recolección de métricas con una vista de monitoreo en tiempo real a través de un panel desarrollado en Flask.

## Estructura del Proyecto

- **`mqtt_connection/`**: Contiene la lógica de conexión MQTT.
- **`backend/`**: Implementación del servidor backend y sus endpoints.
- **`client/`**: Cliente MQTT para simulación y validación.
- **`monitoring/`**: Incluye el sistema de logging, métricas y dashboard en Flask.

## Configuración Inicia

- **Logs:**
  - Configuraciones en `logger_config.py`. Directorios para logs son creados automáticamente en `./logs/`.
- **Métricas:**
  - Usa `MetricsCollector` para recolectar métricas, accesibles vía endpoints del dashboard.
  
## Uso del Dashboard

- **Iniciar el Dashboard:**
  Ejecutar `python -m monitoring.dashboard`.
- **URL:**
  Accede a `http://localhost:5001` para visualizar métricas y logs.
- **Auto-refresh:**
  Actualiza cada 30 segundos. Puedes desactivar esta opción manualmente.

## Futuras Mejoras

1. Integración con sistemas de monitoreo externos (Prometheus, Grafana).
2. Ampliar el soporte para múltiples tipos de alertas y respuestas más complejas.
3. Mecanismos avanzados de recuperación ante fallos.

## Conclusión

Este sistema está diseñado para ser escalable y mantener la integridad y monitoreo continuos en un entorno de producción. La arquitectura modular permite añadir funcionalidades sin grandes cambios estructurales.
