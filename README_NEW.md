# 🚨 Sistema MQTT de Alertas - ECOES

## 📋 Descripción

Sistema escalable de alertas MQTT para gestión de hardware, empresas y sedes. Incluye verificación prioritaria por hardware, backend REST, monitoreo en tiempo real y dashboard web.

## 🏗️ Arquitectura

```
📊 Dashboard Web (Flask)     🔄 Cliente MQTT
         ↓                           ↓
📡 Backend REST (Flask)  ←→  📨 Broker MQTT
         ↓                           ↓
🗄️ MongoDB (AlertasMQTT)   📋 Logs & Métricas
```

## 🚀 Inicio Rápido

### 1. Configuración Inicial
```bash
# Clonar y configurar
git clone <repository>
cd MqttConnection

# Instalar dependencias
pip install -r requirements.txt

# Configurar base de datos
./scripts/backend_utils.sh setup

# Iniciar sistema completo
python start_system.py
```

### 2. Acceso al Sistema
- **Backend API**: http://localhost:5000
- **Dashboard**: http://localhost:5001
- **Documentación**: [docs/](docs/)

## 📚 Documentación Completa

### 📖 Guías Principales
- **[Guía de Endpoints](docs/BACKEND_ENDPOINTS.md)** - Documentación detallada de todos los endpoints con ejemplos curl
- **[Instalación y Configuración](docs/INSTALLATION.md)** - Setup completo paso a paso
- **[Documentación de API](docs/API.md)** - Referencia técnica de la API
- **[README General](docs/README.md)** - Visión general del sistema

### 🔧 Herramientas
- **[Scripts de Utilidad](scripts/backend_utils.sh)** - Herramientas para gestión del backend
- **[Script de Inicio](start_system.py)** - Inicio automático del sistema completo

## 🛠️ Uso del Sistema

### Verificar Estado del Sistema
```bash
# Usando scripts de utilidad
./scripts/backend_utils.sh health

# Usando curl directamente
curl http://localhost:5000/health
```

### Gestión de Hardware
```bash
# Agregar hardware interactivamente
./scripts/backend_utils.sh add-hardware

# Listar hardware existente
./scripts/backend_utils.sh list-hardware

# Verificar hardware específico
curl -X POST http://localhost:5000/verificar-hardware \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Semaforo001"}'
```

### Gestión de Empresas
```bash
# Agregar empresa interactivamente
./scripts/backend_utils.sh add-empresa

# Verificar empresa
curl -X POST http://localhost:5000/verificar-empresa \
  -H "Content-Type: application/json" \
  -d '{"nombre": "empresa1"}'
```

### Gestión de Sedes
```bash
# Agregar sede interactivamente
./scripts/backend_utils.sh add-sede

# Verificar sede
curl -X POST http://localhost:5000/verificar-sede \
  -H "Content-Type: application/json" \
  -d '{"empresa": "empresa1", "sede": "principal"}'
```

### Pruebas y Monitoreo
```bash
# Ejecutar prueba completa
./scripts/backend_utils.sh test-complete

# Monitoreo continuo
./scripts/backend_utils.sh monitor

# Estadísticas del sistema
./scripts/backend_utils.sh stats

# Diagnóstico completo
./scripts/backend_utils.sh diagnose
```

## 📊 Endpoints Principales

### 🔍 Verificación
- `GET /health` - Estado del sistema
- `POST /verificar-hardware` - Verificar hardware
- `POST /verificar-empresa` - Verificar empresa
- `POST /verificar-sede` - Verificar sede
- `POST /prueba-completa` - Prueba completa del flujo

### 📊 Monitoreo
- `GET /api/health` - Estado detallado
- `GET /api/metrics` - Métricas del sistema
- `GET /api/alerts/recent` - Alertas recientes
- `GET /api/logs/{tipo}` - Logs del sistema

## 🗄️ Estructura de Datos

### Hardware
```json
{
  "nombre": "Semaforo001",
  "tipo": "semaforo",
  "estado": "activo",
  "empresa": "empresa1",
  "sede": "principal",
  "ubicacion": "Cruce principal",
  "coordenadas": {"lat": 4.6097, "lng": -74.0817}
}
```

### Empresa
```json
{
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
```

### Sede
```json
{
  "nombre": "principal",
  "empresa": "empresa1",
  "ubicacion": "Bogotá",
  "estado": "activo"
}
```

## 🔄 Flujo de Alertas MQTT

### 1. Estructura de Mensaje
```json
{
  "empresa1": {
    "semaforo": {
      "sede": "principal",
      "alerta": "amarilla",
      "nombre": "Semaforo001",
      "ubicacion": "Cruce principal"
    }
  }
}
```

### 2. Flujo de Verificación
1. **Hardware** - Verificación prioritaria
2. **Empresa** - Si hardware existe
3. **Sede** - Si empresa existe
4. **Procesamiento** - Guardar alerta y notificar

### 3. Respuesta del Sistema
```json
{
  "autorizado": true,
  "estado_activo": true,
  "usuarios": [...],
  "data": {...}
}
```

## 🔧 Herramientas de Utilidad

### Script Principal
```bash
# Ver todas las opciones
./scripts/backend_utils.sh help

# Opciones principales
./scripts/backend_utils.sh health          # Estado del sistema
./scripts/backend_utils.sh test-complete  # Prueba completa
./scripts/backend_utils.sh monitor        # Monitoreo continuo
./scripts/backend_utils.sh setup          # Configuración inicial
```

### Comandos Útiles
```bash
# Verificar sistema completo
./scripts/backend_utils.sh diagnose

# Ver logs en tiempo real
./scripts/backend_utils.sh logs system

# Estadísticas detalladas
./scripts/backend_utils.sh stats

# Configurar datos de ejemplo
./scripts/backend_utils.sh setup
```

## 🚨 Solución de Problemas

### Problemas Comunes
1. **Backend no responde** - Verificar que MongoDB esté corriendo
2. **Hardware no encontrado** - Agregar hardware a la base de datos
3. **Empresa no encontrada** - Crear empresa con usuarios
4. **Sede no encontrada** - Agregar sede a la empresa

### Diagnóstico
```bash
# Diagnóstico completo
./scripts/backend_utils.sh diagnose

# Verificar servicios
sudo systemctl status mongod
sudo systemctl status mosquitto

# Verificar puertos
netstat -tlnp | grep -E ":(5000|5001|1883|27017)"
```

## 🔐 Configuración de Seguridad

### MongoDB
```bash
# Configurar autenticación
mongo
use admin
db.createUser({
  user: "admin",
  pwd: "password",
  roles: ["userAdminAnyDatabase"]
})
```

### MQTT
```bash
# Configurar autenticación Mosquitto
sudo mosquitto_passwd -c /etc/mosquitto/passwd mqtt_user
```

## 📈 Monitoreo y Métricas

### Dashboard Web
- **URL**: http://localhost:5001
- **Métricas**: Tiempo real, alertas/minuto, uptime
- **Logs**: Sistema, alertas, errores
- **Estado**: Salud del sistema con códigos de color

### Métricas Clave
- Total de alertas procesadas
- Promedio de alertas por minuto
- Tiempo de respuesta del sistema
- Estado de conexiones (DB, MQTT)

## 🔄 Desarrollo y Contribución

### Estructura del Proyecto
```
MqttConnection/
├── core/           # Aplicación principal
├── clients/        # Clientes MQTT y backend
├── handlers/       # Manejadores de mensajes
├── config/         # Configuración
├── monitoring/     # Sistema de monitoreo
├── scripts/        # Scripts de utilidad
└── docs/          # Documentación
```

### Extensibilidad
- Agregar nuevos tipos de hardware
- Implementar nuevos endpoints
- Personalizar sistema de notificaciones
- Integrar con sistemas externos

## 📞 Soporte

### Documentación
- [Guía Completa de Endpoints](docs/BACKEND_ENDPOINTS.md)
- [Instalación Detallada](docs/INSTALLATION.md)
- [API Reference](docs/API.md)

### Logs y Debugging
```bash
# Logs del sistema
tail -f logs/mqtt/system.log

# Logs de errores
tail -f logs/errors/errors.log

# Logs de alertas
tail -f logs/alerts/alerts.log
```

---

## 🎯 Funcionalidades Principales

✅ **Verificación Prioritaria por Hardware**  
✅ **Backend REST con Endpoints Completos**  
✅ **Sistema de Monitoreo en Tiempo Real**  
✅ **Dashboard Web Interactivo**  
✅ **Logging y Métricas Detalladas**  
✅ **Scripts de Utilidad Automatizados**  
✅ **Documentación Completa**  
✅ **Configuración de Producción**  

---

*Sistema desarrollado para ECOES - Gestión eficiente de alertas MQTT*
