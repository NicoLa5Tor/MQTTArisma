#!/usr/bin/env python3
"""
Script de prueba simple para verificar si el cliente MQTT está funcionando correctamente
"""
import sys
import os
import time
import logging

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import MQTTConfig
from clients import MQTTClient

def setup_logging():
    """Configurar logging simple"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def main():
    logger = setup_logging()
    logger.info("🚀 Iniciando prueba simple de MQTT...")
    
    # Crear configuración
    config = MQTTConfig()
    logger.info(f"📡 Configuración MQTT:")
    logger.info(f"   Broker: {config.broker}:{config.port}")
    logger.info(f"   Usuario: {config.username}")
    logger.info(f"   Topic: {config.topic}")
    logger.info(f"   Client ID: {config.client_id}")
    
    # Crear cliente
    client = MQTTClient(config)
    
    # Callback para mensajes
    def on_message_received(topic, payload, json_data):
        logger.info(f"📬 MENSAJE RECIBIDO:")
        logger.info(f"   📂 Topic: {topic}")
        logger.info(f"   📄 Payload: {payload}")
        if json_data:
            logger.info(f"   📊 JSON: {json_data}")
    
    # Callback para conexión
    def on_connected(client, userdata, flags, rc):
        if rc == 0:
            logger.info("✅ ¡Conectado exitosamente al broker MQTT!")
            logger.info(f"🔔 Suscribiéndose al topic: {config.topic}")
        else:
            logger.error(f"❌ Error conectando: {rc}")
    
    # Callback para desconexión
    def on_disconnected(client, userdata, rc):
        logger.warning(f"⚠️ Desconectado del broker: {rc}")
    
    # Configurar callbacks
    client.set_message_callback(on_message_received)
    client.set_connect_callback(on_connected)
    client.set_disconnect_callback(on_disconnected)
    
    # Conectar
    if client.connect():
        logger.info("🔗 Intentando conectar al broker...")
        client.start_loop()
        
        logger.info("👂 Esperando mensajes... (Ctrl+C para salir)")
        try:
            counter = 0
            while True:
                time.sleep(5)
                counter += 1
                logger.info(f"💓 Heartbeat #{counter} - Conectado: {client.is_connected}")
                
                if counter % 12 == 0:  # Cada minuto
                    logger.info("📊 Estado del cliente:")
                    logger.info(f"   🔗 Conectado: {client.is_connected}")
                    logger.info(f"   📡 Broker: {config.broker}:{config.port}")
                    logger.info(f"   🔔 Topic: {config.topic}")
                
        except KeyboardInterrupt:
            logger.info("⏹️ Interrupción del usuario detectada")
        
        client.stop_loop()
        client.disconnect()
        logger.info("🛑 Cliente MQTT desconectado")
    else:
        logger.error("❌ No se pudo conectar al broker MQTT")

if __name__ == "__main__":
    main()
