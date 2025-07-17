"""
Mini cliente MQTT para publicación que reutiliza el MQTTClient existente
"""

import logging
from typing import Dict, Any, Optional
from clients.mqtt_client import MQTTClient
from config.settings import MQTTConfig

class MQTTPublisherLite:
    """
    Mini cliente MQTT para publicación que reutiliza el MQTTClient existente
    sin dañar la lógica actual ni los callbacks
    """
    
    def __init__(self, config: MQTTConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Crear un MQTTClient pero configurado solo para publicar
        self.mqtt_client = MQTTClient(config)
        
        # Configurar callbacks minimalistas (sin suscripciones automáticas)
        self._setup_publisher_callbacks()
        
        self.is_connected = False
        self.publish_count = 0
        self.error_count = 0
    
    def _setup_publisher_callbacks(self):
        """Configurar callbacks minimalistas solo para publicación"""
        
        def minimal_connect_callback(client, userdata, flags, rc):
            """Callback de conexión sin suscripciones automáticas"""
            if rc == 0:
                self.is_connected = True
                self.logger.info("📤 MQTT Publisher conectado al broker")
            else:
                self.is_connected = False
                self.logger.error(f"❌ Error conectando MQTT Publisher: {rc}")
        
        def minimal_disconnect_callback(client, userdata, rc):
            """Callback de desconexión"""
            self.is_connected = False
            self.logger.info("📡 MQTT Publisher desconectado")
        
        # Asignar callbacks minimalistas
        self.mqtt_client.set_connect_callback(minimal_connect_callback)
        self.mqtt_client.set_disconnect_callback(minimal_disconnect_callback)
        
        # NO configurar callback de mensajes para evitar logs innecesarios
        # self.mqtt_client.set_message_callback(None)
    
    def connect(self) -> bool:
        """
        Conectar al broker MQTT
        Reutiliza el método connect del MQTTClient existente
        """
        try:
            if self.mqtt_client.connect():
                self.mqtt_client.start_loop()
                
                # Esperar un poco para que se establezca la conexión
                import time
                timeout = 5
                start_time = time.time()
                while not self.is_connected and (time.time() - start_time) < timeout:
                    time.sleep(0.1)
                
                if self.is_connected:
                    self.logger.info("✅ MQTT Publisher conectado y listo")
                    return True
                else:
                    self.logger.error("❌ Timeout conectando MQTT Publisher")
                    return False
            else:
                self.logger.error("❌ Error en conexión inicial")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error conectando al broker: {e}")
            return False
    
    def disconnect(self):
        """
        Desconectar del broker
        Reutiliza el método disconnect del MQTTClient existente
        """
        try:
            self.mqtt_client.stop_loop()
            self.mqtt_client.disconnect()
            self.is_connected = False
            self.logger.info("✅ MQTT Publisher desconectado")
        except Exception as e:
            self.logger.error(f"❌ Error desconectando: {e}")
    
    def publish(self, topic: str, message: str, qos: int = 0) -> bool:
        """
        Publicar mensaje de texto
        Reutiliza el método publish del MQTTClient existente
        """
        if not self.is_connected:
            self.logger.warning("⚠️ MQTT Publisher no conectado")
            self.error_count += 1
            return False
        
        try:
            success = self.mqtt_client.publish(topic, message, qos)
            if success:
                self.publish_count += 1
                self.logger.info(f"📤 Mensaje publicado en {topic}")
            else:
                self.error_count += 1
                self.logger.error(f"❌ Error publicando mensaje en {topic}")
            
            return success
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"❌ Excepción publicando mensaje: {e}")
            return False
    
    def publish_json(self, topic: str, data: Dict[str, Any], qos: int = 0) -> bool:
        """
        Publicar datos JSON
        Reutiliza el método publish_json del MQTTClient existente
        """
        if not self.is_connected:
            self.logger.warning("⚠️ MQTT Publisher no conectado")
            self.error_count += 1
            return False
        
        try:
            success = self.mqtt_client.publish_json(topic, data, qos)
            if success:
                self.publish_count += 1
                self.logger.info(f"📤 JSON publicado en {topic}")
            else:
                self.error_count += 1
                self.logger.error(f"❌ Error publicando JSON en {topic}")
            
            return success
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"❌ Excepción publicando JSON: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del publisher"""
        return {
            "connected": self.is_connected,
            "broker": self.config.broker,
            "port": self.config.port,
            "client_id": self.config.client_id,
            "messages_published": self.publish_count,
            "errors": self.error_count,
            "success_rate": round(
                (self.publish_count / max(self.publish_count + self.error_count, 1)) * 100, 2
            )
        }
    
    def get_underlying_client(self) -> MQTTClient:
        """
        Obtener el cliente MQTT subyacente para acceso avanzado
        (solo si es necesario)
        """
        return self.mqtt_client
