"""
Mixin para integrar el servicio de publicación MQTT en el WebSocket Server
"""

import logging
from typing import Dict, Any, Optional
from services.mqtt_publisher_service import MQTTPublisherService

class MQTTPublisherMixin:
    """
    Mixin para agregar funcionalidad de publicación MQTT a cualquier clase
    sin modificar el código existente
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mqtt_publisher_service: Optional[MQTTPublisherService] = None
        self.mqtt_publisher_logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def init_mqtt_publisher(self, config=None) -> bool:
        """
        Inicializar el servicio de publicación MQTT
        
        Args:
            config: Configuración opcional (usa AppConfig por defecto)
            
        Returns:
            bool: True si se inicializó correctamente
        """
        try:
            self.mqtt_publisher_service = MQTTPublisherService(config)
            
            if self.mqtt_publisher_service.start():
                self.mqtt_publisher_logger.info("✅ Servicio MQTT Publisher integrado exitosamente")
                return True
            else:
                self.mqtt_publisher_logger.error("❌ Error iniciando servicio MQTT Publisher")
                return False
                
        except Exception as e:
            self.mqtt_publisher_logger.error(f"❌ Error inicializando MQTT Publisher: {e}")
            return False
    
    def stop_mqtt_publisher(self):
        """Detener el servicio de publicación MQTT"""
        if self.mqtt_publisher_service:
            try:
                self.mqtt_publisher_service.stop()
                self.mqtt_publisher_logger.info("✅ Servicio MQTT Publisher detenido")
            except Exception as e:
                self.mqtt_publisher_logger.error(f"❌ Error deteniendo MQTT Publisher: {e}")
    
    def publish_mqtt(self, topic: str, message: str, qos: int = 0) -> bool:
        """
        Publicar mensaje MQTT (texto)
        
        Args:
            topic: Topic MQTT
            message: Mensaje de texto
            qos: Calidad de servicio
            
        Returns:
            bool: True si se publicó exitosamente
        """
        if not self.mqtt_publisher_service:
            self.mqtt_publisher_logger.warning("⚠️ Servicio MQTT Publisher no inicializado")
            return False
        
        return self.mqtt_publisher_service.publish_message(topic, message, qos)
    
    def publish_mqtt_json(self, topic: str, data: Dict[str, Any], qos: int = 0) -> bool:
        """
        Publicar datos JSON via MQTT
        
        Args:
            topic: Topic MQTT
            data: Datos JSON
            qos: Calidad de servicio
            
        Returns:
            bool: True si se publicó exitosamente
        """
        if not self.mqtt_publisher_service:
            self.mqtt_publisher_logger.warning("⚠️ Servicio MQTT Publisher no inicializado")
            return False
        
        return self.mqtt_publisher_service.publish_json(topic, data, qos)
    
    def get_mqtt_publisher_status(self) -> Dict[str, Any]:
        """
        Obtener estado del servicio MQTT Publisher
        
        Returns:
            Dict con el estado del servicio
        """
        if not self.mqtt_publisher_service:
            return {
                "initialized": False,
                "running": False,
                "connected": False,
                "messages_published": 0
            }
        
        status = self.mqtt_publisher_service.get_simple_status()
        status["initialized"] = True
        return status
    
    def is_mqtt_publisher_healthy(self) -> bool:
        """
        Verificar si el servicio MQTT Publisher está saludable
        
        Returns:
            bool: True si está saludable
        """
        if not self.mqtt_publisher_service:
            return False
        
        return self.mqtt_publisher_service.is_healthy()
