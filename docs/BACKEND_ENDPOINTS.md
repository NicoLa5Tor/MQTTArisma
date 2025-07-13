# 🔧 Backend MQTT - Guía Completa de Endpoints

## 📋 Índice
1. [Información General](#información-general)
2. [Endpoints Principales](#endpoints-principales)
3. [Endpoints de Monitoreo](#endpoints-de-monitoreo)
4. [Gestión de Datos](#gestión-de-datos)
5. [Ejemplos Prácticos](#ejemplos-prácticos)
6. [Solución de Problemas](#solución-de-problemas)

---

## 🌐 Información General

### Base URL
```
http://localhost:5000
```

### Headers Comunes
```bash
Content-Type: application/json
Accept: application/json
```

### Códigos de Respuesta
- `200 OK` - Solicitud exitosa
- `201 Created` - Recurso creado exitosamente
- `400 Bad Request` - Datos inválidos
- `404 Not Found` - Recurso no encontrado
- `500 Internal Server Error` - Error del servidor

---

## 🚀 Endpoints Principales

### 1. 🏥 Health Check

**Verificar el estado del servidor**

```bash
curl -X GET http://localhost:5000/health
```

**Respuesta Exitosa:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-09T20:10:04.123456",
  "uptime": "2:15:30",
  "database": "connected",
  "mqtt": "connected",
  "version": "1.0.0"
}
```

**Ejemplo de Uso:**
```bash
# Verificar estado antes de usar otros endpoints
health_status=$(curl -s http://localhost:5000/health | jq -r '.status')
if [ "$health_status" = "healthy" ]; then
    echo "✅ Servidor disponible"
else
    echo "❌ Servidor no disponible"
fi
```

---

### 2. 🔍 Verificar Hardware

**Verificar si un hardware específico existe**

```bash
curl -X POST http://localhost:5000/verificar-hardware \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Semaforo001"
  }'
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
    "sede": "principal",
    "ubicacion": "Cruce principal",
    "coordenadas": {
      "lat": 4.6097,
      "lng": -74.0817
    },
    "fecha_instalacion": "2025-01-01T00:00:00",
    "ultima_actualizacion": "2025-07-09T20:10:04"
  }
}
```

**Respuesta Error:**
```json
{
  "existe": false,
  "mensaje": "Hardware no encontrado",
  "error_code": "HARDWARE_NOT_FOUND"
}
```

**Cómo Agregar Hardware:**
```bash
# Conectar a MongoDB directamente
mongo tu_base_de_datos

# Agregar nuevo hardware
db.hardware.insertOne({
  "nombre": "Semaforo002",
  "tipo": "semaforo",
  "estado": "activo",
  "empresa": "empresa1",
  "sede": "secundaria",
  "ubicacion": "Cruce secundario",
  "coordenadas": {
    "lat": 4.6100,
    "lng": -74.0820
  },
  "fecha_instalacion": new Date(),
  "ultima_actualizacion": new Date()
})
```

---

### 3. 🏢 Verificar Empresa

**Verificar si una empresa existe y está activa**

```bash
curl -X POST http://localhost:5000/verificar-empresa \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "empresa1"
  }'
```

**Respuesta Exitosa:**
```json
{
  "existe": true,
  "empresa": {
    "nombre": "empresa1",
    "estado": "activo",
    "fecha_creacion": "2025-01-01T00:00:00",
    "contacto": {
      "telefono": "+57 300 123 4567",
      "email": "admin@empresa1.com"
    },
    "usuarios": [
      {
        "nombre": "Juan Pérez",
        "email": "juan@empresa1.com",
        "rol": "admin",
        "telefono": "+57 300 111 2222"
      },
      {
        "nombre": "María García",
        "email": "maria@empresa1.com",
        "rol": "operador",
        "telefono": "+57 300 333 4444"
      }
    ],
    "configuracion": {
      "notificaciones_email": true,
      "notificaciones_sms": true,
      "alertas_criticas": true
    }
  }
}
```

**Cómo Agregar Empresa:**
```bash
# Conectar a MongoDB
mongo tu_base_de_datos

# Agregar nueva empresa
db.empresas.insertOne({
  "nombre": "empresa2",
  "estado": "activo",
  "fecha_creacion": new Date(),
  "contacto": {
    "telefono": "+57 300 555 6666",
    "email": "admin@empresa2.com"
  },
  "usuarios": [
    {
      "nombre": "Carlos López",
      "email": "carlos@empresa2.com",
      "rol": "admin",
      "telefono": "+57 300 777 8888"
    }
  ],
  "configuracion": {
    "notificaciones_email": true,
    "notificaciones_sms": false,
    "alertas_criticas": true
  }
})
```

**Modificar Empresa Existente:**
```bash
# Actualizar datos de contacto
db.empresas.updateOne(
  { "nombre": "empresa1" },
  { 
    $set: { 
      "contacto.telefono": "+57 300 999 0000",
      "ultima_actualizacion": new Date()
    }
  }
)

# Agregar nuevo usuario
db.empresas.updateOne(
  { "nombre": "empresa1" },
  { 
    $push: { 
      "usuarios": {
        "nombre": "Ana Rodríguez",
        "email": "ana@empresa1.com",
        "rol": "supervisor",
        "telefono": "+57 300 222 3333"
      }
    }
  }
)
```

---

### 4. 🏢 Verificar Sede

**Verificar si una sede existe para una empresa**

```bash
curl -X POST http://localhost:5000/verificar-sede \
  -H "Content-Type: application/json" \
  -d '{
    "empresa": "empresa1",
    "sede": "principal"
  }'
```

**Respuesta Exitosa:**
```json
{
  "existe": true,
  "sede": {
    "nombre": "principal",
    "empresa": "empresa1",
    "ubicacion": "Bogotá",
    "direccion": "Calle 123 #45-67",
    "estado": "activo",
    "coordenadas": {
      "lat": 4.6097,
      "lng": -74.0817
    },
    "responsables": [
      {
        "nombre": "Pedro Martínez",
        "cargo": "Jefe de Operaciones",
        "telefono": "+57 300 444 5555"
      }
    ],
    "horarios": {
      "apertura": "06:00",
      "cierre": "22:00",
      "dias_operacion": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado"]
    }
  }
}
```

**Cómo Agregar Sede:**
```bash
# Conectar a MongoDB
mongo tu_base_de_datos

# Agregar nueva sede
db.sedes.insertOne({
  "nombre": "secundaria",
  "empresa": "empresa1",
  "ubicacion": "Medellín",
  "direccion": "Carrera 50 #30-20",
  "estado": "activo",
  "coordenadas": {
    "lat": 6.2442,
    "lng": -75.5812
  },
  "responsables": [
    {
      "nombre": "Laura Gómez",
      "cargo": "Coordinadora",
      "telefono": "+57 300 666 7777"
    }
  ],
  "horarios": {
    "apertura": "07:00",
    "cierre": "21:00",
    "dias_operacion": ["lunes", "martes", "miércoles", "jueves", "viernes"]
  }
})
```

---

### 5. 🧪 Prueba Completa

**Ejecutar una prueba completa del flujo de alertas**

```bash
curl -X POST http://localhost:5000/prueba-completa \
  -H "Content-Type: application/json" \
  -d '{
    "empresa": "empresa1",
    "tipo_alerta": "semaforo",
    "sede": "principal",
    "nombre": "Semaforo001"
  }'
```

**Respuesta Exitosa:**
```json
{
  "mensaje": "Prueba completa exitosa",
  "timestamp": "2025-07-09T20:10:04.123456",
  "resultado": {
    "hardware_existe": true,
    "empresa_existe": true,
    "sede_existe": true,
    "alerta_creada": true,
    "alerta_id": "60f7b3b4e1b2c3d4e5f6a7b8",
    "tiempo_procesamiento": "0.245s",
    "usuarios_notificados": 2
  },
  "usuarios": [
    {
      "nombre": "Juan Pérez",
      "email": "juan@empresa1.com",
      "rol": "admin",
      "notificacion_enviada": true
    },
    {
      "nombre": "María García",
      "email": "maria@empresa1.com",
      "rol": "operador",
      "notificacion_enviada": true
    }
  ],
  "datos_procesados": {
    "hardware_nombre": "Semaforo001",
    "empresa": "empresa1",
    "sede": "principal",
    "tipo_alerta": "semaforo",
    "estado": "procesada",
    "prioridad": "normal"
  }
}
```

---

## 📊 Endpoints de Monitoreo

### 1. 📈 Estado del Sistema

```bash
curl -X GET http://localhost:5001/api/health
```

**Respuesta:**
```json
{
  "status": "healthy",
  "issues": [],
  "summary": {
    "uptime_seconds": 7200,
    "uptime_formatted": "2:00:00",
    "total_alerts": 1250,
    "alerts_per_minute": 3.2,
    "response_time_stats": {
      "avg": 0.125,
      "min": 0.050,
      "max": 0.450,
      "count": 1000
    }
  }
}
```

### 2. 📊 Métricas del Sistema

```bash
curl -X GET http://localhost:5001/api/metrics
```

### 3. 🚨 Alertas Recientes

```bash
curl -X GET http://localhost:5001/api/alerts/recent
```

### 4. 📋 Logs del Sistema

```bash
# Logs del sistema
curl -X GET http://localhost:5001/api/logs/system

# Logs de alertas
curl -X GET http://localhost:5001/api/logs/alerts

# Logs de errores
curl -X GET http://localhost:5001/api/logs/errors

# Logs de métricas
curl -X GET http://localhost:5001/api/logs/metrics
```

---

## 🛠️ Gestión de Datos

### 📋 Estructura de la Base de Datos

#### Colección `hardware`
```javascript
{
  "_id": ObjectId("..."),
  "nombre": "Semaforo001",          // REQUERIDO - Identificador único
  "tipo": "semaforo",               // semaforo, alarma, sensor, etc.
  "estado": "activo",               // activo, inactivo, mantenimiento
  "empresa": "empresa1",            // Empresa propietaria
  "sede": "principal",              // Sede donde está ubicado
  "ubicacion": "Cruce principal",   // Descripción de ubicación
  "coordenadas": {                  // Coordenadas GPS
    "lat": 4.6097,
    "lng": -74.0817
  },
  "fecha_instalacion": ISODate("2025-01-01T00:00:00Z"),
  "ultima_actualizacion": ISODate("2025-07-09T20:10:04Z"),
  "configuracion": {                // Configuración específica del hardware
    "modelo": "SEM-2025",
    "version_firmware": "1.2.3",
    "intervalo_reporte": 30
  }
}
```

#### Colección `empresas`
```javascript
{
  "_id": ObjectId("..."),
  "nombre": "empresa1",             // REQUERIDO - Identificador único
  "estado": "activo",               // activo, inactivo, suspendido
  "fecha_creacion": ISODate("2025-01-01T00:00:00Z"),
  "contacto": {
    "telefono": "+57 300 123 4567",
    "email": "admin@empresa1.com"
  },
  "usuarios": [                     // Lista de usuarios para notificaciones
    {
      "nombre": "Juan Pérez",
      "email": "juan@empresa1.com",
      "rol": "admin",               // admin, operador, supervisor
      "telefono": "+57 300 111 2222",
      "activo": true
    }
  ],
  "configuracion": {
    "notificaciones_email": true,
    "notificaciones_sms": true,
    "alertas_criticas": true,
    "zona_horaria": "America/Bogota"
  }
}
```

#### Colección `sedes`
```javascript
{
  "_id": ObjectId("..."),
  "nombre": "principal",            // REQUERIDO - Nombre de la sede
  "empresa": "empresa1",            // REQUERIDO - Empresa propietaria
  "ubicacion": "Bogotá",            // Ciudad o región
  "direccion": "Calle 123 #45-67",
  "estado": "activo",               // activo, inactivo, mantenimiento
  "coordenadas": {
    "lat": 4.6097,
    "lng": -74.0817
  },
  "responsables": [
    {
      "nombre": "Pedro Martínez",
      "cargo": "Jefe de Operaciones",
      "telefono": "+57 300 444 5555"
    }
  ],
  "horarios": {
    "apertura": "06:00",
    "cierre": "22:00",
    "dias_operacion": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado"]
  }
}
```

#### Colección `mqtt_alerts`
```javascript
{
  "_id": ObjectId("..."),
  "hardware_nombre": "Semaforo001", // REQUERIDO - Referencia al hardware
  "empresa": "empresa1",            // Empresa asociada
  "sede": "principal",              // Sede asociada
  "tipo_alerta": "semaforo",        // Tipo de alerta
  "alerta": "amarilla",             // Estado específico de la alerta
  "autorizado": true,               // Si está autorizado para procesar
  "estado_activo": true,            // Si el hardware está activo
  "timestamp": ISODate("2025-07-09T20:10:04Z"),
  "data": {                         // Datos adicionales del mensaje MQTT
    "ubicacion": "Cruce principal",
    "coordenadas": {
      "lat": 4.6097,
      "lng": -74.0817
    },
    "metadata": {
      "version": "1.0",
      "source": "mqtt"
    }
  },
  "procesado": true,                // Si fue procesado exitosamente
  "usuarios_notificados": 2,        // Cantidad de usuarios notificados
  "tiempo_procesamiento": 0.245     // Tiempo en segundos
}
```

### 📝 Comandos de Gestión

#### Agregar Hardware
```bash
# Script para agregar hardware masivamente
cat > agregar_hardware.js << 'EOF'
db.hardware.insertMany([
  {
    "nombre": "Semaforo002",
    "tipo": "semaforo",
    "estado": "activo",
    "empresa": "empresa1",
    "sede": "secundaria",
    "ubicacion": "Cruce norte",
    "coordenadas": {"lat": 4.6100, "lng": -74.0820},
    "fecha_instalacion": new Date(),
    "ultima_actualizacion": new Date()
  },
  {
    "nombre": "Alarma002",
    "tipo": "alarma",
    "estado": "activo",
    "empresa": "empresa1",
    "sede": "principal",
    "ubicacion": "Edificio principal",
    "coordenadas": {"lat": 4.6095, "lng": -74.0815},
    "fecha_instalacion": new Date(),
    "ultima_actualizacion": new Date()
  }
])
EOF

mongo tu_base_de_datos < agregar_hardware.js
```

#### Modificar Hardware
```bash
# Cambiar estado de hardware
db.hardware.updateOne(
  { "nombre": "Semaforo001" },
  { 
    $set: { 
      "estado": "mantenimiento",
      "ultima_actualizacion": new Date()
    }
  }
)

# Actualizar ubicación
db.hardware.updateOne(
  { "nombre": "Semaforo001" },
  { 
    $set: { 
      "ubicacion": "Cruce principal renovado",
      "coordenadas": {"lat": 4.6098, "lng": -74.0818},
      "ultima_actualizacion": new Date()
    }
  }
)
```

#### Eliminar Hardware
```bash
# Desactivar en lugar de eliminar (recomendado)
db.hardware.updateOne(
  { "nombre": "Semaforo001" },
  { 
    $set: { 
      "estado": "inactivo",
      "fecha_desactivacion": new Date()
    }
  }
)

# Eliminar permanentemente (use con cuidado)
db.hardware.deleteOne({ "nombre": "Semaforo001" })
```

#### Gestionar Usuarios de Empresa
```bash
# Agregar usuario a empresa
db.empresas.updateOne(
  { "nombre": "empresa1" },
  { 
    $push: { 
      "usuarios": {
        "nombre": "Nuevo Usuario",
        "email": "nuevo@empresa1.com",
        "rol": "operador",
        "telefono": "+57 300 888 9999",
        "activo": true,
        "fecha_creacion": new Date()
      }
    }
  }
)

# Desactivar usuario
db.empresas.updateOne(
  { "nombre": "empresa1", "usuarios.email": "usuario@empresa1.com" },
  { 
    $set: { 
      "usuarios.$.activo": false,
      "usuarios.$.fecha_desactivacion": new Date()
    }
  }
)

# Cambiar rol de usuario
db.empresas.updateOne(
  { "nombre": "empresa1", "usuarios.email": "usuario@empresa1.com" },
  { 
    $set: { 
      "usuarios.$.rol": "supervisor",
      "usuarios.$.fecha_actualizacion": new Date()
    }
  }
)
```

### 📊 Consultas Útiles

#### Estadísticas de Hardware
```bash
# Contar hardware por tipo
db.hardware.aggregate([
  { $group: { _id: "$tipo", count: { $sum: 1 } } }
])

# Hardware por empresa
db.hardware.aggregate([
  { $group: { _id: "$empresa", count: { $sum: 1 } } }
])

# Hardware activo vs inactivo
db.hardware.aggregate([
  { $group: { _id: "$estado", count: { $sum: 1 } } }
])
```

#### Estadísticas de Alertas
```bash
# Alertas de los últimos 7 días
db.mqtt_alerts.find({
  "timestamp": { 
    $gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) 
  }
}).count()

# Alertas por empresa
db.mqtt_alerts.aggregate([
  { $group: { _id: "$empresa", count: { $sum: 1 } } }
])

# Alertas por tipo
db.mqtt_alerts.aggregate([
  { $group: { _id: "$tipo_alerta", count: { $sum: 1 } } }
])
```

---

## 🔧 Ejemplos Prácticos

### 1. 🚀 Configuración Inicial Completa

```bash
#!/bin/bash
# Script de configuración inicial

echo "🔧 Configurando sistema MQTT..."

# 1. Verificar que el servidor esté disponible
echo "1. Verificando servidor..."
curl -f http://localhost:5000/health || exit 1

# 2. Agregar hardware de prueba
echo "2. Agregando hardware de prueba..."
curl -X POST http://localhost:5000/verificar-hardware \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Semaforo001"}' | jq .

# 3. Verificar empresa
echo "3. Verificando empresa..."
curl -X POST http://localhost:5000/verificar-empresa \
  -H "Content-Type: application/json" \
  -d '{"nombre": "empresa1"}' | jq .

# 4. Verificar sede
echo "4. Verificando sede..."
curl -X POST http://localhost:5000/verificar-sede \
  -H "Content-Type: application/json" \
  -d '{"empresa": "empresa1", "sede": "principal"}' | jq .

# 5. Ejecutar prueba completa
echo "5. Ejecutando prueba completa..."
curl -X POST http://localhost:5000/prueba-completa \
  -H "Content-Type: application/json" \
  -d '{
    "empresa": "empresa1",
    "tipo_alerta": "semaforo",
    "sede": "principal",
    "nombre": "Semaforo001"
  }' | jq .

echo "✅ Configuración completa"
```

### 2. 📊 Monitoreo Continuo

```bash
#!/bin/bash
# Script de monitoreo continuo

while true; do
  echo "=== $(date) ==="
  
  # Estado del sistema
  health=$(curl -s http://localhost:5000/health | jq -r '.status')
  echo "Estado: $health"
  
  # Métricas del dashboard
  metrics=$(curl -s http://localhost:5001/api/metrics)
  total_alerts=$(echo $metrics | jq -r '.total_alerts')
  alerts_per_min=$(echo $metrics | jq -r '.alerts_per_minute')
  
  echo "Total alertas: $total_alerts"
  echo "Alertas/min: $alerts_per_min"
  
  # Esperar 30 segundos
  sleep 30
done
```

### 3. 🔄 Procesamiento de Alertas Batch

```bash
#!/bin/bash
# Procesar múltiples alertas

alertas=(
  '{"empresa": "empresa1", "tipo_alerta": "semaforo", "sede": "principal", "nombre": "Semaforo001"}'
  '{"empresa": "empresa1", "tipo_alerta": "alarma", "sede": "principal", "nombre": "Alarma001"}'
  '{"empresa": "empresa1", "tipo_alerta": "semaforo", "sede": "secundaria", "nombre": "Semaforo002"}'
)

for alerta in "${alertas[@]}"; do
  echo "Procesando: $alerta"
  
  response=$(curl -s -X POST http://localhost:5000/prueba-completa \
    -H "Content-Type: application/json" \
    -d "$alerta")
  
  success=$(echo $response | jq -r '.resultado.alerta_creada')
  
  if [ "$success" = "true" ]; then
    echo "✅ Alerta procesada exitosamente"
  else
    echo "❌ Error procesando alerta"
    echo $response | jq .
  fi
  
  sleep 1
done
```

### 4. 📈 Reporte de Estadísticas

```bash
#!/bin/bash
# Generar reporte de estadísticas

echo "📊 REPORTE DE ESTADÍSTICAS MQTT"
echo "================================"

# Métricas generales
metrics=$(curl -s http://localhost:5001/api/metrics)
echo "Uptime: $(echo $metrics | jq -r '.uptime_formatted')"
echo "Total alertas: $(echo $metrics | jq -r '.total_alerts')"
echo "Alertas/minuto: $(echo $metrics | jq -r '.alerts_per_minute')"

# Tiempo de respuesta
response_stats=$(echo $metrics | jq -r '.response_time_stats')
echo "Tiempo respuesta promedio: $(echo $response_stats | jq -r '.avg')s"
echo "Tiempo respuesta mínimo: $(echo $response_stats | jq -r '.min')s"
echo "Tiempo respuesta máximo: $(echo $response_stats | jq -r '.max')s"

# Estado del sistema
health=$(curl -s http://localhost:5001/api/health)
status=$(echo $health | jq -r '.status')
echo "Estado del sistema: $status"

if [ "$status" != "healthy" ]; then
  echo "⚠️  Problemas detectados:"
  echo $health | jq -r '.issues[]'
fi
```

---

## 🛠️ Solución de Problemas

### 1. ❌ Error: "Hardware no encontrado"

**Problema:**
```json
{
  "existe": false,
  "mensaje": "Hardware no encontrado"
}
```

**Solución:**
```bash
# 1. Verificar que el hardware existe en la base de datos
mongo tu_base_de_datos
db.hardware.find({"nombre": "Semaforo001"})

# 2. Si no existe, agregarlo
db.hardware.insertOne({
  "nombre": "Semaforo001",
  "tipo": "semaforo",
  "estado": "activo",
  "empresa": "empresa1",
  "sede": "principal",
  "ubicacion": "Cruce principal",
  "fecha_instalacion": new Date(),
  "ultima_actualizacion": new Date()
})

# 3. Verificar nuevamente
curl -X POST http://localhost:5000/verificar-hardware \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Semaforo001"}'
```

### 2. ❌ Error: "Empresa no encontrada"

**Problema:**
```json
{
  "existe": false,
  "mensaje": "Empresa no encontrada"
}
```

**Solución:**
```bash
# Agregar empresa
mongo tu_base_de_datos
db.empresas.insertOne({
  "nombre": "empresa1",
  "estado": "activo",
  "fecha_creacion": new Date(),
  "usuarios": [
    {
      "nombre": "Admin",
      "email": "admin@empresa1.com",
      "rol": "admin",
      "telefono": "+57 300 123 4567"
    }
  ]
})
```

### 3. ❌ Error: "Sede no encontrada"

**Problema:**
```json
{
  "existe": false,
  "mensaje": "Sede no encontrada"
}
```

**Solución:**
```bash
# Agregar sede
mongo tu_base_de_datos
db.sedes.insertOne({
  "nombre": "principal",
  "empresa": "empresa1",
  "ubicacion": "Bogotá",
  "estado": "activo"
})
```

### 4. ❌ Error: Servidor no responde

**Problema:**
```bash
curl: (7) Failed to connect to localhost port 5000
```

**Solución:**
```bash
# 1. Verificar que el servidor esté corriendo
ps aux | grep python

# 2. Verificar puertos disponibles
netstat -tlnp | grep :5000

# 3. Reiniciar el servidor
python start_system.py

# 4. Verificar logs
tail -f logs/mqtt/system.log
```

### 5. ❌ Error: Base de datos no conecta

**Problema:**
```json
{
  "status": "unhealthy",
  "database": "disconnected"
}
```

**Solución:**
```bash
# 1. Verificar que MongoDB esté corriendo
sudo systemctl status mongod

# 2. Iniciar MongoDB si no está corriendo
sudo systemctl start mongod

# 3. Verificar conexión
mongo --eval "db.runCommand('ping')"

# 4. Verificar configuración
grep -r "mongodb://" config/
```

### 6. 🔧 Comandos de Diagnóstico

```bash
#!/bin/bash
# Script de diagnóstico completo

echo "🔍 DIAGNÓSTICO DEL SISTEMA"
echo "=========================="

# 1. Verificar servicios
echo "1. Verificando servicios..."
sudo systemctl status mongod | grep Active
sudo systemctl status mosquitto | grep Active

# 2. Verificar puertos
echo "2. Verificando puertos..."
netstat -tlnp | grep -E ":(5000|5001|1883|27017)"

# 3. Verificar conectividad
echo "3. Verificando conectividad..."
curl -f http://localhost:5000/health && echo "✅ Backend OK" || echo "❌ Backend Error"
curl -f http://localhost:5001/api/health && echo "✅ Dashboard OK" || echo "❌ Dashboard Error"

# 4. Verificar base de datos
echo "4. Verificando base de datos..."
mongo --quiet --eval "
  db.hardware.count() > 0 && print('✅ Hardware: ' + db.hardware.count() + ' registros') || print('❌ No hay hardware');
  db.empresas.count() > 0 && print('✅ Empresas: ' + db.empresas.count() + ' registros') || print('❌ No hay empresas');
  db.sedes.count() > 0 && print('✅ Sedes: ' + db.sedes.count() + ' registros') || print('❌ No hay sedes');
" tu_base_de_datos

# 5. Verificar logs recientes
echo "5. Verificando logs recientes..."
if [ -f "logs/errors/errors.log" ]; then
  echo "Últimos errores:"
  tail -n 5 logs/errors/errors.log
else
  echo "✅ No hay logs de errores"
fi

echo "=========================="
echo "✅ Diagnóstico completado"
```

---

## 📚 Recursos Adicionales

### 🔗 Enlaces Útiles
- Dashboard de Monitoreo: http://localhost:5001
- API Backend: http://localhost:5000
- Documentación de API: [API.md](API.md)
- Guía de Instalación: [INSTALLATION.md](INSTALLATION.md)

### 📧 Contacto
Para soporte adicional o reportar problemas, consulta los logs del sistema o contacta al equipo de desarrollo.

---

*Última actualización: 2025-07-09*
