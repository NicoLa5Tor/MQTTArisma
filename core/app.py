"""
Aplicación principal escalable que ejecuta el cliente MQTT, el receptor WebSocket y el cliente Backend
"""
import logging
import time
import json
from config import AppConfig
from clients import MQTTClient, WebSocketReceiver, BackendClient
from handlers import MessageHandler
from utils import setup_logger


class ScalableMQTTApp:
    """Aplicación principal escalable para manejar múltiples empresas y tipos de mensajes"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Inicializar componentes
        self.mqtt_client = MQTTClient(config.mqtt)
        self.websocket_receiver = WebSocketReceiver(config.websocket)
        self.backend_client = BackendClient(config.backend)
        
        # Inicializar manejador de mensajes
        self.message_handler = MessageHandler(
            backend_client=self.backend_client,
            websocket_receiver=self.websocket_receiver
        )
        
        # Configurar callbacks
        self._setup_callbacks()
        
        # Estado de la aplicación
        self.is_running = False
        self.message_count = 0
        
    def _setup_callbacks(self):
        """Configurar callbacks para MQTT y WebSocket"""
        
        # Callback para mensajes MQTT
        def mqtt_message_callback(topic, payload, json_data):
            self.message_count += 1
            self.logger.info("="*120)
            self.logger.info(f"🎉 CALLBACK PRINCIPAL - MENSAJE #{self.message_count} 🎉")
            self.logger.info(f"📋 TOPIC: {topic}")
            self.logger.info(f"📋 PAYLOAD: {payload}")
            self.logger.info(f"📋 JSON_DATA: {json_data}")
            self.logger.info("="*120)
            
            # Procesar mensaje usando el manejador escalable
            success = self.message_handler.process_mqtt_message(topic, payload, json_data)
            
            if success:
                self.logger.info(f"✅ Mensaje #{self.message_count} procesado exitosamente")
            else:
                self.logger.error(f"❌ Error procesando mensaje #{self.message_count} del topic {topic}")
        
        # Callback para conexión MQTT
        def mqtt_connect_callback(client, userdata, flags, rc):
            if rc == 0:
                self.logger.info("Conectado exitosamente al broker MQTT")
                
                # Suscribirse a TODOS los topics posibles para capturar mensajes
                topics_to_subscribe = [
                    "empresas/+/+/+",          # 4 niveles
                    "empresas/+/+/+/+",        # 5 niveles
                    "empresas/+/+/+/+/+",      # 6 niveles
                    "empresas/#",              # Wildcard completo
                    "#",                       # TODO - literalmente TODO
                    "+/+/+/+",                # Cualquier estructura de 4 niveles
                    "BOTONERA",               # Topic directo BOTONERA
                    "BOTONERA/+",             # BOTONERA con subcategorías
                    "BOTONERA/+/+",           # BOTONERA con 2 subcategorías
                    "BOTONERA/+/+/+",         # BOTONERA con 3 subcategorías
                    "*/BOTONERA",             # Cualquier cosa seguida de BOTONERA
                    "*/BOTONERA/*",           # BOTONERA en el medio
                    "*/*/BOTONERA",           # BOTONERA en el tercer nivel
                    "*/*/BOTONERA/*",         # BOTONERA en el tercer nivel con subcategoría
                ]
                
                for topic in topics_to_subscribe:
                    self.mqtt_client.subscribe(topic, qos=0)
                    self.logger.info(f"🔍 Suscrito a: {topic}")
                
                self.logger.info(f"🎯 TOTAL DE SUBSCRIPCIONES: {len(topics_to_subscribe)}")
                    
            else:
                self.logger.error(f"Error conectando al MQTT: {rc}")
        
        # Callback para desconexión MQTT
        def mqtt_disconnect_callback(client, userdata, rc):
            self.logger.warning(f"Desconectado del broker MQTT: {rc}")
        
        # Callback para mensajes WebSocket
        def websocket_message_callback(message):
            self.logger.info(f"Mensaje WebSocket recibido: {message}")
            try:
                # Procesar mensaje JSON del WebSocket
                json_data = json.loads(message)
                # Aquí puedes agregar lógica para procesar mensajes del WebSocket
                self.logger.info(f"Datos WebSocket procesados: {json_data}")
            except json.JSONDecodeError:
                self.logger.error(f"Error parseando mensaje WebSocket: {message}")
        
        # Asignar callbacks
        self.mqtt_client.set_message_callback(mqtt_message_callback)
        self.mqtt_client.set_connect_callback(mqtt_connect_callback)
        self.mqtt_client.set_disconnect_callback(mqtt_disconnect_callback)
        self.websocket_receiver.set_message_callback(websocket_message_callback)
    
    def start(self):
        """Iniciar la aplicación"""
        self.logger.info("Iniciando aplicación escalable MQTT...")
        
        try:
            # Verificar conectividad del backend (opcional)
            backend_available = False
            if self.config.backend.enabled:
                try:
                    backend_available = self.backend_client.health_check()
                    if backend_available:
                        self.logger.info("✅ Backend disponible y conectado")
                    else:
                        self.logger.warning("⚠️ Backend no disponible, continuando sin backend")
                except Exception as e:
                    self.logger.warning(f"⚠️ Error verificando backend: {e}")
            else:
                self.logger.info("ℹ️ Backend deshabilitado en configuración")
            
            # Conectar MQTT (obligatorio)
            if not self.mqtt_client.connect():
                self.logger.error("❌ Error conectando al broker MQTT - Este servicio es obligatorio")
                return False
            
            self.mqtt_client.start_loop()
            self.logger.info("✅ Cliente MQTT conectado exitosamente")
            
            # Conectar WebSocket (opcional)
            websocket_connected = False
            if self.config.websocket.enabled:
                try:
                    websocket_connected = self.websocket_receiver.connect()
                    if websocket_connected:
                        self.logger.info("✅ WebSocket conectado exitosamente")
                    else:
                        self.logger.warning("⚠️ WebSocket no disponible, continuando sin WebSocket")
                except Exception as e:
                    self.logger.warning(f"⚠️ Error conectando WebSocket: {e}")
            else:
                self.logger.info("ℹ️ WebSocket deshabilitado en configuración")
            
            self.is_running = True
            
            # Resumen de servicios
            self.logger.info("🚀 Aplicación iniciada exitosamente")
            self.logger.info(f"   📡 MQTT: ✅ Conectado")
            self.logger.info(f"   🌐 Backend: {'✅ Disponible' if backend_available else '❌ No disponible'}")
            self.logger.info(f"   🔌 WebSocket: {'✅ Conectado' if websocket_connected else '❌ No conectado'}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error iniciando aplicación: {e}")
            return False
    
    def stop(self):
        """Detener la aplicación"""
        self.logger.info("Deteniendo aplicación...")
        
        self.is_running = False
        
        # Detener MQTT
        self.mqtt_client.stop_loop()
        self.mqtt_client.disconnect()
        
        # Detener WebSocket
        self.websocket_receiver.disconnect()
        
        self.logger.info("Aplicación detenida exitosamente")
    
    def run(self):
        """Ejecutar la aplicación principal"""
        if not self.start():
            return
        
        try:
            # Mostrar estadísticas cada 60 segundos
            last_stats_time = time.time()
            
            while self.is_running:
                current_time = time.time()
                
                # Mostrar estadísticas cada minuto
                if current_time - last_stats_time >= 60:
                    self._show_statistics()
                    last_stats_time = current_time
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.logger.info("Interrupción del usuario detectada")
        except Exception as e:
            self.logger.error(f"Error en bucle principal: {e}")
        finally:
            self.stop()
    
    def _show_statistics(self):
        """Mostrar estadísticas de la aplicación"""
        stats = self.message_handler.get_statistics()
        self.logger.info(f"Estadísticas: Mensajes procesados: {self.message_count}, "
                        f"Tipos de hardware soportados: {stats['hardware_types_count']}, "
                        f"MQTT conectado: {self.mqtt_client.is_connected}, "
                        f"WebSocket conectado: {self.websocket_receiver.is_connected}")
    
    def add_company(self, company_code: str, company_name: str):
        """Agregar nueva empresa dinámicamente"""
        self.message_handler.add_company(company_code, company_name)


def main():
    """Función principal"""
    # Configurar logging
    logger = setup_logger("mqtt_app", "INFO")
    
    # Crear configuración
    config = AppConfig()
    
    # Crear y ejecutar aplicación
    app = ScalableMQTTApp(config)
    app.run()


if __name__ == '__main__':
    main()
