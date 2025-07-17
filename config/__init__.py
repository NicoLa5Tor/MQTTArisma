"""
Módulo de configuración para la aplicación MQTT escalable
"""

from .settings import AppConfig, MQTTConfig, BackendConfig
from .env_config import load_config_from_env
# from .hardware_manager import HardwareManager, HardwareType  # ELIMINADO

__all__ = ['AppConfig', 'MQTTConfig', 'BackendConfig', 'load_config_from_env']  # , 'HardwareManager', 'HardwareType']
