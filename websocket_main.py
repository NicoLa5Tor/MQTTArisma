#!/usr/bin/env python3
"""
Script principal para ejecutar servicios WebSocket y/o MQTT con clientes independientes
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

# Instancias globales para cada servicio
websocket_server_instance = None
mqtt_client_instance = None

def websocket_signal_handler(signum, frame):
    """Manejar señales para detener el servidor WebSocket"""
    print("\n¡Recibida señal de terminación para WebSocket!")
    global websocket_server_instance
    if websocket_server_instance:
        asyncio.create_task(websocket_server_instance.stop())
    sys.exit(0)

def mqtt_signal_handler(signum, frame):
    """Manejar señales para detener el cliente MQTT"""
    print("\n¡Recibida señal de terminación para MQTT!")
    global mqtt_client_instance
    if mqtt_client_instance:
        mqtt_client_instance.stop_loop()
        mqtt_client_instance.disconnect()
    sys.exit(0)

async def show_websocket_statistics_periodically():
    """Mostrar estadísticas del WebSocket periódicamente"""
    global websocket_server_instance
    
    while websocket_server_instance and websocket_server_instance.is_running:
        try:
            await asyncio.sleep(30)  # Mostrar estadísticas cada 30 segundos
            
            if websocket_server_instance:
                stats = websocket_server_instance.get_whatsapp_statistics()
                print(f"\n📊 Estadísticas WebSocket - WhatsApp:")
                print(f"  • Mensajes procesados: {stats['processed_messages']}")
                print(f"  • Errores: {stats['error_count']}")
                print(f"  • Cola actual: {stats['queue_size']}/{stats['queue_max_size']}")
                print(f"  • Procesando: {'Sí' if stats['is_processing'] else 'No'}")
                print(f"  • Tasa de error: {stats['error_rate']}%")
                print("=" * 50)
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"⚠️ Error mostrando estadísticas WebSocket: {e}")

async def run_websocket():
    """Ejecutar solo el servidor WebSocket con sus propios clientes"""
    global websocket_server_instance
    
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, websocket_signal_handler)
    signal.signal(signal.SIGTERM, websocket_signal_handler)
    
    # Configurar logging
    logger = setup_logger("websocket_server", "INFO")
    
    try:
        # Obtener configuración centralizada
        config = AppConfig()
        
        # Crear clientes independientes para WebSocket
        websocket_backend_client = BackendClient(config.backend)
        websocket_whatsapp_service = WhatsAppService(config.whatsapp)
        
        # Crear servidor WebSocket con clientes independientes
        websocket_server_instance = WebSocketServer(
            host=config.websocket.host,
            port=config.websocket.port,
            enable_mqtt=False,  # Desactivar MQTT en WebSocket
            backend_client=websocket_backend_client,
            whatsapp_service=websocket_whatsapp_service
        )
        
        # Iniciar servidor
        await websocket_server_instance.start()
        
        logger.info("📱 Esperando mensajes de WhatsApp...")
        logger.info("🔄 Sistema de colas activado para procesamiento secuencial")
        logger.info("📋 Presiona Ctrl+C para detener")
        
        # Iniciar tarea de estadísticas
        stats_task = asyncio.create_task(show_websocket_statistics_periodically())
        
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
        if websocket_server_instance:
            # Detener procesamiento de cola
            await websocket_server_instance.stop_whatsapp_processing()
            
            # Mostrar estadísticas finales
            stats = websocket_server_instance.get_whatsapp_statistics()
            print(f"\n📊 Estadísticas finales WebSocket:")
            print(f"  • Mensajes procesados: {stats['processed_messages']}")
            print(f"  • Errores: {stats['error_count']}")
            print(f"  • Cola final: {stats['queue_size']} mensajes pendientes")
            
            # Detener servidor
            await websocket_server_instance.stop()

def run_mqtt():
    """Ejecutar solo el cliente MQTT con sus propios clientes"""
    global mqtt_client_instance
    
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, mqtt_signal_handler)
    signal.signal(signal.SIGTERM, mqtt_signal_handler)
    
    # Configurar logging
    logger = setup_logger("mqtt_client", "INFO")
    
    try:
        # Obtener configuración
        config = AppConfig()
        
        # Crear clientes independientes para MQTT
        mqtt_backend_client = BackendClient(config.backend)
        mqtt_whatsapp_service = WhatsAppService(config.whatsapp)  # Para ENVIAR mensajes
        mqtt_publisher = MQTTPublisherLite(config.mqtt)
        
        # Inicializar cliente MQTT
        mqtt_client_instance = MQTTClient(config.mqtt)
        
        # Inicializar manejador de mensajes para MQTT (con WhatsApp para ENVIAR)
        mqtt_message_handler = MessageHandler(
            backend_client=mqtt_backend_client,
            mqtt_client=mqtt_client_instance,
            whatsapp_service=mqtt_whatsapp_service,  # Para ENVIAR mensajes
            config=config,
            mqtt_publisher=mqtt_publisher
        )
        
        # Configurar callbacks
        def mqtt_message_callback(topic, payload, json_data):
            logger.info(f"🎉 MENSAJE MQTT - TOPIC: {topic}")
            success = mqtt_message_handler.process_mqtt_message(topic, payload, json_data)
            if success:
                logger.info(f"✅ Mensaje procesado exitosamente")
            else:
                logger.error(f"❌ Error procesando mensaje")
        
        def mqtt_connect_callback(client, userdata, flags, rc):
            if rc == 0:
                logger.info("🔥 Conectado exitosamente al broker MQTT")
                # Suscribirse a topics
                topics = ["empresas/+/+/BOTONERA/+", "empresas/#"]
                for topic in topics:
                    mqtt_client_instance.subscribe(topic, qos=0)
                    logger.info(f"🔍 Suscrito a: {topic}")
            else:
                logger.error(f"Error conectando al MQTT: {rc}")
        
        # Asignar callbacks
        mqtt_client_instance.set_message_callback(mqtt_message_callback)
        mqtt_client_instance.set_connect_callback(mqtt_connect_callback)
        
        # Conectar y ejecutar
        if not mqtt_client_instance.connect():
            logger.error("❌ Error conectando al broker MQTT")
            return
        
        mqtt_client_instance.start_loop()
        logger.info("✅ Cliente MQTT conectado y ejecutándose")
        
        # Mantener el proceso corriendo
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupción del usuario detectada")
        finally:
            mqtt_client_instance.stop_loop()
            mqtt_client_instance.disconnect()
            logger.info("✅ Cliente MQTT desconectado")
            
    except Exception as e:
        logger.error(f"Error en cliente MQTT: {e}")
        sys.exit(1)

async def run_both():
    """Ejecutar ambos servicios de forma paralela con clientes independientes"""
    # Configurar logging
    logger = setup_logger("combined_services", "INFO")
    
    try:
        # Crear tareas para ambos servicios
        logger.info("🚀 Iniciando ambos servicios (WebSocket y MQTT)...")
        
        # Iniciar solo tareas necesarias dependiendo de la elección
        # Esto separa por completo la lógica en vez de iniciar uno en el otro
        websocket_task = asyncio.create_task(run_websocket())
        
        # Nota: no inicializar el WebSocket cuando se ejecuta MQTT
        mqtt_task = asyncio.create_task(run_mqtt_async())
        
        # Ejecutar las tareas necesarias
        await asyncio.gather(websocket_task, mqtt_task)
        
    except KeyboardInterrupt:
        logger.info("Interrupción del usuario detectada")
    except Exception as e:
        logger.error(f"Error ejecutando servicios: {e}")
    finally:
        logger.info("✅ Ambos servicios terminados")

async def run_websocket():
    """Ejecutar solo el servidor WebSocket con sus propios clientes"""
    global websocket_server_instance
    
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, websocket_signal_handler)
    signal.signal(signal.SIGTERM, websocket_signal_handler)
    
    # Configurar logging
    logger = setup_logger("websocket_server", "INFO")
    
    try:
        # Obtener configuración centralizada
        config = AppConfig()
        
        # Crear clientes independientes para WebSocket
        websocket_backend_client = BackendClient(config.backend)
        websocket_whatsapp_service = WhatsAppService(config.whatsapp)
        
        # Crear servidor WebSocket con clientes independientes
        websocket_server_instance = WebSocketServer(
            host=config.websocket.host,
            port=config.websocket.port,
            enable_mqtt=False,  # Desactivar MQTT en WebSocket
            backend_client=websocket_backend_client,
            whatsapp_service=websocket_whatsapp_service
        )
        
        # Iniciar servidor
        await websocket_server_instance.start()
        
        logger.info("📱 Esperando mensajes de WhatsApp...")
        logger.info("🔄 Sistema de colas activado para procesamiento secuencial")
        logger.info("📋 Presiona Ctrl+C para detener")
        
        # Iniciar tarea de estadísticas
        stats_task = asyncio.create_task(show_websocket_statistics_periodically())
        
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
        if websocket_server_instance:
            # Detener procesamiento de cola
            await websocket_server_instance.stop_whatsapp_processing()
            
            # Mostrar estadísticas finales
            stats = websocket_server_instance.get_whatsapp_statistics()
            print(f"\n📊 Estadísticas finales WebSocket:")
            print(f"  • Mensajes procesados: {stats['processed_messages']}")
            print(f"  • Errores: {stats['error_count']}")
            print(f"  • Cola final: {stats['queue_size']} mensajes pendientes")
            
            # Detener servidor
            await websocket_server_instance.stop()

async def run_mqtt_async():
    """Función asíncrona para ejecutar MQTT"""
    loop = asyncio.get_event_loop()
    
    # Ejecutar la función MQTT en un hilo separado
    def mqtt_thread():
        run_mqtt()
    
    # Crear y ejecutar el hilo
    import threading
    mqtt_thread_instance = threading.Thread(target=mqtt_thread)
    mqtt_thread_instance.daemon = True
    mqtt_thread_instance.start()
    
    # Esperar a que el hilo termine
    while mqtt_thread_instance.is_alive():
        await asyncio.sleep(0.1)


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
