#!/usr/bin/env python3
"""
Script para publicar mensajes de prueba al topic empresas
"""
import sys
import os
import time
import json
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
    logger.info("🚀 Iniciando publicador de prueba MQTT...")
    
    # Crear configuración
    config = MQTTConfig()
    config.client_id = "TEST_PUBLISHER"  # Cambiar ID para evitar conflictos
    
    logger.info(f"📡 Configuración MQTT:")
    logger.info(f"   Broker: {config.broker}:{config.port}")
    logger.info(f"   Usuario: {config.username}")
    logger.info(f"   Client ID: {config.client_id}")
    
    # Crear cliente
    client = MQTTClient(config)
    
    # Callback para conexión
    def on_connected(client, userdata, flags, rc):
        if rc == 0:
            logger.info("✅ ¡Conectado exitosamente al broker MQTT!")
        else:
            logger.error(f"❌ Error conectando: {rc}")
    
    # Configurar callbacks
    client.set_connect_callback(on_connected)
    
    # Conectar
    if client.connect():
        logger.info("🔗 Intentando conectar al broker...")
        client.start_loop()
        
        # Esperar a que se conecte
        time.sleep(2)
        
        if client.is_connected:
            logger.info("📤 Publicando mensajes de prueba...")
            
            # Mensajes de prueba
            test_messages = [
                {
                    "topic": "empresas/acme/sede1/semaforo",
                    "data": {
                        "timestamp": int(time.time()),
                        "empresa": "acme",
                        "sede": "sede1",
                        "hardware": "semaforo",
                        "estado": "verde",
                        "duracion": 30
                    }
                },
                {
                    "topic": "empresas/tech/bogota/sensor",
                    "data": {
                        "timestamp": int(time.time()),
                        "empresa": "tech",
                        "sede": "bogota",
                        "hardware": "sensor",
                        "temperatura": 25.5,
                        "humedad": 60
                    }
                },
                {
                    "topic": "empresas/industrial/medellin/alarma",
                    "data": {
                        "timestamp": int(time.time()),
                        "empresa": "industrial",
                        "sede": "medellin",
                        "hardware": "alarma",
                        "tipo": "incendio",
                        "activa": True
                    }
                }
            ]
            
            for i, msg in enumerate(test_messages):
                logger.info(f"📨 Publicando mensaje {i+1}/{len(test_messages)}")
                logger.info(f"   📂 Topic: {msg['topic']}")
                logger.info(f"   📄 Data: {msg['data']}")
                
                success = client.publish_json(msg['topic'], msg['data'])
                if success:
                    logger.info("   ✅ Mensaje publicado exitosamente")
                else:
                    logger.error("   ❌ Error publicando mensaje")
                
                time.sleep(1)
            
            logger.info("🎉 Todos los mensajes han sido publicados!")
            
        else:
            logger.error("❌ No se pudo conectar al broker MQTT")
        
        client.stop_loop()
        client.disconnect()
        logger.info("🛑 Cliente MQTT desconectado")
    else:
        logger.error("❌ No se pudo conectar al broker MQTT")

if __name__ == "__main__":
    main()
