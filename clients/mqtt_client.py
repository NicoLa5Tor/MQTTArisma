"""
Cliente MQTT escalable y reutilizable
"""
import json
import logging
import time
from typing import Callable, Optional, Any, Dict
import paho.mqtt.client as mqtt
from config.settings import MQTTConfig


class MQTTClient:
    """Cliente MQTT escalable con callbacks personalizables"""
    
    def __init__(self, config: MQTTConfig):
        self.config = config
        self.client = mqtt.Client(config.client_id)
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
        
        # Callbacks personalizables
        self.on_message_callback: Optional[Callable] = None
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None
        
        # Configurar cliente
        self._setup_client()
    
    def _setup_client(self):
        """Configurar el cliente MQTT"""
        self.client.username_pw_set(self.config.username, self.config.password)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
    
    def _should_display_message(self, topic: str) -> bool:
        """Determinar si un mensaje debe mostrarse (solo BOTONERA válidos)"""
        # SOLO procesar si el topic contiene "BOTONERA"
        if "BOTONERA" in topic:
            topic_parts = topic.split("/")
            
            # Buscar la posición de BOTONERA
            botonera_index = -1
            for i, part in enumerate(topic_parts):
                if "BOTONERA" in part:
                    botonera_index = i
                    break
            
            # Verificar que después de BOTONERA hay exactamente 1 parte más
            if botonera_index != -1 and botonera_index + 1 < len(topic_parts):
                # Obtener partes después de BOTONERA
                parts_after_botonera = topic_parts[botonera_index + 1:]
                
                # Filtrar partes vacías (por barras al final como "/")
                parts_after_botonera = [part for part in parts_after_botonera if part.strip()]
                
                # Solo mostrar si hay exactamente 1 parte después de BOTONERA
                return len(parts_after_botonera) == 1
        
        return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback interno para conexión"""
        if rc == 0:
            self.is_connected = True
            self.logger.info("Conectado al broker MQTT!")
            print(f"🔥 CONECTADO AL BROKER MQTT 🔥")
            
            # Suscribirse a TODO
            client.subscribe("#", qos=0)
            print(f"SUSCRITO A: #")
            
            # También suscribirse al topic configurado
            client.subscribe(self.config.topic, qos=0)
            print(f"SUSCRITO A: {self.config.topic}")
            
            # Ejecutar callback personalizado si existe
            if self.on_connect_callback:
                self.on_connect_callback(client, userdata, flags, rc)
        else:
            self.is_connected = False
            self.logger.error(f"Fallo al conectar, código de retorno {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Callback interno para mensajes recibidos - SOLO muestra BOTONERA válidos"""
        try:
            topic = msg.topic
            payload = msg.payload.decode()
            
            # FILTRO PREVIO: Solo mostrar si es BOTONERA válido
            should_display = self._should_display_message(topic)
            
            if should_display:
                print("\n" + "=" * 100)
                print(f"🔥🔥🔥 MENSAJE RECIBIDO 🔥🔥🔥")
                print(f"TOPIC: {topic}")
                print(f"PAYLOAD: {payload}")
                print("=" * 100 + "\n")
                
                self.logger.info("=" * 100)
                self.logger.info(f"🎯 MENSAJE MQTT RECIBIDO 🎯")
                self.logger.info(f"📡 TOPIC: {topic}")
                self.logger.info(f"📦 PAYLOAD: {payload}")
                self.logger.info(f"📊 QoS: {msg.qos}")
                self.logger.info(f"🔄 Retain: {msg.retain}")
                self.logger.info("=" * 100)
                
                # Intentar parsear JSON solo para BOTONERA válidos
                try:
                    json_data = json.loads(payload)
                    self.logger.info(f"✅ JSON VÁLIDO: {json.dumps(json_data, indent=2)}")
                    print(f"JSON: {json.dumps(json_data, indent=2)}")
                except json.JSONDecodeError:
                    self.logger.info("⚠️ NO ES JSON VÁLIDO")
                    json_data = None
            else:
                # Para mensajes no-BOTONERA, parsear JSON sin mostrar
                try:
                    json_data = json.loads(payload)
                except json.JSONDecodeError:
                    json_data = None
            
            # Ejecutar callback personalizado si existe (siempre)
            if self.on_message_callback:
                self.on_message_callback(topic, payload, json_data)
            else:
                self.logger.warning("⚠️ NO HAY CALLBACK CONFIGURADO")
                
        except Exception as e:
            self.logger.error(f"💥 ERROR PROCESANDO MENSAJE: {e}")
            print(f"ERROR: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback interno para desconexión"""
        self.is_connected = False
        self.logger.info(f"Desconectado del broker MQTT: {rc}")
        
        if self.on_disconnect_callback:
            self.on_disconnect_callback(client, userdata, rc)
    
    def connect(self) -> bool:
        """Conectar al broker MQTT"""
        try:
            self.client.connect(
                self.config.broker, 
                self.config.port, 
                self.config.keep_alive
            )
            return True
        except Exception as e:
            self.logger.error(f"Error conectando al broker: {e}")
            return False
    
    def start_loop(self):
        """Iniciar el loop de MQTT (non-blocking)"""
        self.client.loop_start()
    
    def stop_loop(self):
        """Detener el loop de MQTT"""
        self.client.loop_stop()
    
    def disconnect(self):
        """Desconectar del broker"""
        self.client.disconnect()
        self.is_connected = False
    
    def publish(self, topic: str, message: str, qos: int = 0) -> bool:
        """Publicar mensaje en un tema"""
        if not self.is_connected:
            self.logger.warning("No conectado al broker. No se puede publicar.")
            return False
        
        try:
            result = self.client.publish(topic, message, qos)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Mensaje publicado en {topic}: {message}")
                return True
            else:
                self.logger.error(f"Error publicando mensaje: {result.rc}")
                return False
        except Exception as e:
            self.logger.error(f"Excepción al publicar: {e}")
            return False
    
    def publish_json(self, topic: str, data: Dict[str, Any], qos: int = 0) -> bool:
        """Publicar datos JSON en un tema"""
        try:
            json_message = json.dumps(data)
            return self.publish(topic, json_message, qos)
        except Exception as e:
            self.logger.error(f"Error serializando JSON: {e}")
            return False
    
    def subscribe(self, topic: str, qos: int = 0):
        """Suscribirse a un tema adicional"""
        if self.is_connected:
            self.client.subscribe(topic, qos)
            self.logger.info(f"Suscrito a {topic}")
    
    def unsubscribe(self, topic: str):
        """Desuscribirse de un tema"""
        if self.is_connected:
            self.client.unsubscribe(topic)
            self.logger.info(f"Desuscrito de {topic}")
    
    def set_message_callback(self, callback: Callable):
        """Establecer callback para mensajes recibidos"""
        self.on_message_callback = callback
    
    def set_connect_callback(self, callback: Callable):
        """Establecer callback para conexión"""
        self.on_connect_callback = callback
    
    def set_disconnect_callback(self, callback: Callable):
        """Establecer callback para desconexión"""
        self.on_disconnect_callback = callback
