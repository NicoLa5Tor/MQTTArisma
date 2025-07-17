#!/usr/bin/env python3
"""
Punto de entrada principal para la aplicación MQTT simplificada
"""

import sys
import os
import signal
import logging
import time
import json

# Agregar el directorio actual al path para las importaciones
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import AppConfig
from clients import MQTTClient, BackendClient
from handlers import MessageHandler
from utils import setup_logger

app_instance = None

class SimpleMQTTApp:
    """Aplicación MQTT simplificada"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Inicializar componentes
        self.mqtt_client = MQTTClient(config.mqtt)
        self.backend_client = BackendClient(config.backend)
        
        # Inicializar manejador de mensajes
        self.message_handler = MessageHandler(
            backend_client=self.backend_client,
            mqtt_client=self.mqtt_client
        )
        
        # Configurar callbacks
        self._setup_callbacks()
        
        # Estado de la aplicación
        self.is_running = False
        self.message_count = 0
        
    def _setup_callbacks(self):
        """Configurar callbacks para MQTT"""
        
        # Callback para mensajes MQTT
        def mqtt_message_callback(topic, payload, json_data):
            self.message_count += 1
            self.logger.info(f"🎉 MENSAJE MQTT #{self.message_count} - TOPIC: {topic}")
            
            # Procesar mensaje usando el manejador
            success = self.message_handler.process_mqtt_message(topic, payload, json_data)
            
            if success:
                self.logger.info(f"✅ Mensaje #{self.message_count} procesado exitosamente")
            else:
                self.logger.error(f"❌ Error procesando mensaje #{self.message_count}")
        
        # Callback para conexión MQTT
        def mqtt_connect_callback(client, userdata, flags, rc):
            if rc == 0:
                self.logger.info("Conectado exitosamente al broker MQTT")
                
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
    
    def start(self):
        """Iniciar la aplicación"""
        self.logger.info("🚀 Iniciando aplicación MQTT simplificada...")
        
        try:
            # Conectar MQTT
            if not self.mqtt_client.connect():
                self.logger.error("❌ Error conectando al broker MQTT")
                return False
            
            self.mqtt_client.start_loop()
            self.logger.info("✅ Cliente MQTT conectado")
            
            self.is_running = True
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error iniciando aplicación: {e}")
            return False
    
    def stop(self):
        """Detener la aplicación"""
        self.logger.info("🛑 Deteniendo aplicación...")
        
        self.is_running = False
        
        # Detener MQTT
        self.mqtt_client.stop_loop()
        self.mqtt_client.disconnect()
        
        self.logger.info("✅ Aplicación detenida")
    
    def run(self):
        """Ejecutar la aplicación principal"""
        if not self.start():
            return
        
        try:
            while self.is_running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Interrupción del usuario detectada")
        except Exception as e:
            self.logger.error(f"Error en bucle principal: {e}")
        finally:
            self.stop()

def signal_handler(signum, frame):
    """Manejar señales para detener la aplicación correctamente"""
    print("\n¡Recibida señal de terminación!")
    if app_instance:
        app_instance.stop()
    sys.exit(0)

def main():
    global app_instance
    
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Configurar logging
    logger = setup_logger("mqtt_app", "INFO")
    
    try:
        # Crear configuración
        config = AppConfig()
        
        # Crear y ejecutar aplicación
        app_instance = SimpleMQTTApp(config)
        app_instance.run()
        
    except Exception as e:
        logger.error(f"Error en aplicación principal: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
