#!/usr/bin/env python3
"""
Script principal para ejecutar solo el servidor WebSocket
"""

import asyncio
import signal
import sys
import os
import argparse

# Agregar el directorio actual al path para las importaciones
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clients import WebSocketServer, MQTTClient, BackendClient
from clients.mqtt_publisher_lite import MQTTPublisherLite
from handlers import MessageHandler
from services.whatsapp_service import WhatsAppService
from utils import setup_logger
from config import AppConfig

# Instancia global del servidor
server_instance = None

def signal_handler(signum, frame):
    """Manejar señales para detener el servidor"""
    print("\n¡Recibida señal de terminación!")
    if server_instance:
        asyncio.create_task(server_instance.stop())
    sys.exit(0)

async def show_statistics_periodically():
    """Mostrar estadísticas periódicamente"""
    global server_instance
    
    while server_instance and server_instance.is_running:
        try:
            await asyncio.sleep(30)  # Mostrar estadísticas cada 30 segundos
            
            if server_instance:
                stats = server_instance.get_whatsapp_statistics()
                print(f"\n📊 Estadísticas WhatsApp:")
                print(f"  • Mensajes procesados: {stats['processed_messages']}")
                print(f"  • Errores: {stats['error_count']}")
                print(f"  • Cola actual: {stats['queue_size']}/{stats['queue_max_size']}")
                print(f"  • Procesando: {'Sí' if stats['is_processing'] else 'No'}")
                print(f"  • Tasa de error: {stats['error_rate']}%")
                print("=" * 50)
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"⚠️ Error mostrando estadísticas: {e}")

async def run_websocket():
    """Ejecutar solo el servidor WebSocket"""
    global server_instance
    
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Configurar logging
    logger = setup_logger("websocket_server", "INFO")
    
    try:
        # Obtener configuración centralizada
        config = AppConfig()
        
        # Crear servidor WebSocket usando la configuración
        server_instance = WebSocketServer(
            host=config.websocket.host,
            port=config.websocket.port
        )
        
        # Iniciar servidor
        await server_instance.start()
        
        logger.info("📱 Esperando mensajes de WhatsApp...")
        logger.info("🔄 Sistema de colas activado para procesamiento secuencial")
        logger.info("📋 Presiona Ctrl+C para detener")
        
        # Iniciar tarea de estadísticas
        stats_task = asyncio.create_task(show_statistics_periodically())
        
        try:
            # Mantener el servidor corriendo
            await asyncio.Future()  # Correr indefinidamente
        finally:
            # Cancelar tarea de estadísticas
            stats_task.cancel()
            try:
                await stats_task
            except asyncio.CancelledError:
                pass
        
    except KeyboardInterrupt:
        logger.info("Interrupción del usuario detectada")
    except Exception as e:
        logger.error(f"Error en servidor: {e}")
    finally:
        if server_instance:
            # Detener procesamiento de cola
            await server_instance.stop_whatsapp_processing()
            
            # Mostrar estadísticas finales
            stats = server_instance.get_whatsapp_statistics()
            print(f"\n📊 Estadísticas finales:")
            print(f"  • Mensajes procesados: {stats['processed_messages']}")
            print(f"  • Errores: {stats['error_count']}")
            print(f"  • Cola final: {stats['queue_size']} mensajes pendientes")
            
            # Detener servidor
            await server_instance.stop()

def run_mqtt():
    """Ejecutar solo el cliente MQTT"""
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Configurar logging
    logger = setup_logger("mqtt_client", "INFO")
    
    try:
        # Obtener configuración
        config = AppConfig()
        
        # Inicializar componentes
        mqtt_client = MQTTClient(config.mqtt)
        backend_client = BackendClient(config.backend)
        whatsapp_service = WhatsAppService(config.whatsapp)
        
        # Inicializar manejador de mensajes
        message_handler = MessageHandler(
            backend_client=backend_client,
            mqtt_client=mqtt_client,
            whatsapp_service=whatsapp_service,
            config=config,
            mqtt_publisher=None
        )
        
        # Configurar callbacks
        def mqtt_message_callback(topic, payload, json_data):
            logger.info(f"🎉 MENSAJE MQTT - TOPIC: {topic}")
            success = message_handler.process_mqtt_message(topic, payload, json_data)
            if success:
                logger.info(f"✅ Mensaje procesado exitosamente")
            else:
                logger.error(f"❌ Error procesando mensaje")
        
        def mqtt_connect_callback(client, userdata, flags, rc):
            if rc == 0:
                logger.info("Conectado exitosamente al broker MQTT")
                # Suscribirse a topics
                topics = ["empresas/+/+/BOTONERA/+", "empresas/#"]
                for topic in topics:
                    mqtt_client.subscribe(topic, qos=0)
                    logger.info(f"🔍 Suscrito a: {topic}")
            else:
                logger.error(f"Error conectando al MQTT: {rc}")
        
        # Asignar callbacks
        mqtt_client.set_message_callback(mqtt_message_callback)
        mqtt_client.set_connect_callback(mqtt_connect_callback)
        
        # Conectar y ejecutar
        if not mqtt_client.connect():
            logger.error("❌ Error conectando al broker MQTT")
            return
        
        mqtt_client.start_loop()
        logger.info("✅ Cliente MQTT conectado y ejecutándose")
        
        # Mantener el proceso corriendo
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupción del usuario detectada")
        finally:
            mqtt_client.stop_loop()
            mqtt_client.disconnect()
            logger.info("✅ Cliente MQTT desconectado")
            
    except Exception as e:
        logger.error(f"Error en cliente MQTT: {e}")
        sys.exit(1)

async def run_both():
    """Ejecutar ambos servicios"""
    await run_websocket()


if __name__ == "__main__":
    # Configurar parser de argumentos
    parser = argparse.ArgumentParser(description='Ejecutar servicios WebSocket y/o MQTT')
    parser.add_argument('--websocket', action='store_true', help='Ejecutar solo WebSocket')
    parser.add_argument('--mqtt', action='store_true', help='Ejecutar solo MQTT')
    
    args = parser.parse_args()
    
    # Obtener configuración centralizada
    config = AppConfig()
    
    try:
        if args.websocket:
            # Solo WebSocket
            print("🚀 Iniciando servidor WebSocket...")
            print(f"📡 Servidor: ws://{config.websocket.host}:{config.websocket.port}")
            print("=" * 60)
            asyncio.run(run_websocket())
            
        elif args.mqtt:
            # Solo MQTT
            print("🚀 Iniciando cliente MQTT...")
            print(f"📡 Broker: {config.mqtt.broker}:{config.mqtt.port}")
            print("=" * 60)
            run_mqtt()
            
        else:
            # Ambos servicios (por defecto)
            print("🚀 Iniciando servidor WebSocket...")
            print(f"📡 Servidor: ws://{config.websocket.host}:{config.websocket.port}")
            print("=" * 60)
            asyncio.run(run_both())
            
    except KeyboardInterrupt:
        print("\n👋 ¡Adiós!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
