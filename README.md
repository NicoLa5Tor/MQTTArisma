# Sistema WebSocket y MQTT Unificado

Sistema unificado para manejar servicios WebSocket y MQTT con procesamiento de mensajes de WhatsApp y backend, utilizando configuración centralizada.

## Estructura del Proyecto

```
MqttConnection/
├── config/                 # Configuraciones
│   ├── __init__.py
│   ├── settings.py        # Configuraciones principales
│   └── env_config.py      # Configuración por variables de entorno
├── clients/               # Clientes de comunicación
│   ├── __init__.py
│   ├── mqtt_client.py     # Cliente MQTT
│   ├── websocket_receiver.py  # Cliente WebSocket
│   └── backend_client.py  # Cliente Backend HTTP
├── handlers/              # Manejadores de mensajes
│   ├── __init__.py
│   └── message_handler.py # Procesamiento de mensajes
├── core/                  # Aplicación principal
│   ├── __init__.py
│   └── app.py            # Aplicación principal
├── utils/                 # Utilidades
│   ├── __init__.py
│   ├── logger.py         # Configuración de logging
│   └── constants.py      # Constantes
├── main.py               # Punto de entrada
├── requirements.txt      # Dependencias
└── README.md            # Esta documentación
```

## Características

### 🚀 Escalabilidad
- Arquitectura modular con separación de responsabilidades
- Soporte para múltiples empresas dinámicamente
- Manejo de diferentes tipos de mensajes

### 🔌 Conectividad
- **MQTT**: Suscripción únicamente al topic `empresas`
- **WebSocket**: Receptor de mensajes JSON
- **Backend HTTP**: Cliente con reintentos automáticos

### 📊 Monitoreo
- Logging estructurado
- Estadísticas en tiempo real
- Manejo de errores robusto

## Instalación

1. Clona el repositorio:
```bash
git clone <url-del-repo>
cd MqttConnection
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Configura las variables de entorno (opcional):
```bash
export MQTT_BROKER=161.35.239.177
export MQTT_PORT=17090
export MQTT_USERNAME=tocancipa
export MQTT_PASSWORD=B0mb3r0s
export BACKEND_URL=http://localhost:8000
export WEBSOCKET_URL=ws://localhost:8080/ws
export LOG_LEVEL=INFO
```

## Uso

### Ejecución básica:
```bash
python main.py
```

### Importar como módulo:
```python
from config import AppConfig
from core import ScalableMQTTApp

config = AppConfig()
app = ScalableMQTTApp(config)
app.run()
```

### Configuración personalizada:
```python
from config import load_config_from_env
from core import ScalableMQTTApp

# Cargar desde variables de entorno
config = load_config_from_env()
app = ScalableMQTTApp(config)
app.run()
```

## Tipos de Mensajes Soportados

### 1. Semáforos
```json
{
  "tipo_mensaje": "semaforos",
  "tipo_alarma": "AZUL",
  "empresa": "cota"
}
```

### 2. Alarmas
```json
{
  "tipo_mensaje": "alarmas",
  "tipo_alarma": "CRITICA",
  "descripcion": "Fallo en sistema"
}
```

### 3. Estado
```json
{
  "tipo_mensaje": "estado",
  "status": "online",
  "timestamp": "2024-01-01T12:00:00"
}
```

### 4. Configuración
```json
{
  "tipo_mensaje": "configuracion",
  "parametros": {
    "intervalo": 30,
    "modo": "automatico"
  }
}
```

### 5. Heartbeat
```json
{
  "tipo_mensaje": "heartbeat",
  "timestamp": "2024-01-01T12:00:00"
}
```

## Configuración

### MQTT
- **Broker**: 161.35.239.177:17090
- **Topic**: `empresas` (escucha únicamente este topic principal)
- **Credenciales**: tocancipa/B0mb3r0s

### Backend
- **URL**: http://localhost:8000
- **Endpoints**:
  - `POST /api/mqtt-alerts/process` - Procesar mensajes MQTT
  - `GET /api/mqtt-alerts/verify-empresa-sede` - Verificar empresa y sede
  - `GET /api/mqtt-alerts` - Obtener todas las alertas
  - `GET /api/mqtt-alerts/<id>` - Obtener alerta por ID

### WebSocket
- **URL**: ws://localhost:8080/ws
- **Reconexión**: 5 intentos con 3 segundos de delay

## Empresas Soportadas

- **cota**: Cota
- **tocancipa**: Tocancipa
- **funza**: Funza
- **madrid**: Madrid

*Se pueden agregar más empresas dinámicamente*

## Logging

El sistema incluye logging estructurado con:
- Timestamp
- Nombre del módulo
- Nivel de log
- Mensaje

### Niveles de log:
- `DEBUG`: Información detallada
- `INFO`: Información general
- `WARNING`: Advertencias
- `ERROR`: Errores
- `CRITICAL`: Errores críticos

## Desarrollo

### Agregar nueva empresa:
```python
app.add_company("nueva_empresa", "Nueva Empresa S.A.")
```

### Agregar nuevo tipo de mensaje:
1. Editar `MessageType` en `handlers/message_handler.py`
2. Agregar procesador en `message_processors`
3. Implementar método `_process_nuevo_tipo_message`

### Personalizar logging:
```python
from utils import setup_logger

logger = setup_logger(
    name="mi_app",
    level="DEBUG",
    log_file="app.log"
)
```

## Troubleshooting

### Problemas comunes:

1. **Error de conexión MQTT**:
   - Verificar credenciales
   - Comprobar conectividad de red
   - Revisar configuración del broker

2. **Error de importación**:
   - Verificar que todos los `__init__.py` estén presentes
   - Ejecutar desde el directorio raíz del proyecto

3. **Backend no disponible**:
   - La aplicación continúa funcionando
   - Se registra warning en logs
   - Revisar configuración de URL del backend

## Contribución

1. Fork el proyecto
2. Crea una branch para tu feature
3. Commit tus cambios
4. Push a la branch
5. Crea un Pull Request

## Licencia

Este proyecto está bajo la licencia MIT.
