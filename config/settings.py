"""
Configuración centralizada para la aplicación MQTT
"""
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MQTTConfig:
    """Configuración para conexión MQTT"""
    broker: str = "161.35.239.177"
    port: int = 17090
    topic: str = "empresas"
    username: str = "tocancipa"
    password: str = "B0mb3r0s"
    client_id: str = "TST123"
    keep_alive: int = 60
    
    @classmethod
    def with_random_client_id(cls) -> 'MQTTConfig':
        """Crear configuración con ID de cliente aleatorio"""
        config = cls()
        config.client_id = f"tst-{uuid.uuid4()}"
        return config


@dataclass
class BackendConfig:
    """Configuración para conexión al backend"""
    base_url: str = "http://127.0.0.1:5002"
    api_key: Optional[str] = None
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5
    enabled: bool = True  # Habilitado porque está corriendo


@dataclass
class WebSocketConfig:
    """Configuración para WebSocket"""
    url: str = "ws://localhost:8080/ws"
    reconnect_attempts: int = 3
    reconnect_delay: int = 5
    enabled: bool = False  # Por defecto deshabilitado


@dataclass
class AppConfig:
    """Configuración general de la aplicación"""
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    log_level: str = "INFO"
    message_interval: int = 20
