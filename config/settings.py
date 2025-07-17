"""
Configuración centralizada para la aplicación MQTT
"""
import os
import uuid
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


@dataclass
class MQTTConfig:
    """Configuración para conexión MQTT"""
    broker: str = os.getenv("MQTT_BROKER", "161.35.239.177")
    port: int = int(os.getenv("MQTT_PORT", "17090"))
    topic: str = os.getenv("MQTT_TOPIC", "empresas")
    username: str = os.getenv("MQTT_USERNAME", "tocancipa")
    password: str = os.getenv("MQTT_PASSWORD", "B0mb3r0s")
    client_id: str = os.getenv("MQTT_CLIENT_ID", "TST123")
    keep_alive: int = int(os.getenv("MQTT_KEEP_ALIVE", "60"))
    
    @classmethod
    def with_random_client_id(cls) -> 'MQTTConfig':
        """Crear configuración con ID de cliente aleatorio"""
        config = cls()
        config.client_id = f"tst-{uuid.uuid4()}"
        return config


@dataclass
class BackendConfig:
    """Configuración para conexión al backend"""
    base_url: str = os.getenv("BACKEND_URL", "http://localhost:5002")
    api_key: Optional[str] = os.getenv("BACKEND_API_KEY") or None
    timeout: int = int(os.getenv("BACKEND_TIMEOUT", "30"))
    retry_attempts: int = int(os.getenv("BACKEND_RETRY_ATTEMPTS", "3"))
    retry_delay: int = int(os.getenv("BACKEND_RETRY_DELAY", "5"))
    enabled: bool = True  # Habilitado porque está corriendo


@dataclass
class WhatsAppConfig:
    """Configuración para API de WhatsApp"""
    api_url: str = os.getenv("WHATSAPP_API_URL", "http://localhost:5050")
    timeout: int = int(os.getenv("WHATSAPP_API_TIMEOUT", "30"))
    enabled: bool = True


@dataclass
class WebSocketConfig:
    """Configuración para servidor WebSocket"""
    host: str = os.getenv("WEBSOCKET_HOST", "localhost")
    port: int = int(os.getenv("WEBSOCKET_PORT", "8080"))
    ping_interval: int = int(os.getenv("WEBSOCKET_PING_INTERVAL", "30"))
    ping_timeout: int = int(os.getenv("WEBSOCKET_PING_TIMEOUT", "10"))
    enabled: bool = True


@dataclass
class RedisConfig:
    """Configuración para Redis"""
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD") or None
    
    # Configuración de colas WhatsApp
    whatsapp_queue_name: str = os.getenv("WHATSAPP_QUEUE_NAME", "whatsapp_messages")
    whatsapp_workers: int = int(os.getenv("WHATSAPP_WORKERS", "3"))
    whatsapp_queue_ttl: int = int(os.getenv("WHATSAPP_QUEUE_TTL", "3600"))


@dataclass
class AppConfig:
    """Configuración general de la aplicación"""
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)
    whatsapp: WhatsAppConfig = field(default_factory=WhatsAppConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    message_interval: int = int(os.getenv("MESSAGE_INTERVAL", "20"))
