# Guía de Instalación y Configuración

## Requisitos del Sistema

- Python 3.8 o superior
- MongoDB 4.4 o superior
- Broker MQTT (como Mosquitto)

## Dependencias de Python

```bash
pip install pymongo flask paho-mqtt python-dateutil
```

## Configuración del Entorno

### 1. Base de Datos MongoDB

```bash
# Iniciar MongoDB
sudo systemctl start mongod

# Crear base de datos y colecciones
mongo
use tu_base_de_datos
db.createCollection("hardware")
db.createCollection("empresas")
db.createCollection("sedes")
db.createCollection("mqtt_alerts")
```

### 2. Broker MQTT

```bash
# Instalar Mosquitto
sudo apt-get install mosquitto mosquitto-clients

# Iniciar el broker
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

### 3. Configuración del Sistema

1. **Configurar variables de entorno:**

```bash
export MONGODB_URI="mongodb://localhost:27017/tu_base_de_datos"
export MQTT_BROKER="localhost"
export MQTT_PORT=1883
export MQTT_TOPIC="alerts/mqtt"
```

2. **Configurar logging:**

Los logs se crean automáticamente en el directorio `logs/`:
- `logs/mqtt/system.log` - Logs del sistema MQTT
- `logs/alerts/alerts.log` - Logs de alertas
- `logs/errors/errors.log` - Logs de errores
- `logs/metrics.log` - Métricas del sistema

## Inicialización del Sistema

### 1. Estructura de Datos

Crear documentos de ejemplo en MongoDB:

```javascript
// Hardware
db.hardware.insertMany([
  {
    "nombre": "Semaforo001",
    "tipo": "semaforo",
    "estado": "activo",
    "empresa": "empresa1",
    "sede": "principal"
  },
  {
    "nombre": "Alarma001",
    "tipo": "alarma",
    "estado": "activo",
    "empresa": "empresa1",
    "sede": "principal"
  }
]);

// Empresas
db.empresas.insertMany([
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
]);

// Sedes
db.sedes.insertMany([
  {
    "nombre": "principal",
    "empresa": "empresa1",
    "ubicacion": "Bogotá",
    "estado": "activo"
  }
]);
```

### 2. Iniciar los Servicios

```bash
# 1. Iniciar el servidor MQTT (en una terminal)
python servidor_mqtt.py

# 2. Iniciar el dashboard de monitoreo (en otra terminal)
python -m monitoring.dashboard

# 3. Probar el sistema (en otra terminal)
python ejemplo_uso.py
```

## Verificación de la Instalación

### 1. Verificar el Dashboard

Accede a `http://localhost:5001` para ver el dashboard de monitoreo.

### 2. Probar los Endpoints

```bash
# Verificar salud del sistema
curl http://localhost:5000/health

# Verificar hardware
curl -X POST http://localhost:5000/verificar-hardware \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Semaforo001"}'

# Verificar empresa
curl -X POST http://localhost:5000/verificar-empresa \
  -H "Content-Type: application/json" \
  -d '{"nombre": "empresa1"}'

# Verificar sede
curl -X POST http://localhost:5000/verificar-sede \
  -H "Content-Type: application/json" \
  -d '{"empresa": "empresa1", "sede": "principal"}'
```

### 3. Enviar Mensaje MQTT de Prueba

```bash
# Usar mosquitto_pub para enviar un mensaje de prueba
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

## Solución de Problemas

### Problema: MongoDB no se conecta

**Solución:**
```bash
# Verificar estado de MongoDB
sudo systemctl status mongod

# Verificar logs
tail -f /var/log/mongodb/mongod.log

# Reiniciar si es necesario
sudo systemctl restart mongod
```

### Problema: Broker MQTT no responde

**Solución:**
```bash
# Verificar estado de Mosquitto
sudo systemctl status mosquitto

# Verificar configuración
sudo nano /etc/mosquitto/mosquitto.conf

# Reiniciar servicio
sudo systemctl restart mosquitto
```

### Problema: Logs no se crean

**Solución:**
```bash
# Verificar permisos de escritura
ls -la logs/

# Crear directorios manualmente si es necesario
mkdir -p logs/{mqtt,alerts,errors}
chmod 755 logs/
```

## Configuración de Producción

### 1. Supervisor para Procesos

```bash
# Instalar supervisor
sudo apt-get install supervisor

# Crear configuración
sudo nano /etc/supervisor/conf.d/mqtt-system.conf
```

Contenido del archivo:
```ini
[program:mqtt-server]
command=python /ruta/completa/servidor_mqtt.py
directory=/ruta/completa/
user=tu_usuario
autostart=true
autorestart=true
stderr_logfile=/var/log/mqtt-server.err.log
stdout_logfile=/var/log/mqtt-server.out.log

[program:mqtt-dashboard]
command=python -m monitoring.dashboard
directory=/ruta/completa/
user=tu_usuario
autostart=true
autorestart=true
stderr_logfile=/var/log/mqtt-dashboard.err.log
stdout_logfile=/var/log/mqtt-dashboard.out.log
```

### 2. Nginx para el Dashboard

```bash
# Instalar nginx
sudo apt-get install nginx

# Configurar proxy reverso
sudo nano /etc/nginx/sites-available/mqtt-dashboard
```

Contenido del archivo:
```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Activar configuración
sudo ln -s /etc/nginx/sites-available/mqtt-dashboard /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

## Configuración de Seguridad

### 1. Firewall

```bash
# Permitir solo puertos necesarios
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 1883/tcp    # MQTT
sudo ufw allow 27017/tcp   # MongoDB (solo si es necesario)

sudo ufw enable
```

### 2. Autenticación MQTT

Configurar autenticación en Mosquitto:

```bash
# Crear usuario para MQTT
sudo mosquitto_passwd -c /etc/mosquitto/passwd usuario_mqtt

# Configurar mosquitto
sudo nano /etc/mosquitto/mosquitto.conf
```

Agregar:
```
allow_anonymous false
password_file /etc/mosquitto/passwd
```

### 3. SSL/TLS

Para producción, configurar certificados SSL tanto para el dashboard como para MQTT.

## Mantenimiento

### 1. Rotación de Logs

Los logs se rotan automáticamente (10MB máximo, 5 backups).

### 2. Limpieza de Base de Datos

```bash
# Script para limpiar alertas antiguas (más de 30 días)
mongo tu_base_de_datos --eval "
  db.mqtt_alerts.deleteMany({
    'timestamp': {
      \$lt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
    }
  })
"
```

### 3. Monitoreo de Salud

El sistema incluye endpoints de salud en:
- `http://localhost:5000/health` - Backend
- `http://localhost:5001/api/health` - Dashboard

## Contacto y Soporte

Para problemas o dudas, consulta los logs del sistema o contacta al equipo de desarrollo.
