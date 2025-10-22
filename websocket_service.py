#!/usr/bin/env python3
"""
Servicio WebSocket independiente
Recibe mensajes de WhatsApp por WebSocket y puede enviar notificaciones MQTT.
"""

import asyncio
import signal
import sys
import os
import logging

# Agregar el directorio actual al path para las importaciones
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clients.websocket_server import WebSocketServer
from clients.backend_client import BackendClient
from services.whatsapp_service import WhatsAppService
from handlers.websocket_message_handler import WebSocketMessageHandler
from utils.logger import setup_logger
from config import AppConfig


class WebSocketService:
    """Servicio WebSocket independiente - SIN dependencias de MQTT"""
    
    def __init__(self):
        # Configuración
        self.config = AppConfig()
        # Logger con archivo separado para poder hacer tail -f
        self.logger = setup_logger(
            "websocket_service", 
            self.config.log_level,
            log_file="logs/websocket_service.log"
        )
        
        # Clientes independientes para WebSocket
        self.backend_client = BackendClient(self.config.backend)
        self.whatsapp_service = WhatsAppService(self.config.whatsapp)
        
        # Servidor WebSocket CON MQTT Publisher para envío
        self.websocket_server = WebSocketServer(
            host=self.config.websocket.host,
            port=self.config.websocket.port,
            backend_client=self.backend_client,
            whatsapp_service=self.whatsapp_service,
            enable_mqtt_publisher=True  # Habilitar envío MQTT desde WhatsApp
        )
        
        # Estado del servicio
        self.is_running = False
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Manejar señales de terminación"""
        self.logger.info("\n¡Recibida señal de terminación para servicio WebSocket!")
        asyncio.create_task(self.stop())
        sys.exit(0)
    
    async def start(self) -> bool:
        """Iniciar el servicio WebSocket"""
        self.logger.info("🚀 Iniciando servicio WebSocket independiente...")
        self.logger.info(f"📡 Servidor: ws://{self.config.websocket.host}:{self.config.websocket.port}")
        self.logger.info("📱 Procesamiento de WhatsApp con envío MQTT")
        self.logger.info("✅ MQTT Publisher habilitado para notificaciones")
        
        try:
            # Iniciar servidor WebSocket
            await self.websocket_server.start()
            self.is_running = True
            
            self.logger.info("✅ Servicio WebSocket iniciado correctamente")
            self.logger.info("📱 Esperando mensajes de WhatsApp...")
            self.logger.info("📋 Presiona Ctrl+C para detener")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error iniciando servicio WebSocket: {e}")
            return False
    
    async def run(self):
        """Ejecutar el servicio WebSocket de forma continua"""
        if not await self.start():
            self.logger.error("❌ No se pudo iniciar el servicio WebSocket")
            return False
        
        try:
            # Iniciar tarea de estadísticas periódicas
            stats_task = asyncio.create_task(self._show_statistics_periodically())
            
            try:
                # Mantener el servidor corriendo indefinidamente
                await asyncio.Future()
            finally:
                # Cancelar tarea de estadísticas
                stats_task.cancel()
                try:
                    await stats_task
                except asyncio.CancelledError:
                    pass
                    
        except KeyboardInterrupt:
            self.logger.info("Interrupción del usuario detectada")
        finally:
            await self.stop()
        
        return True
    
    async def stop(self):
        """Detener el servicio WebSocket"""
        self.logger.info("🛑 Deteniendo servicio WebSocket...")
        self.is_running = False
        
        try:
            # Detener procesamiento de cola WhatsApp
            if hasattr(self, 'websocket_server') and self.websocket_server:
                await self.websocket_server.stop_whatsapp_processing()
                
                # Mostrar estadísticas finales
                await self._show_final_statistics()
                
                # Detener servidor
                await self.websocket_server.stop()
                self.logger.info("✅ WebSocket Server detenido")
            
        except Exception as e:
            self.logger.error(f"❌ Error deteniendo servicio: {e}")
    
    async def _show_statistics_periodically(self):
        """Mostrar estadísticas del WebSocket periódicamente"""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Mostrar estadísticas cada 30 segundos
                
                if self.websocket_server and self.websocket_server.is_running:
                    stats = self.websocket_server.get_whatsapp_statistics()
                    
                    self.logger.info("📊 Estadísticas WebSocket - WhatsApp:")
                    self.logger.info(f"  • Mensajes procesados: {stats['processed_messages']}")
                    self.logger.info(f"  • Errores: {stats['error_count']}")
                    self.logger.info(f"  • Cola actual: {stats['queue_size']}/{stats['queue_max_size']}")
                    self.logger.info(f"  • Procesando: {'Sí' if stats['is_processing'] else 'No'}")
                    self.logger.info(f"  • Tasa de error: {stats['error_rate']}%")
                    self.logger.info("=" * 50)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.warning(f"⚠️ Error mostrando estadísticas WebSocket: {e}")
    
    async def _show_final_statistics(self):
        """Mostrar estadísticas finales"""
        if self.websocket_server:
            stats = self.websocket_server.get_whatsapp_statistics()
            
            self.logger.info("📊 Estadísticas finales WebSocket:")
            self.logger.info(f"  • Total de mensajes procesados: {stats['processed_messages']}")
            self.logger.info(f"  • Total de errores: {stats['error_count']}")
            self.logger.info(f"  • Mensajes pendientes: {stats['queue_size']}")
            self.logger.info(f"  • Tasa de éxito final: {100 - stats['error_rate']}%")
    
    def get_status(self) -> dict:
        """Obtener estado del servicio"""
        websocket_stats = {}
        if self.websocket_server:
            websocket_stats = self.websocket_server.get_whatsapp_statistics()
        
        return {
            "service": "WebSocket Service",
            "running": self.is_running,
            "websocket_running": self.websocket_server.is_running if self.websocket_server else False,
            "backend_enabled": self.config.backend.enabled,
            "whatsapp_enabled": self.config.whatsapp.enabled,
            "whatsapp_stats": websocket_stats
        }


async def main():
    """Función principal para ejecutar el servicio WebSocket"""
    fallback_logger = None

    try:
        websocket_service = WebSocketService()
    except Exception as exc:
        fallback_logger = setup_logger(
            "websocket_service_bootstrap",
            os.getenv("LOG_LEVEL", "INFO"),
            log_file="logs/websocket_service.log"
        )
        fallback_logger.exception("Error inicializando servicio WebSocket", exc_info=exc)
        sys.exit(1)

    try:
        await websocket_service.run()

    except Exception as exc:
        logger = websocket_service.logger if websocket_service and websocket_service.logger else fallback_logger
        if logger is None:
            logger = setup_logger(
                "websocket_service_bootstrap",
                os.getenv("LOG_LEVEL", "INFO"),
                log_file="logs/websocket_service.log"
            )
        logger.exception("Error ejecutando servicio WebSocket", exc_info=exc)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
