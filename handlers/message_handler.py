"""
Manejador de mensajes MQTT para BOTONERA
"""
import json
import logging
import threading
import os
import time
import asyncio
from asyncio import Queue
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from utils.redis_queue_manager import RedisQueueManager

# Cargar variables de entorno
load_dotenv()
class MessageHandler:
    """Manejador de mensajes MQTT para BOTONERA"""
    
    def __init__(self, backend_client, mqtt_client=None, whatsapp_service=None, config=None, mqtt_publisher=None):
        
        self.backend_client = backend_client
        self.mqtt_client = mqtt_client
        self.mqtt_publisher = mqtt_publisher
        self.whatsapp_service = whatsapp_service
        self.config = config
        self.logger = logging.getLogger(__name__)
        # Estadísticas
        self.processed_messages = 0
        self.error_count = 0
        
        # Sistema de colas Redis para mensajes de WhatsApp
        try:
            # Pasar configuración Redis específica si está disponible
            redis_config = config.redis if config else None
            self.redis_queue = RedisQueueManager(redis_config)
            self.redis_queue.start_workers(self._process_single_whatsapp_message_sync)
            self.logger.info("✅ Sistema de colas Redis iniciado")
        except Exception as e:
            self.logger.error(f"❌ Error iniciando Redis, usando cola en memoria: {e}")
            # Fallback a cola en memoria si Redis no está disponible
            self.redis_queue = None
            
        # Siempre inicializar cola en memoria como fallback
        self.whatsapp_queue = Queue(maxsize=1000)
        self.is_processing = False
        self._queue_task = None
        
        self.whatsapp_processed_count = 0
        self.whatsapp_error_count = 0
        # Usar settings en lugar de .env directo
        self.pathern_topic = config.mqtt.topic if config else "empresas"

    def process_mqtt_message(self, topic: str, payload: str, json_data: Optional[Dict] = None) -> bool:
        """FILTRO ABSOLUTO PARA BOTONERA - Solo procesar topics que terminen después del hardware"""
        
        # SOLO PROCESAR SI EL TOPIC CONTIENE "BOTONERA"
        if "BOTONERA" in topic:
            topic_parts = topic.split("/")
            
            # Buscar la posición de BOTONERA
            botonera_index = -1
            for i, part in enumerate(topic_parts):
                if "BOTONERA" in part:
                    botonera_index = i
                    break
            
            # Verificar que después de BOTONERA hay exactamente 1 parte más (el nombre del hardware)
            # y que no hay nada después (o solo una barra final vacía)
            if botonera_index != -1 and botonera_index + 1 < len(topic_parts):
                # Obtener partes después de BOTONERA
                parts_after_botonera = topic_parts[botonera_index + 1:]
                
                # Filtrar partes vacías (por barras al final como "/")
                parts_after_botonera = [part for part in parts_after_botonera if part.strip()]
                
                # Solo procesar si hay exactamente 1 parte después de BOTONERA
                if len(parts_after_botonera) == 1:
                    hardware_name = parts_after_botonera[0]
                    
                    print(f"🚨 BOTONERA: {hardware_name} - {topic}")
                    
                    # Procesar JSON de BOTONERA (cualquier estructura)
                    try:
                        json_data = json.loads(payload)
                        
                        # ENVIAR DATOS AL BACKEND (usando hilo)
                        self._send_botonera_to_backend(hardware_name, json_data, topic, payload)
                        
                        # El procesamiento se hace en un hilo separado
                        print(f"✅ Mensaje enviado a procesamiento en hilo")
                        
                        self.processed_messages += 1
                        return True
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON inválido: {e}")
                        self.error_count += 1
                        return False
                    except Exception as e:
                        print(f"❌ Error procesando: {e}")
                        self.error_count += 1
                        return False
                else:
                    # Ignorar si hay más de 1 parte después de BOTONERA
                    return True
            else:
                # No hay partes después de BOTONERA, ignorar
                return True
        
        # IGNORAR CUALQUIER TOPIC QUE NO CONTENGA "BOTONERA"
        else:
            # No mostrar ni procesar otros topics
            return True  # Retorna True pero no hace nada

    def _send_botonera_to_backend(self, hardware_name: str, data: Dict, topic: str, payload: str) -> None:
        """Enviar mensaje de BOTONERA al backend usando un nuevo hilo"""
        thread = threading.Thread(target=self._send_alarm_thread, args=(hardware_name, data, topic, payload))
        thread.start()
    def _send_alarm_thread(self, hardware_name: str, data: Dict, topic: str, payload: str):
        """Enviar mensaje de BOTONERA al backend"""
        try:
            # Extraer datos reales del topic: empresas/nombre_empresa/sede_empresa/BOTONERA/nombre_hardware
            topic_parts = topic.split("/")
            
            # Validar estructura del topic
            if len(topic_parts) < 5 or topic_parts[0] != "empresas":
                print(f"❌ Formato de topic inválido")
                return False
            # Extraer partes del topic
            empresa = topic_parts[1]
            sede = topic_parts[2] 
            tipo_hardware = topic_parts[3]  # BOTONERA
            nombre_hardware = topic_parts[4]
            # Crear estructura de datos con SOLO los campos requeridos
            mqtt_data = {
                "empresa": empresa,
                "sede": sede,
                "tipo_hardware": tipo_hardware,
                "nombre_hardware": nombre_hardware,
                "data": data
            }
            # Autenticar y enviar alarma
            token = self.backend_client.authenticate_hardware(mqtt_data)
            
            if not token:
                print(f"❌ Autenticación fallida")
                return False
            
            response = self.backend_client.send_alarm_data(mqtt_data, token)
            
            if response:
                self._handle_alarm_notifications(response, mqtt_data)
                return True
            else:
                print(f"❌ Error enviando alarma")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    def _handle_alarm_notifications(self, response: Dict, mqtt_data: Dict) -> None:
        """Procesar respuesta del backend y enviar notificaciones"""
        try:
            # print(" RESPUESTA DEL BACKEND:")
            # print(json.dumps(response, indent=4))
            self._send_mqtt_message(data=response)
            self._send_broadcast_personalized_message(data=response)
            print("ℹ️ Procesamiento de notificaciones completado")
        except Exception as e:
            print(f"❌ Error manejando notificaciones: {e}")
            self.logger.error(f"Error en notificaciones: {e}")
    def _send_mqtt_message(self, data) -> None:
         # Procesar topics de otros hardware (MQTT)
            if "topics_otros_hardware" in data:
                other_hardwars = data["topics_otros_hardware"]
                for item in other_hardwars:
                    item = self.pathern_topic + "/" + item
                    if "SEMAFORO" in item:
                        messsage_data = {
                            "action": "activar botonera",
                            "semaforo": "mensaje para activar semaforo",
                           
                        }
                    elif "BOTONERA" in item:
                        messsage_data = {
                            "action": "activar botone",
                            "botonera": "mensaje para enviar",
                        }
                    else:
                        messsage_data = {
                            "action": "generic",
                            "message": "notificación genérica",
                        }
                    
                    self.send_mqtt_message(topic=item, message_data=messsage_data)
    def _send_broadcast_personalized_message(self, data) -> None:
        print(f"la data es {json.dumps(data,indent=4)}")
        numeros_data = data["numeros_telefonicos"]
        tipo_alarma_info = data.get("tipo_alarma_info",{})
        recipients = []
        for item in numeros_data:
            data_item = {
                "phone":item["numero"],
                "body_text": f"Hola {item.get("nombre","")}.\nRESCUE te informa sobre una alerta de {tipo_alarma_info.get("nombre")}"
            }
            recipients.append(data_item)
        self.whatsapp_service.send_personalized_broadcast(
            recipients= recipients,
            header_type="image",
            header_content=tipo_alarma_info.get("imagen_base64",""),
            button_text="Más detalles",
            button_url="https://mi-app.com/update",
            footer_text="Equipo RESCUE",
            use_queue=True
        )

        return

    def send_mqtt_message(self, topic: str, message_data: Dict, qos: int = 0) -> bool:
        """
        Función para enviar mensajes MQTT a un topic específico.
        
        Args:
            topic: Topic MQTT donde enviar el mensaje
            message_data: Datos JSON para enviar
            qos: Calidad de servicio (0, 1, 2)
            
        Returns:
            bool: True si el mensaje se envió correctamente, False en caso contrario
        """
        try:
            # Preferir mqtt_publisher si está disponible (solo envío)
            if self.mqtt_publisher:
                success = self.mqtt_publisher.publish_json(topic, message_data, qos)
                
                if success:
                    print(f"✅ Mensaje MQTT enviado a topic: {topic} (via publisher)")
                    return True
                else:
                    print(f"❌ Error enviando mensaje MQTT a topic: {topic} (via publisher)")
                    return False
            
            # Fallback a mqtt_client si no hay mqtt_publisher
            elif self.mqtt_client:
                success = self.mqtt_client.publish_json(topic, message_data, qos)
                
                if success:
                    print(f"✅ Mensaje MQTT enviado a topic: {topic} (via client)")
                    return True
                else:
                    print(f"❌ Error enviando mensaje MQTT a topic: {topic} (via client)")
                    return False
            
            else:
                print(f"❌ No hay cliente MQTT disponible")
                return False
                
        except Exception as e:
            print(f"❌ Error enviando mensaje MQTT: {e}")
            self.logger.error(f"Error enviando mensaje MQTT: {e}")
            return False
    
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
            print(f"⚠️ Cola de WhatsApp llena, descartando mensaje")
            self.whatsapp_error_count += 1
            return False
        except Exception as e:
            print(f"❌ Error agregando mensaje a cola: {e}")
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
            """
            se obtiene la llave del mendaje, si sale error es porque 
            el mensaje no es correcto entonces pasa a la exceptio y no ejecuta nada
            (este paso es necesario, a veces se envian mensajes de conexion al webhook por parte de whp)
            """
            entry = json_message["entry"][0]["changes"][0]["value"]["messages"][0]
            #obtener numero
            number_client = entry["from"]
            type_message = entry["type"]
            is_text = entry[type_message]["body"] if type_message == "text" else False
             #validar si el usuario ya existe 
            if json_message["save_number"]:
                #usuario guardado
                pass
            else:
                #usuario nuevo
                # Versión síncrona para Redis
                self._process_new_number_sync(number=number_client)
            print(f"📱 Mensaje WhatsApp #{self.whatsapp_processed_count + 1}:")
            print(json.dumps(entry, indent=4, ensure_ascii=False))
            print("=" * 50)         
            self.whatsapp_processed_count += 1
            return True
        except json.JSONDecodeError:
            print(f"❌ Error: Mensaje no es JSON válido")
            print(f"Mensaje recibido: {message}")
            self.whatsapp_error_count += 1
            return False
        except Exception as e:
            print(f"❌ Error procesando mensaje: {e}")
            self.whatsapp_error_count += 1
            return False
    
    async def _process_single_whatsapp_message(self, message: str) -> None:
        """Procesar un solo mensaje de WhatsApp (versión asíncrona para fallback)"""
        try:
            # Parsear JSON
            json_message = json.loads(message)
            """
            se obtiene la llave del mendaje, si sale error es porque 
            el mensaje no es correcto entonces pasa a la exceptio y no ejecuta nada
            (este paso es necesario, a veces se envian mensajes de conexion al webhook por parte de whp)
            """
            entry = json_message["entry"][0]["changes"][0]["value"]["messages"][0]
            #obtener numero
            number_client = entry["from"]
            type_message = entry["type"]
            is_text = entry[type_message]["body"] if type_message == "text" else False
             #validar si el usuario ya existe 
            if json_message["save_number"]:
                #usuario guardado
                pass
            else:
                #usuario nuevo
                await self._process_new_number(number=number_client)
            print(f"📱 Mensaje WhatsApp #{self.whatsapp_processed_count + 1}:")
            print(json.dumps(entry, indent=4, ensure_ascii=False))
            print("=" * 50)         
            self.whatsapp_processed_count += 1
        except json.JSONDecodeError:
            print(f"❌ Error: Mensaje no es JSON válido")
            print(f"Mensaje recibido: {message}")
            self.whatsapp_error_count += 1
        except Exception as e:
            print(f"❌ Error procesando mensaje: {e}")
            self.whatsapp_error_count += 1
    def _process_new_number_sync(self, number: str) -> None:
        """Procesar nuevo número (versión síncrona para Redis)"""
        verify_number = self.backend_client.verify_user_number(number)
        print(verify_number)
    
    async def _process_new_number(self, number: str) -> None:
        """Procesar nuevo número (versión asíncrona para fallback)"""
        verify_number = self.backend_client.verify_user_number(number)
        print(verify_number)
    
    async def _process_save_number(self) -> None:
        return

    def process_whatsapp_message(self, message: str) -> None:
        """Función de compatibilidad - crear tarea para agregar a cola"""
        try:
            # Crear tarea para agregar el mensaje a la cola
            loop = asyncio.get_event_loop()
            loop.create_task(self.queue_whatsapp_message(message))
            
        except RuntimeError:
            # Si no hay loop corriendo, procesar directamente
            print(f"⚠️ No hay loop asyncio, procesando mensaje directamente")
            try:
                json_message = json.loads(message)
                print(json.dumps(json_message, indent=4, ensure_ascii=False))
            except json.JSONDecodeError:
                print(f"❌ Error: Mensaje no es JSON válido")
                print(f"Mensaje recibido: {message}")
        except Exception as e:
            print(f"❌ Error procesando mensaje: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del manejador"""
        return {
            "processed_messages": self.processed_messages,
            "error_count": self.error_count,
            "error_rate": round(self.error_count / max(self.processed_messages, 1) * 100, 2),
            "hardware_types_count": 1  # Solo BOTONERA
        }
    
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

    def add_company(self, company_code: str, company_name: str):
        """Compatibilidad - agregar empresa (no hace nada real)"""
        self.logger.info(f"Empresa agregada: {company_code} - {company_name}")

