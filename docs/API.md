# Documentación de la API

## Visión General

Esta API REST proporciona endpoints para gestionar alertas MQTT, verificar hardware, empresas y sedes, y monitorear el estado del sistema.

## Base URL

```
http://localhost:5000
```

## Endpoints Principales

### 1. Salud del Sistema

#### GET /health

**Descripción:** Verifica el estado de salud del sistema.

**Respuesta:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-09T19:57:22.123456",
  "uptime": "1:23:45",
  "database": "connected",
  "mqtt": "connected"
}
```

**Códigos de Estado:**
- `200 OK` - Sistema funcionando correctamente
- `503 Service Unavailable` - Sistema degradado o no disponible

---

### 2. Verificación de Hardware

#### POST /verificar-hardware

**Descripción:** Verifica si un hardware específico existe en el sistema.

**Parámetros:**
```json
{
  "nombre": "string (requerido)"
}
```

**Respuesta Exitosa:**
```json
{
  "existe": true,
  "hardware": {
    "nombre": "Semaforo001",
    "tipo": "semaforo",
    "estado": "activo",
    "empresa": "empresa1",
    "sede": "principal"
  }
}
```

**Respuesta de Error:**
```json
{
  "existe": false,
  "mensaje": "Hardware no encontrado"
}
```

**Códigos de Estado:**
- `200 OK` - Hardware encontrado
- `404 Not Found` - Hardware no encontrado
- `400 Bad Request` - Parámetros inválidos

---

### 3. Verificación de Empresa

#### POST /verificar-empresa

**Descripción:** Verifica si una empresa específica existe y está activa.

**Parámetros:**
```json
{
  "nombre": "string (requerido)"
}
```

**Respuesta Exitosa:**
```json
{
  "existe": true,
  "empresa": {
    "nombre": "empresa1",
    "estado": "activo",
    "usuarios": [
      {
        "nombre": "Juan Pérez",
        "email": "juan@empresa1.com",
        "rol": "admin"
      }
    ]
  }
}
```

**Respuesta de Error:**
```json
{
  "existe": false,
  "mensaje": "Empresa no encontrada"
}
```

**Códigos de Estado:**
- `200 OK` - Empresa encontrada
- `404 Not Found` - Empresa no encontrada
- `400 Bad Request` - Parámetros inválidos

---

### 4. Verificación de Sede

#### POST /verificar-sede

**Descripción:** Verifica si una sede específica existe para una empresa.

**Parámetros:**
```json
{
  "empresa": "string (requerido)",
  "sede": "string (requerido)"
}
```

**Respuesta Exitosa:**
```json
{
  "existe": true,
  "sede": {
    "nombre": "principal",
    "empresa": "empresa1",
    "ubicacion": "Bogotá",
    "estado": "activo"
  }
}
```

**Respuesta de Error:**
```json
{
  "existe": false,
  "mensaje": "Sede no encontrada"
}
```

**Códigos de Estado:**
- `200 OK` - Sede encontrada
- `404 Not Found` - Sede no encontrada
- `400 Bad Request` - Parámetros inválidos

---

### 5. Prueba Completa

#### POST /prueba-completa

**Descripción:** Realiza una verificación completa del flujo de alertas.

**Parámetros:**
```json
{
  "empresa": "string (requerido)",
  "tipo_alerta": "string (requerido)",
  "sede": "string (requerido)",
  "nombre": "string (requerido)"
}
```

**Respuesta Exitosa:**
```json
{
  "mensaje": "Prueba completa exitosa",
  "resultado": {
    "hardware_existe": true,
    "empresa_existe": true,
    "sede_existe": true,
    "alerta_creada": true,
    "alerta_id": "60f7b3b4e1b2c3d4e5f6a7b8",
    "usuarios": [
      {
        "nombre": "Juan Pérez",
        "email": "juan@empresa1.com",
        "rol": "admin"
      }
    ]
  }
}
```

**Respuesta de Error:**
```json
{
  "mensaje": "Error en la prueba",
  "error": "Hardware no encontrado",
  "resultado": {
    "hardware_existe": false,
    "empresa_existe": false,
    "sede_existe": false,
    "alerta_creada": false
  }
}
```

**Códigos de Estado:**
- `200 OK` - Prueba exitosa
- `400 Bad Request` - Error en la verificación
- `500 Internal Server Error` - Error del servidor

---

## Endpoints de Monitoreo

### 1. Estado de Salud (Dashboard)

#### GET /api/health

**Descripción:** Obtiene el estado de salud detallado del sistema.

**Respuesta:**
```json
{
  "status": "healthy",
  "issues": [],
  "summary": {
    "uptime_seconds": 3600,
    "uptime_formatted": "1:00:00",
    "total_alerts": 150,
    "alerts_per_minute": 2.5,
    "response_time_stats": {
      "avg": 0.125,
      "min": 0.050,
      "max": 0.300,
      "count": 100
    },
    "counters": {
      "alerts_total": {"alerts_total": 150}
    },
    "timestamp": "2025-07-09T19:57:22.123456"
  }
}
```

### 2. Métricas del Sistema

#### GET /api/metrics

**Descripción:** Obtiene métricas detalladas del sistema.

**Respuesta:**
```json
{
  "uptime_seconds": 3600,
  "uptime_formatted": "1:00:00",
  "total_alerts": 150,
  "alerts_per_minute": 2.5,
  "response_time_stats": {
    "avg": 0.125,
    "min": 0.050,
    "max": 0.300,
    "count": 100
  },
  "counters": {
    "alerts_total": {"alerts_total": 150}
  },
  "timestamp": "2025-07-09T19:57:22.123456"
}
```

### 3. Alertas Recientes

#### GET /api/alerts/recent

**Descripción:** Obtiene las alertas más recientes del sistema.

**Respuesta:**
```json
{
  "alerts": [
    "2025-07-09 19:57:22,123 - mqtt_alerts - INFO - Alert created - Data: {...}",
    "2025-07-09 19:56:45,456 - mqtt_alerts - INFO - Alert created - Data: {...}"
  ]
}
```

### 4. Logs del Sistema

#### GET /api/logs/{log_type}

**Descripción:** Obtiene logs específicos del sistema.

**Parámetros de Ruta:**
- `log_type`: `system` | `alerts` | `errors` | `metrics`

**Respuesta:**
```json
{
  "logs": [
    "2025-07-09 19:57:22,123 - mqtt_system - INFO - MQTT received - Topic: alerts/mqtt - Payload: {...}",
    "2025-07-09 19:56:45,456 - mqtt_system - INFO - Processing alert for empresa1"
  ]
}
```

---

## Estructura de Mensajes MQTT

### Formato de Mensaje

```json
{
  "empresa_nombre": {
    "tipo_alerta": {
      "sede": "nombre_sede",
      "alerta": "tipo_alerta",
      "nombre": "nombre_hardware",
      "otros_campos": "opcional"
    }
  }
}
```

### Ejemplo de Mensaje Válido

```json
{
  "empresa1": {
    "semaforo": {
      "sede": "principal",
      "alerta": "amarilla",
      "ubicacion": "Cruce principal",
      "nombre": "Semaforo001",
      "hardware_id": "SEM001",
      "coordenadas": {
        "lat": 4.6097,
        "lng": -74.0817
      },
      "timestamp": "2025-07-09T19:57:22.123456"
    }
  }
}
```

### Campos Requeridos

- `empresa_nombre`: Nombre de la empresa
- `tipo_alerta`: Tipo de alerta (semaforo, alarma, etc.)
- `sede`: Nombre de la sede
- `nombre`: Nombre del hardware (OBLIGATORIO)

### Campos Opcionales

- `alerta`: Tipo específico de alerta
- `ubicacion`: Ubicación textual
- `hardware_id`: ID único del hardware
- `coordenadas`: Coordenadas GPS
- `timestamp`: Marca de tiempo
- Cualquier otro campo adicional

---

## Flujo de Verificación

### 1. Verificación Prioritaria

1. **Hardware**: Se verifica primero si el hardware existe
2. **Empresa**: Si el hardware existe, se verifica la empresa
3. **Sede**: Si la empresa existe, se verifica la sede

### 2. Estados de Alerta

- **Autorizado**: `true` si todas las verificaciones son exitosas
- **Estado Activo**: `true` si el hardware existe (independientemente de empresa/sede)

### 3. Respuestas del Sistema

```json
{
  "autorizado": true,
  "estado_activo": true,
  "usuarios": [
    {
      "nombre": "Juan Pérez",
      "email": "juan@empresa1.com",
      "rol": "admin"
    }
  ],
  "data": {
    "hardware_nombre": "Semaforo001",
    "empresa": "empresa1",
    "sede": "principal",
    "tipo_alerta": "semaforo",
    "ubicacion": "Cruce principal",
    "coordenadas": {
      "lat": 4.6097,
      "lng": -74.0817
    }
  }
}
```

---

## Códigos de Error

### HTTP Status Codes

- `200 OK` - Solicitud exitosa
- `400 Bad Request` - Parámetros inválidos
- `404 Not Found` - Recurso no encontrado
- `500 Internal Server Error` - Error del servidor
- `503 Service Unavailable` - Servicio no disponible

### Códigos de Error Específicos

```json
{
  "error": "HARDWARE_NOT_FOUND",
  "message": "Hardware no encontrado",
  "code": 404
}
```

```json
{
  "error": "EMPRESA_NOT_FOUND",
  "message": "Empresa no encontrada",
  "code": 404
}
```

```json
{
  "error": "SEDE_NOT_FOUND",
  "message": "Sede no encontrada",
  "code": 404
}
```

---

## Límites y Restricciones

### Rate Limiting

- Máximo 100 requests por minuto por IP
- Máximo 1000 requests por hora por IP

### Tamaño de Payload

- Máximo 1MB por mensaje MQTT
- Máximo 10MB por request HTTP

### Timeouts

- Timeout de conexión: 30 segundos
- Timeout de lectura: 60 segundos
- Timeout de base de datos: 10 segundos

---

## Autenticación y Seguridad

### Autenticación MQTT

```bash
# Usuario/contraseña para MQTT
usuario: mqtt_user
contraseña: configurada_en_mosquitto
```

### Headers de Seguridad

```http
Content-Type: application/json
X-API-Version: 1.0
```

### Validación de Datos

- Todos los campos `nombre` son requeridos
- Longitud máxima de campos: 255 caracteres
- Caracteres especiales permitidos: `a-zA-Z0-9_-`

---

## Ejemplos de Uso

### Verificar Hardware con cURL

```bash
curl -X POST http://localhost:5000/verificar-hardware \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Semaforo001"}'
```

### Enviar Mensaje MQTT

```bash
mosquitto_pub -h localhost -t alerts/mqtt -m '{
  "empresa1": {
    "semaforo": {
      "sede": "principal",
      "alerta": "amarilla",
      "nombre": "Semaforo001",
      "ubicacion": "Cruce principal"
    }
  }
}'
```

### Verificar Salud del Sistema

```bash
curl http://localhost:5000/health
```

---

## Changelog

### v1.0.0
- API inicial con endpoints básicos
- Soporte para verificación de hardware, empresa y sede
- Sistema de monitoreo integrado
- Dashboard web para visualización
