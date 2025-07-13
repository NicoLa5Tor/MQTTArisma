#!/usr/bin/env python3
"""
Script de prueba integral para verificar todo el sistema
"""
import sys
import os
import time
import json
import logging
import threading
from datetime import datetime

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import AppConfig
from core import ScalableMQTTApp
from clients import MQTTClient
from config.settings import MQTTConfig

def setup_logging():
    """Configurar logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def create_test_publisher():
    """Crear cliente publicador de prueba"""
    logger = logging.getLogger("publisher")
    
    # Configuración del publicador
    config = MQTTConfig()
    config.client_id = "TEST_PUBLISHER_FULL"
    
    client = MQTTClient(config)
    
    def on_connected(client, userdata, flags, rc):
        if rc == 0:
            logger.info("📤 Publicador conectado exitosamente")
        else:
            logger.error(f"❌ Error conectando publicador: {rc}")
    
    client.set_connect_callback(on_connected)
    return client, logger

def publisher_thread_func(client, logger):
    """Función para ejecutar en hilo separado del publicador"""
    if not client.connect():
        logger.error("❌ No se pudo conectar el publicador")
        return
    
    client.start_loop()
    time.sleep(2)  # Esperar conexión
    
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
    
    logger.info("🚀 Iniciando publicación de mensajes de prueba...")
    
    for i in range(3):  # Publicar 3 rondas
        logger.info(f"📨 Ronda {i+1}/3 de publicación")
        
        for j, msg in enumerate(test_messages):
            logger.info(f"   📤 Publicando mensaje {j+1}/{len(test_messages)}: {msg['topic']}")
            
            success = client.publish_json(msg['topic'], msg['data'])
            if success:
                logger.info(f"   ✅ Publicado exitosamente")
            else:
                logger.error(f"   ❌ Error publicando")
            
            time.sleep(2)  # Esperar entre mensajes
        
        time.sleep(5)  # Esperar entre rondas
    
    logger.info("🎉 Publicación completada")
    client.stop_loop()
    client.disconnect()

def main():
    logger = setup_logging()
    logger.info("🚀 PRUEBA INTEGRAL DEL SISTEMA MQTT")
    logger.info("=" * 60)
    
    # Crear la aplicación principal
    config = AppConfig()
    app = ScalableMQTTApp(config)
    
    # Crear publicador de prueba
    publisher, pub_logger = create_test_publisher()
    
    # Iniciar aplicación principal en hilo separado
    def run_app():
        try:
            app.run()
        except Exception as e:
            logger.error(f"Error en aplicación principal: {e}")
    
    app_thread = threading.Thread(target=run_app)
    app_thread.daemon = True
    app_thread.start()
    
    # Esperar a que la aplicación se inicie
    time.sleep(3)
    
    # Iniciar publicador en hilo separado
    pub_thread = threading.Thread(target=publisher_thread_func, args=(publisher, pub_logger))
    pub_thread.daemon = True
    pub_thread.start()
    
    # Esperar a que termine la publicación
    pub_thread.join()
    
    # Esperar un poco más para ver resultados
    logger.info("⏳ Esperando para ver resultados...")
    time.sleep(10)
    
    # Detener aplicación
    logger.info("🛑 Deteniendo aplicación...")
    app.stop()
    
    logger.info("✅ Prueba integral completada")

if __name__ == "__main__":
    main()
