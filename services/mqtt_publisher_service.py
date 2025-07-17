"""
Servicio independiente de publicación MQTT
"""

import logging
from typing import Dict, Any, Optional
from clients.mqtt_publisher_lite import MQTTPublisherLite
from config import AppConfig

class MQTTPublisherService:
    """
    Servicio independiente para publicar mensajes MQTT
    Reutiliza el MQTTClient existente sin dañar la lógica actual
    """
    
    def __init__(self, config: AppConfig = None):
        self.config = config or AppConfig()
        self.logger = logging.getLogger(__name__)
        
        # Crear el mini cliente publisher
        self.publisher = MQTTPublisherLite(self.config.mqtt)
        
        self.is_running = False
        self.service_stats = {
            "start_time": None,
            "total_requests": 0,
            "successful_publishes": 0,
            "failed_publishes": 0
        }
    
    def start(self) -> bool:
        """Iniciar el servicio de publicación"""
        self.logger.info("🚀 Iniciando servicio de publicación MQTT...")
        
        try:
            if self.publisher.connect():
                self.is_running = True
                
                import time
                self.service_stats["start_time"] = time.time()
                
                self.logger.info("✅ Servicio de publicación MQTT iniciado")
                return True
            else:
                self.logger.error("❌ Error iniciando servicio de publicación")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error iniciando servicio: {e}")
            return False
    
    def stop(self):
        """Detener el servicio de publicación"""
        self.logger.info("🛑 Deteniendo servicio de publicación MQTT...")
        
        try:
            self.publisher.disconnect()
            self.is_running = False
            self.logger.info("✅ Servicio de publicación MQTT detenido")
        except Exception as e:
            self.logger.error(f"❌ Error deteniendo servicio: {e}")
    
    def publish_message(self, topic: str, message: str, qos: int = 0) -> bool:
        """
        Publicar mensaje de texto
        
        Args:
            topic: Topic MQTT donde publicar
            message: Mensaje de texto
            qos: Calidad de servicio (0, 1, 2)
            
        Returns:
            bool: True si se publicó exitosamente, False en caso contrario
        """
        if not self.is_running:
            self.logger.warning("⚠️ Servicio no está corriendo")
            return False
        
        self.service_stats["total_requests"] += 1
        
        try:
            success = self.publisher.publish(topic, message, qos)
            
            if success:
                self.service_stats["successful_publishes"] += 1
                self.logger.info(f"📤 Mensaje publicado exitosamente en {topic}")
            else:
                self.service_stats["failed_publishes"] += 1
                self.logger.error(f"❌ Error publicando mensaje en {topic}")
            
            return success
            
        except Exception as e:
            self.service_stats["failed_publishes"] += 1
            self.logger.error(f"❌ Excepción publicando mensaje: {e}")
            return False
    
    def publish_json(self, topic: str, data: Dict[str, Any], qos: int = 0) -> bool:
        """
        Publicar datos JSON
        
        Args:
            topic: Topic MQTT donde publicar
            data: Datos JSON para publicar
            qos: Calidad de servicio (0, 1, 2)
            
        Returns:
            bool: True si se publicó exitosamente, False en caso contrario
        """
        if not self.is_running:
            self.logger.warning("⚠️ Servicio no está corriendo")
            return False
        
        self.service_stats["total_requests"] += 1
        
        try:
            success = self.publisher.publish_json(topic, data, qos)
            
            if success:
                self.service_stats["successful_publishes"] += 1
                self.logger.info(f"📤 JSON publicado exitosamente en {topic}")
            else:
                self.service_stats["failed_publishes"] += 1
                self.logger.error(f"❌ Error publicando JSON en {topic}")
            
            return success
            
        except Exception as e:
            self.service_stats["failed_publishes"] += 1
            self.logger.error(f"❌ Excepción publicando JSON: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado completo del servicio"""
        publisher_status = self.publisher.get_status()
        
        import time
        current_time = time.time()
        uptime = current_time - self.service_stats["start_time"] if self.service_stats["start_time"] else 0
        
        return {
            "service": {
                "running": self.is_running,
                "uptime_seconds": round(uptime, 2),
                "total_requests": self.service_stats["total_requests"],
                "successful_publishes": self.service_stats["successful_publishes"],
                "failed_publishes": self.service_stats["failed_publishes"],
                "success_rate": round(
                    (self.service_stats["successful_publishes"] / max(self.service_stats["total_requests"], 1)) * 100, 2
                )
            },
            "mqtt_publisher": publisher_status
        }
    
    def get_simple_status(self) -> Dict[str, Any]:
        """Obtener estado simple del servicio"""
        status = self.get_status()
        return {
            "running": status["service"]["running"],
            "connected": status["mqtt_publisher"]["connected"],
            "messages_published": status["mqtt_publisher"]["messages_published"],
            "success_rate": status["service"]["success_rate"]
        }
    
    def is_healthy(self) -> bool:
        """Verificar si el servicio está saludable"""
        return self.is_running and self.publisher.is_connected
