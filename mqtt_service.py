#!/usr/bin/env python3
"""
Servicio MQTT independiente - SIN WEBSOCKETS
Maneja SOLO conexiones MQTT, procesamiento de mensajes MQTT y comunicación con el backend.
"""

import signal
import sys
import os
import logging
import time
from typing import Dict, Any

# Agregar el directorio actual al path para las importaciones
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clients.mqtt_client import MQTTClient
from clients.backend_client import BackendClient
from clients.mqtt_publisher_lite import MQTTPublisherLite
from handlers.mqtt_message_handler import MQTTMessageHandler
from services.whatsapp_service import WhatsAppService
from utils.logger import setup_logger
from config import AppConfig
from config.settings import MQTTConfig


class MQTTService:
    """Servicio MQTT independiente - SIN dependencias de WebSocket"""
    
    def __init__(self):
        # Configuración
        self.config = AppConfig()
        # Logger con archivo separado para poder hacer tail -f
        self.logger = setup_logger(
            "mqtt_service", 
            self.config.log_level,
            log_file="logs/mqtt_service.log"
        )
        
        # Clientes independientes para MQTT
        self.backend_client = BackendClient(self.config.backend)
        self.whatsapp_service = WhatsAppService(self.config.whatsapp)
        
        # MQTT Cliente para recibir mensajes (receiver)
        receiver_config = MQTTConfig(
            broker=self.config.mqtt.broker,
            port=self.config.mqtt.port,
            topic=self.config.mqtt.topic,
            username=self.config.mqtt.username,
            password=self.config.mqtt.password,
            client_id=f"{self.config.mqtt.client_id}_receiver",
            keep_alive=self.config.mqtt.keep_alive
        )
        self.mqtt_receiver = MQTTClient(receiver_config)
        
        # MQTT Publisher para enviar mensajes (publisher)
        publisher_config = MQTTConfig(
            broker=self.config.mqtt.broker,
            port=self.config.mqtt.port,
            topic=self.config.mqtt.topic,
            username=self.config.mqtt.username,
            password=self.config.mqtt.password,
            client_id=f"{self.config.mqtt.client_id}_publisher",
            keep_alive=self.config.mqtt.keep_alive
        )
        self.mqtt_publisher = MQTTPublisherLite(publisher_config)
        
        # Manejador de mensajes MQTT puro (sin WebSocket)
        self.message_handler = MQTTMessageHandler(
            backend_client=self.backend_client,
            mqtt_publisher=self.mqtt_publisher,
            whatsapp_service=self.whatsapp_service,  # Solo para ENVIAR notificaciones
            config=self.config
        )
        
        # Estado del servicio
        self.is_running = False
        self.message_count = 0
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Manejar señales de terminación"""
        self.logger.info("\n¡Recibida señal de terminación para servicio MQTT!")
        self.stop()
        sys.exit(0)
    
    def _setup_mqtt_callbacks(self):
        """Configurar callbacks para el cliente MQTT receptor"""
        
        def mqtt_message_callback(topic, payload, json_data):
            """Callback para procesar mensajes MQTT recibidos"""
            self.message_count += 1
            self.logger.info(f"🎉 MENSAJE MQTT #{self.message_count} - TOPIC: {topic}")
            
            try:
                success = self.message_handler.process_mqtt_message(topic, payload, json_data)
                
                if success:
                    self.logger.info(f"✅ Mensaje MQTT #{self.message_count} procesado exitosamente")
                else:
                    self.logger.error(f"❌ Error procesando mensaje MQTT #{self.message_count}")
                    
            except Exception as e:
                self.logger.error(f"❌ Excepción procesando mensaje MQTT: {e}")
        
        def mqtt_connect_callback(client, userdata, flags, rc):
            """Callback para conexión MQTT establecida"""
            if rc == 0:
                self.logger.info("🔥 Conectado exitosamente al broker MQTT")
                
                # Suscribirse SOLO a topics de BOTONERA física
                topics_to_subscribe = [
                    "empresas/+/+/BOTONERA/+",  # Solo BOTONERA física
                ]
                
                for topic in topics_to_subscribe:
                    self.mqtt_receiver.subscribe(topic, qos=0)
                    self.logger.info(f"🔍 Suscrito a: {topic}")
                    
            else:
                self.logger.error(f"Error conectando al MQTT: {rc}")
        
        def mqtt_disconnect_callback(client, userdata, rc):
            """Callback para desconexión MQTT"""
            if rc != 0:
                self.logger.warning(f"Desconexión inesperada del broker MQTT: {rc}")
        
        # Asignar callbacks
        self.mqtt_receiver.set_message_callback(mqtt_message_callback)
        self.mqtt_receiver.set_connect_callback(mqtt_connect_callback)
        self.mqtt_receiver.set_disconnect_callback(mqtt_disconnect_callback)
    
    def start(self) -> bool:
        """Iniciar el servicio MQTT"""
        self.logger.info("🚀 Iniciando servicio MQTT independiente...")
        self.logger.info(f"📡 Broker: {self.config.mqtt.broker}:{self.config.mqtt.port}")
        self.logger.info(f"👤 Usuario: {self.config.mqtt.username}")
        self.logger.info(f"📋 Topic base: {self.config.mqtt.topic}")
        
        try:
            # Conectar MQTT Publisher
            if not self.mqtt_publisher.connect():
                self.logger.error("❌ Error conectando MQTT Publisher")
                return False
            
            self.logger.info("✅ MQTT Publisher conectado exitosamente")
            
            # Configurar callbacks del receptor
            self._setup_mqtt_callbacks()
            
            # Conectar MQTT Receiver
            if not self.mqtt_receiver.connect():
                self.logger.error("❌ Error conectando MQTT Receiver")
                return False
            
            # Iniciar loop del receptor
            self.mqtt_receiver.start_loop()
            self.is_running = True
            
            self.logger.info("✅ Servicio MQTT iniciado correctamente")
            self.logger.info("🎯 Esperando mensajes MQTT de BOTONERA...")
            self.logger.info("📋 Presiona Ctrl+C para detener")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error iniciando servicio MQTT: {e}")
            return False
    
    def run(self):
        """Ejecutar el servicio MQTT de forma continua"""
        if not self.start():
            self.logger.error("❌ No se pudo iniciar el servicio MQTT")
            return False
        
        try:
            # Mantener el servicio corriendo
            while self.is_running:
                time.sleep(1)
                
                # Mostrar estadísticas cada 5 minutos (300 segundos)
                if self.message_count > 0 and self.message_count % 100 == 0:
                    self._show_statistics()
                    
        except KeyboardInterrupt:
            self.logger.info("Interrupción del usuario detectada")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Detener el servicio MQTT"""
        self.logger.info("🛑 Deteniendo servicio MQTT...")
        self.is_running = False
        
        try:
            # Detener receptor MQTT
            if hasattr(self, 'mqtt_receiver') and self.mqtt_receiver:
                self.mqtt_receiver.stop_loop()
                self.mqtt_receiver.disconnect()
                self.logger.info("✅ MQTT Receiver desconectado")
            
            # Detener publisher MQTT
            if hasattr(self, 'mqtt_publisher') and self.mqtt_publisher:
                self.mqtt_publisher.disconnect()
                self.logger.info("✅ MQTT Publisher desconectado")
            
            # Mostrar estadísticas finales
            self._show_final_statistics()
            
        except Exception as e:
            self.logger.error(f"❌ Error deteniendo servicio: {e}")
    
    def _show_statistics(self):
        """Mostrar estadísticas del servicio"""
        self.logger.info("📊 Estadísticas del servicio MQTT:")
        self.logger.info(f"  • Mensajes procesados: {self.message_count}")
        self.logger.info(f"  • Estado del receptor: {'Conectado' if self.mqtt_receiver.is_connected else 'Desconectado'}")
        self.logger.info(f"  • Estado del publisher: {'Conectado' if self.mqtt_publisher.is_connected else 'Desconectado'}")
        
        # Estadísticas del manejador de mensajes
        handler_stats = self.message_handler.get_statistics()
        self.logger.info(f"  • Mensajes exitosos: {handler_stats['processed_messages']}")
        self.logger.info(f"  • Errores: {handler_stats['error_count']}")
        self.logger.info(f"  • Tasa de éxito: {100 - handler_stats['error_rate']}%")
        
        print("=" * 60)
    
    def _show_final_statistics(self):
        """Mostrar estadísticas finales"""
        self.logger.info("📊 Estadísticas finales del servicio MQTT:")
        self.logger.info(f"  • Total de mensajes recibidos: {self.message_count}")
        
        if hasattr(self, 'message_handler'):
            handler_stats = self.message_handler.get_statistics()
            self.logger.info(f"  • Mensajes procesados exitosamente: {handler_stats['processed_messages']}")
            self.logger.info(f"  • Errores totales: {handler_stats['error_count']}")
            self.logger.info(f"  • Tasa de éxito final: {100 - handler_stats['error_rate']}%")
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del servicio"""
        return {
            "service": "MQTT Service",
            "running": self.is_running,
            "messages_received": self.message_count,
            "mqtt_receiver_connected": self.mqtt_receiver.is_connected if hasattr(self, 'mqtt_receiver') else False,
            "mqtt_publisher_connected": self.mqtt_publisher.is_connected if hasattr(self, 'mqtt_publisher') else False,
            "backend_enabled": self.config.backend.enabled,
            "whatsapp_enabled": self.config.whatsapp.enabled
        }


def main():
    """Función principal para ejecutar el servicio MQTT"""
    print("🚀 Iniciando Servicio MQTT Independiente")
    print("=" * 60)
    print("📡 Sin dependencias de WebSocket")
    print("🎯 Solo procesamiento MQTT + Backend + WhatsApp")
    print("=" * 60)
    
    try:
        # Crear y ejecutar servicio
        mqtt_service = MQTTService()
        mqtt_service.run()
        
    except Exception as e:
        print(f"❌ Error ejecutando servicio MQTT: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
