"""
Configuración basada en variables de entorno
"""
import os
from .settings import MQTTConfig, BackendConfig, WebSocketConfig, AppConfig


def load_config_from_env() -> AppConfig:
    """
    Cargar configuración desde variables de entorno
    
    Returns:
        AppConfig configurado desde variables de entorno
    """
    
    # Configuración MQTT
    mqtt_config = MQTTConfig(
        broker=os.getenv('MQTT_BROKER', '161.35.239.177'),
        port=int(os.getenv('MQTT_PORT', '17090')),
        topic=os.getenv('MQTT_TOPIC', 'empresas'),
        username=os.getenv('MQTT_USERNAME', 'tocancipa'),
        password=os.getenv('MQTT_PASSWORD', 'B0mb3r0s'),
        client_id=os.getenv('MQTT_CLIENT_ID', 'TST123'),
        keep_alive=int(os.getenv('MQTT_KEEP_ALIVE', '60'))
    )
    
    # Configuración Backend
    backend_config = BackendConfig(
        base_url=os.getenv('BACKEND_URL', 'http://localhost:5002'),
        api_key=os.getenv('BACKEND_API_KEY'),
        timeout=int(os.getenv('BACKEND_TIMEOUT', '30')),
        retry_attempts=int(os.getenv('BACKEND_RETRY_ATTEMPTS', '3')),
        retry_delay=int(os.getenv('BACKEND_RETRY_DELAY', '5'))
    )
    
    # Configuración WebSocket
    websocket_config = WebSocketConfig(
        url=os.getenv('WEBSOCKET_URL', 'ws://localhost:8080/ws'),
        reconnect_attempts=int(os.getenv('WS_RECONNECT_ATTEMPTS', '5')),
        reconnect_delay=int(os.getenv('WS_RECONNECT_DELAY', '3'))
    )
    
    # Configuración de la aplicación
    app_config = AppConfig(
        mqtt=mqtt_config,
        backend=backend_config,
        websocket=websocket_config,
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        message_interval=int(os.getenv('MESSAGE_INTERVAL', '20'))
    )
    
    return app_config
