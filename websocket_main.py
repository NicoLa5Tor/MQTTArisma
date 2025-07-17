#!/usr/bin/env python3
"""
Script principal para ejecutar solo el servidor WebSocket
"""

import asyncio
import signal
import sys
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio actual al path para las importaciones
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clients import WebSocketServer
from handlers import MessageHandler
from utils import setup_logger

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

async def main():
    """Función principal"""
    global server_instance
    
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Configurar logging
    logger = setup_logger("websocket_server", "INFO")
    
    try:
        # Obtener configuración desde variables de entorno
        websocket_host = os.getenv('WEBSOCKET_HOST', 'localhost')
        websocket_port = int(os.getenv('WEBSOCKET_PORT', '8080'))
        
        # Crear servidor WebSocket
        server_instance = WebSocketServer(
            host=websocket_host,
            port=websocket_port
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

if __name__ == "__main__":
    # Obtener configuración para mostrar
    websocket_host = os.getenv('WEBSOCKET_HOST', 'localhost')
    websocket_port = os.getenv('WEBSOCKET_PORT', '8080')
    
    print("🚀 Iniciando servidor WebSocket para mensajes de WhatsApp...")
    print(f"📡 Servidor: ws://{websocket_host}:{websocket_port}")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Adiós!")
