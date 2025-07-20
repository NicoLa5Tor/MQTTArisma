"""
Manejador de mensajes WebSocket puro - SIN MQTT
Solo procesa mensajes entrantes de WhatsApp desde webhooks
"""
import json
import logging
import asyncio
from asyncio import Queue
from typing import Dict, Any, Optional
from utils.redis_queue_manager import RedisQueueManager


class WebSocketMessageHandler:
    """Manejador de mensajes WebSocket puro - SIN dependencias de MQTT"""
    
    def __init__(self, backend_client, whatsapp_service=None, config=None):
        self.backend_client = backend_client
        self.whatsapp_service = whatsapp_service
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Estadísticas solo para WhatsApp
        self.whatsapp_processed_count = 0
        self.whatsapp_error_count = 0
        
        # Sistema de colas Redis para mensajes de WhatsApp ENTRANTES
        self.redis_queue = None
        if whatsapp_service:
            try:
                redis_config = config.redis if config else None
                self.redis_queue = RedisQueueManager(redis_config)
                self.redis_queue.start_workers(self._process_single_whatsapp_message_sync)
                self.logger.info("✅ Sistema de colas Redis iniciado para WhatsApp")
            except Exception as e:
                self.logger.error(f"❌ Error iniciando Redis, usando cola en memoria: {e}")
                self.redis_queue = None
        
        # Cola en memoria como fallback
        self.whatsapp_queue = Queue(maxsize=1000)
        self.is_processing = False
        self._queue_task = None
        
        self.logger.info("📱 WebSocket Message Handler - SOLO procesamiento WhatsApp")
        self.logger.info("❌ SIN procesamiento de mensajes MQTT")

    async def queue_whatsapp_message(self, message: str) -> bool:
        """Agregar mensaje de WhatsApp a la cola para procesamiento"""
        try:
            # Usar Redis si está disponible
            if self.redis_queue and self.redis_queue.is_healthy():
                return self.redis_queue.add_message(message)
            else:
                # Fallback a cola en memoria
                await self.whatsapp_queue.put(message)
                
                # Iniciar el procesador de cola si no está corriendo
                if not self.is_processing:
                    self._queue_task = asyncio.create_task(self._process_whatsapp_queue())
                return True
        except asyncio.QueueFull:
            self.logger.warning(f"⚠️ Cola de WhatsApp llena, descartando mensaje")
            self.whatsapp_error_count += 1
            return False
        except Exception as e:
            self.logger.error(f"❌ Error agregando mensaje a cola: {e}")
            self.whatsapp_error_count += 1
            return False

    async def _process_whatsapp_queue(self):
        """Procesar mensajes de WhatsApp desde la cola de forma secuencial"""
        self.is_processing = True
        self.logger.info("🔄 Iniciando procesador de cola de WhatsApp")
        
        try:
            while True:
                try:
                    # Obtener el siguiente mensaje de la cola
                    message = await self.whatsapp_queue.get()
                    
                    # Procesar el mensaje
                    await self._process_single_whatsapp_message(message)
                    
                    # Marcar la tarea como completada
                    self.whatsapp_queue.task_done()
                    
                except asyncio.CancelledError:
                    self.logger.info("🛑 Procesador de cola cancelado")
                    break
                except Exception as e:
                    self.logger.error(f"❌ Error procesando mensaje de cola: {e}")
                    self.whatsapp_error_count += 1
                    
        finally:
            self.is_processing = False
            self.logger.info("🔄 Procesador de cola de WhatsApp detenido")

    def _process_single_whatsapp_message_sync(self, message: str) -> bool:
        """Procesar un solo mensaje de WhatsApp (versión síncrona para Redis)"""
        try:
            # Parsear JSON
            json_message = json.loads(message)
            
            # Validar estructura del mensaje antes de procesar
            if (not self._is_valid_whatsapp_webhook(json_message)):
                return True  # No es un error, simplemente ignoramos
            
            entry = json_message["entry"][0]["changes"][0]["value"]["messages"][0]
            
            # Obtener número
            number_client = entry["from"]
            
            # Validar si el usuario ya existe 
            save_message = json_message.get("save_number")
            if save_message:
                # Usuario guardado
                cached_info = json_message["cached_info"]
                self._process_save_number(entry=entry, cached_info=cached_info)
            else:
                # Usuario nuevo
                response_verify = self._process_new_number_sync(number=number_client, entry=entry)
                if not response_verify:
                    if self.whatsapp_service:
                        self.whatsapp_service.send_individual_message(
                            phone=number_client, 
                            message="Lo siento 😞, Pero actualmente no te encuentras registrado en el sistema RESCUE."
                        )
            
            self.logger.info(f"📱 Mensaje WhatsApp #{self.whatsapp_processed_count + 1}:")
            self.logger.info(f"   📞 Número: {number_client}")
            
            self.whatsapp_processed_count += 1
            return True
            
        except json.JSONDecodeError:
            self.logger.error(f"❌ Error: Mensaje no es JSON válido")
            self.whatsapp_error_count += 1
            return False
        except Exception as e:
            self.logger.error(f"❌ Error procesando mensaje: {e}")
            self.whatsapp_error_count += 1
            return False

    async def _process_single_whatsapp_message(self, message: str) -> None:
        """Procesar un solo mensaje de WhatsApp (versión asíncrona para fallback)"""
        try:
            # Parsear JSON
            json_message = json.loads(message)
            
            # Validar estructura del mensaje antes de procesar
            if not self._is_valid_whatsapp_webhook(json_message):
                return
                
            entry = json_message["entry"][0]["changes"][0]["value"]["messages"][0]
            number_client = entry["from"]
            type_message = entry["type"]
            
            # Validar si el usuario ya existe 
            save_message = json_message.get("save_number", False)
            if save_message:
                # Usuario guardado
                cached_info = json_message.get("cached_info", {})
                self._process_save_number(entry=entry, cached_info=cached_info)
            else:
                # Usuario nuevo
                await self._process_new_number(number=number_client)
                
            self.logger.info(f"📱 Mensaje WhatsApp #{self.whatsapp_processed_count + 1}:")
            self.logger.info(f"   📞 Número: {number_client}")
            self.logger.info(f"   📋 Tipo: {type_message}")
            
            self.whatsapp_processed_count += 1
            
        except json.JSONDecodeError:
            self.logger.error(f"❌ Error: Mensaje no es JSON válido")
            self.whatsapp_error_count += 1
        except Exception as e:
            self.logger.error(f"❌ Error procesando mensaje: {e}")
            self.whatsapp_error_count += 1

    def _is_valid_whatsapp_webhook(self, json_message: Dict) -> bool:
        """Validar si el mensaje es un webhook válido de WhatsApp"""
        try:
            return (
                "entry" in json_message and 
                json_message["entry"] and 
                "changes" in json_message["entry"][0] and
                json_message["entry"][0]["changes"] and
                "value" in json_message["entry"][0]["changes"][0] and
                "messages" in json_message["entry"][0]["changes"][0]["value"] and
                json_message["entry"][0]["changes"][0]["value"]["messages"]
            )
        except (KeyError, IndexError, TypeError):
            return False

    def _process_save_number(self, entry: Dict, cached_info: Dict) -> None:
        """Procesar mensaje de número guardado"""
        if not cached_info or not self.whatsapp_service:
            return
            
        number = cached_info["phone"]
        user = cached_info["name"]
        type_message = entry["type"]
        
        is_alarm = entry[type_message].get("list_reply", False)
        if is_alarm:
            self.logger.info("Procesando selección de alarma")
            alarm_id = is_alarm["id"]
            return
            
        is_down_alarm = entry[type_message].get("button_reply", False)
        if is_down_alarm:
            self.logger.info("Procesando apagar alarma")
            # Aquí puedes agregar lógica para apagar alarmas
            
        # Enviar lista de alarmas
        self._send_create_alarma(number=number, usuario=user, is_in_cached=True)

    def _process_new_number_sync(self, number: str, entry: Dict = None) -> Optional[bool]:
        """Procesar nuevo número (versión síncrona para Redis)"""
        if not self.backend_client:
            return False
            
        response = self.backend_client.verify_user_number(number)
        
        # Verificar si la respuesta es None (error de conexión)
        if response is None:
            self.logger.error("❌ Sin respuesta del servidor")
            return False
            
        # Verificar códigos de estado específicos
        status_code = response.get('_status_code', 200)
        
        if status_code == 404:
            self.logger.info("🔍 Usuario no encontrado (404)")
            return False
        elif status_code == 401:
            self.logger.info("🔒 No autorizado (401)")
            return False
        
        # Para respuestas exitosas, obtener los datos
        if not response.get('success', False):
            self.logger.error(f"❌ Verificación fallida: {response.get('message', 'Error desconocido')}")
            return False
        
        verify_number = response.get("data")
        if verify_number is None or "telefono" not in verify_number:
            self.logger.error("❌ Datos de usuario incompletos")
            return False
            
        usuario = verify_number.get("nombre", "")
        
        # Agregar número al cache de WhatsApp
        if self.whatsapp_service:
            response_verify = self.whatsapp_service.add_number_to_cache(
                phone=verify_number["telefono"],           
                name=verify_number.get("nombre", ""),           
                data={
                    "id": verify_number.get("id"),
                    "empresa": verify_number.get("empresa"),
                    "sede": verify_number.get("sede")
                }          
            )
            if not response_verify:
                return False
        
        # Procesar tipo de mensaje si existe
        if entry:
            type_message = entry["type"]
            is_down_alarm = entry[type_message].get("list_reply", False)
            if is_down_alarm:
                is_normal = is_down_alarm["id"] if "NORMAL" in is_down_alarm.get("id", "") else False
                if is_normal:
                    return True
        
        # Enviar lista de alarmas
        self._send_create_alarma(number=number, usuario=usuario)
        return True

    async def _process_new_number(self, number: str) -> None:
        """Procesar nuevo número (versión asíncrona para fallback)"""
        if not self.backend_client:
            return
            
        verify_number = self.backend_client.verify_user_number(number)
        self.logger.info(f"Verificación de número: {verify_number}")

    def _send_create_alarma(self, number, usuario, is_in_cached: bool = False) -> bool:
        """Crear y enviar lista de alarmas por WhatsApp"""
        if not self.whatsapp_service:
            self.logger.warning("⚠️ WhatsApp service no disponible")
            return False
            
        try:
            sections = [
                {
                    "title": "Servicios técnicos",
                    "rows": [
                        {
                            "id": "ROJO",
                            "title": "Incendio", 
                            "description": "Alerta por incendio"
                        },
                        {
                            "id": "AZUL",
                            "title": "Inundación", 
                            "description": "Alerta por inundación"
                        },
                        {
                            "id": "AMARILLO",
                            "title": "Peligro químico", 
                            "description": "Exposición a sustancias químicas nocivas"
                        },
                        {
                            "id": "VERDE",
                            "title": "Robo", 
                            "description": "Riesgo de robo o hurto"
                        },
                        {
                            "id": "NARANJA",
                            "title": "Terremoto", 
                            "description": "Alerta por de sismo o terremoto"
                        }
                    ]
                }
            ]
            
            body_text = f"Hola de nuevo {usuario}.\nUn gusto tenerte de vuelta" if is_in_cached else f"Hola {usuario}.\nBienvenido al Sistema de Alertas RESCUE"
            
            self.whatsapp_service.send_list_message(
                phone=number,
                header_text=body_text,
                body_text="Selecciona la alerta que deseas activar",
                footer_text="RESCUE SYSTEM",
                button_text="Ver alertas",
                sections=sections
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error creando alarma: {e}")
            return False

    def get_whatsapp_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del procesador de WhatsApp"""
        return {
            "processed_messages": self.whatsapp_processed_count,
            "error_count": self.whatsapp_error_count,
            "error_rate": round(self.whatsapp_error_count / max(self.whatsapp_processed_count, 1) * 100, 2),
            "queue_size": self.whatsapp_queue.qsize(),
            "queue_max_size": self.whatsapp_queue.maxsize,
            "is_processing": self.is_processing
        }

    async def stop_whatsapp_processing(self):
        """Detener el procesamiento de la cola de WhatsApp"""
        # Detener workers de Redis si existen
        if self.redis_queue:
            self.redis_queue.stop_workers()
        
        # Detener cola en memoria si existe
        if hasattr(self, '_queue_task') and self._queue_task and not self._queue_task.done():
            self._queue_task.cancel()
            try:
                await self._queue_task
            except asyncio.CancelledError:
                pass
        
        if hasattr(self, 'is_processing'):
            self.is_processing = False
        
        self.logger.info("🛑 Procesador de WhatsApp detenido")

    async def clear_whatsapp_queue(self):
        """Limpiar la cola de WhatsApp"""
        cleared_count = 0
        while not self.whatsapp_queue.empty():
            try:
                self.whatsapp_queue.get_nowait()
                self.whatsapp_queue.task_done()
                cleared_count += 1
            except asyncio.QueueEmpty:
                break
        
        self.logger.info(f"🗑️ Cola de WhatsApp limpiada: {cleared_count} mensajes eliminados")
        return cleared_count
