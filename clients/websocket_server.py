"""
Servidor WebSocket híbrido para recibir mensajes de WhatsApp y manejar MQTT
"""

import asyncio
import websockets
import logging
import json
from typing import Optional, Dict, Any
from handlers.message_handler import MessageHandler
from clients.backend_client import BackendClient
from clients.mqtt_client import MQTTClient
from config.settings import BackendConfig
from config import AppConfig

class WebSocketServer:
    """Servidor WebSocket híbrido que maneja WhatsApp y MQTT"""
    
    def __init__(self, host: str = None, port: int = None, enable_mqtt: bool = True):
        # Crear configuración completa
        self.config = AppConfig()
        
        # Usar configuración centralizada o parámetros proporcionados
        self.host = host or self.config.websocket.host
        self.port = port or self.config.websocket.port
        self.enable_mqtt = enable_mqtt
        
        # Inicializar clientes
        self.backend_client = BackendClient(self.config.backend)
        self.mqtt_client = None
        
        if self.enable_mqtt:
            self.mqtt_client = MQTTClient(self.config.mqtt)
            self._setup_mqtt_callbacks()
        
        # Inicializar manejador de mensajes
        self.message_handler = MessageHandler(
            backend_client=self.backend_client,
            mqtt_client=self.mqtt_client
        )
        
        self.server = None
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.mqtt_message_count = 0
        
        # Estadísticas
        self.stats = {
            'mqtt_messages': 0,
            'whatsapp_messages': 0,
            'mqtt_errors': 0,
            'whatsapp_errors': 0
        }
    
    def _setup_mqtt_callbacks(self):
        """Configurar callbacks para MQTT"""
        if not self.mqtt_client:
            return
            
        # Callback para mensajes MQTT
        def mqtt_message_callback(topic, payload, json_data):
            self.mqtt_message_count += 1
            self.stats['mqtt_messages'] += 1
            
            self.logger.info(f"🎉 MENSAJE MQTT #{self.mqtt_message_count} - TOPIC: {topic}")
            
            # Procesar mensaje usando el manejador
            try:
                success = self.message_handler.process_mqtt_message(topic, payload, json_data)
                
                if success:
                    self.logger.info(f"✅ Mensaje MQTT #{self.mqtt_message_count} procesado exitosamente")
                else:
                    self.logger.error(f"❌ Error procesando mensaje MQTT #{self.mqtt_message_count}")
                    self.stats['mqtt_errors'] += 1
            except Exception as e:
                self.logger.error(f"❌ Excepción procesando mensaje MQTT: {e}")
                self.stats['mqtt_errors'] += 1
        
        # Callback para conexión MQTT
        def mqtt_connect_callback(client, userdata, flags, rc):
            if rc == 0:
                self.logger.info("🔥 Conectado exitosamente al broker MQTT desde WebSocket")
                
                # Suscribirse a topics de BOTONERA
                topics_to_subscribe = [
                    "empresas/+/+/BOTONERA/+",  # Estructura principal
                    "empresas/#",               # Wildcard completo
                ]
                
                for topic in topics_to_subscribe:
                    self.mqtt_client.subscribe(topic, qos=0)
                    self.logger.info(f"🔍 Suscrito a: {topic}")
                    
            else:
                self.logger.error(f"Error conectando al MQTT: {rc}")
        
        # Asignar callbacks
        self.mqtt_client.set_message_callback(mqtt_message_callback)
        self.mqtt_client.set_connect_callback(mqtt_connect_callback)
        
    async def handle_client(self, websocket):
        """Manejar conexión de cliente"""
        self.logger.info(f"Cliente conectado desde {websocket.remote_address}")
        
        try:
            async for message in websocket:
                # Usar el sistema de colas asíncrono
                success = await self.message_handler.queue_whatsapp_message(message)
                
                if not success:
                    self.logger.warning(f"No se pudo procesar mensaje: cola llena o error")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Cliente desconectado")
        except Exception as e:
            self.logger.error(f"Error manejando cliente: {e}")
    
    async def start(self):
        """Iniciar el servidor WebSocket"""
        self.logger.info(f"Iniciando servidor WebSocket en ws://{self.host}:{self.port}")
        
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=self.config.websocket.ping_interval,
            ping_timeout=self.config.websocket.ping_timeout
        )
        
        self.is_running = True
        self.logger.info(f"✅ Servidor WebSocket iniciado en ws://{self.host}:{self.port}")
        
        return self.server
    
    async def stop(self):
        """Detener el servidor WebSocket"""
        self.logger.info("🛑 Deteniendo servidor WebSocket...")
        self.is_running = False
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
        self.logger.info("✅ Servidor WebSocket detenido")
    
    def set_message_handler(self, message_handler: MessageHandler):
        """Establecer el manejador de mensajes"""
        self.message_handler = message_handler
    
    def get_whatsapp_statistics(self):
        """Obtener estadísticas del procesador de WhatsApp"""
        return self.message_handler.get_whatsapp_statistics()
    
    async def stop_whatsapp_processing(self):
        """Detener el procesamiento de la cola de WhatsApp"""
        await self.message_handler.stop_whatsapp_processing()
    
    async def clear_whatsapp_queue(self):
        """Limpiar la cola de WhatsApp"""
        return await self.message_handler.clear_whatsapp_queue()
