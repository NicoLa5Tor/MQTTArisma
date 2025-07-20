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
from clients.mqtt_publisher_lite import MQTTPublisherLite
from config.settings import MQTTConfig


class WebSocketMessageHandler:
    """Manejador de mensajes WebSocket puro - SIN dependencias de MQTT"""
    
    def __init__(self, backend_client, whatsapp_service=None, config=None, enable_mqtt_publisher=False):
        self.backend_client = backend_client
        self.whatsapp_service = whatsapp_service
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Estadísticas solo para WhatsApp
        self.whatsapp_processed_count = 0
        self.whatsapp_error_count = 0
        
        # Usar settings en lugar de .env directo (igual que en MQTT handler)
        self.pattern_topic = config.mqtt.topic if config else "empresas"
        
        # MQTT Publisher OPCIONAL (solo para envío desde WhatsApp)
        self.mqtt_publisher = None
        if enable_mqtt_publisher and config:
            try:
                publisher_config = MQTTConfig(
                    broker=config.mqtt.broker,
                    port=config.mqtt.port,
                    topic=config.mqtt.topic,
                    username=config.mqtt.username,
                    password=config.mqtt.password,
                    client_id=f"{config.mqtt.client_id}_websocket_publisher",
                    keep_alive=config.mqtt.keep_alive
                )
                self.mqtt_publisher = MQTTPublisherLite(publisher_config)
                if self.mqtt_publisher.connect():
                    self.logger.info("✅ MQTT Publisher conectado desde WebSocket handler")
                else:
                    self.logger.warning("⚠️ Error conectando MQTT Publisher")
                    self.mqtt_publisher = None
            except Exception as e:
                self.logger.error(f"❌ Error iniciando MQTT Publisher: {e}")
                self.mqtt_publisher = None
        
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
        #print(f"el entry es {entry}")
        is_alarm = entry[type_message].get("list_reply", False)
        if is_alarm:
            #print("entra a lista y el cache es:")
            self.logger.info("Procesando selección de alarma")
            #print(json.dumps(cached_info,indent=4))
            response_alarm = self._create_alarm_in_back(
                descripcion=is_alarm["description"],
                tipo_alerta=is_alarm["id"],
                usuario_id=cached_info['data']["id"]
            )
            data_alert = response_alarm.get("alerta",{})
            list_users = response_alarm.get("numeros_telefonicos",{})
            self._send_create_down_alarma(
                alert=data_alert,
                list_users=list_users,
                data_user=cached_info
            )
           # print(json.dumps(entry,indent=4))
            topics = response_alarm.get("topics",{})
            self._intermediate_to_mqtt(alert=data_alert,topics=topics)
            return
            
        is_down_alarm = entry[type_message].get("button_reply", False)
        if is_down_alarm:
            self.logger.info("Procesando apagar alarma")
            #print(f"es para apagar {json.dumps(entry,indent=4)}")

            response = self._desactivate_alarm_to_back(entry=is_down_alarm,cached=cached_info)
            
            if response and response.get('success'):
                # Si se desactivó exitosamente, enviar confirmación personalizada
                self._send_alarm_deactivation_success_message(number, user, response)
                
                # También enviar comando de desactivación a los dispositivos MQTT
                topics = response.get("topics", [])
                prioridad = response.get("prioridad", "media")
                if topics:
                    self._send_deactivation_to_mqtt(topics=topics, prioridad=prioridad)
                
                return  # No enviar lista de alarmas después de desactivar
            else:
                # Si falló, enviar mensaje de error personalizado 
                self._send_alarm_deactivation_error_message(number, user, response)
                return  # No enviar lista de alarmas si hubo error
            
        # Enviar lista de alarmas solo si NO es una desactivación
        self._send_create_alarma(number=number, usuario=user, is_in_cached=True)
    def _desactivate_alarm_to_back(self,entry: Dict, cached:Dict) ->Optional[Dict]:
        try:

            alert_id = entry["id"]
            user_id = cached["data"]["id"]
            print(alert_id+"+"+user_id)
           # print(json.dumps(entry,indent=4))
            response = self.backend_client.deactivate_user_alert(
                alert_id = alert_id,
                desactivado_por_id = user_id,
                desactivado_por_tipo = "usuario"
            )
            return response
        except Exception as ex:
            self.logger.error(f"Error al tratar de desactivar alerta {ex}")
            return None
      
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
            
       
            # Procesar desactivación de alarma (apagar)
            is_down_alarm = entry[type_message].get("button_reply", False)
            if is_down_alarm:
                self.logger.info("Procesando apagar alarma (usuario nuevo)")
                
                # Desactivar alarma igual que usuarios cached
                response = self._desactivate_alarm_to_back(
                    entry=is_down_alarm,
                    cached={"data": {"id": verify_number.get("id")}}
                )
                
                if response and response.get('success'):
                    # Si se desactivó exitosamente, enviar confirmación personalizada
                    self._send_alarm_deactivation_success_message(number, usuario, response)
                    
                    # También enviar comando de desactivación a los dispositivos MQTT
                    topics = response.get("topics", [])
                    prioridad = response.get("prioridad", "media")
                    if topics:
                        self._send_deactivation_to_mqtt(topics=topics, prioridad=prioridad)
                else:
                    # Si falló, enviar mensaje de error personalizado 
                    self._send_alarm_deactivation_error_message(number, usuario, response)
                
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

    def _create_alarm_in_back(self,usuario_id: str, tipo_alerta: str, descripcion: str) -> Dict:
        prioridad = "media"
        try:
            response = self.backend_client.create_user_alert(
                usuario_id = usuario_id,
                tipo_alerta = tipo_alerta, 
                descripcion = descripcion, 
                prioridad = prioridad
            )
            self.logger.info(f"Alerta {tipo_alerta}, creada por {usuario_id}")
            return response
        except Exception as ex:
            self.logger.error(f"Error al tratar de crear la alerta (websocket service): {ex}")
            return None

    def send_mqtt_message(self, topic: str, message_data: Dict, qos: int = 0) -> bool:
        """Enviar mensaje MQTT desde el handler de WebSocket"""
        if not self.mqtt_publisher:
            self.logger.warning("⚠️ No hay cliente MQTT publisher disponible en WebSocket handler")
            return False
            
        try:
            success = self.mqtt_publisher.publish_json(topic, message_data, qos)
            
            if success:
                self.logger.info(f"✅ Mensaje MQTT enviado desde WebSocket a topic: {topic}")
                return True
            else:
                self.logger.error(f"❌ Error enviando mensaje MQTT desde WebSocket a topic: {topic}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error enviando mensaje MQTT desde WebSocket: {e}")
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
    
    def _send_mqtt_message(self, topic: str, message_data: Dict, qos: int = 0) -> bool:
        """Enviar mensajes MQTT a un topic específico"""
        try:
            # Usar mqtt_publisher si está disponible
            if self.mqtt_publisher:
                success = self.mqtt_publisher.publish_json(topic, message_data, qos)
                
                if success:
                    self.logger.info(f"✅ Mensaje MQTT enviado a topic: {topic}")
                    return True
                else:
                    self.logger.error(f"❌ Error enviando mensaje MQTT a topic: {topic}")
                    return False
            else:
                self.logger.warning(f"⚠️ No hay cliente MQTT publisher disponible")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error enviando mensaje MQTT: {e}")
            return False

    def _send_create_down_alarma(self, list_users: list, alert: Dict, data_user: Dict = {}) -> bool:
        """Crear notificación de alarma por WhatsApp"""
        if not self.whatsapp_service or not self.backend_client:
            self.logger.warning("⚠️ WhatsApp service o backend client no disponibles")
            return False
            
        try:
            #print(f"La alerta es {json.dumps(data_user,indent=4)}")
            id_alert = alert["alert_id"]
            image = alert["imagen_base64"]
            alert_name = alert["nombre"]
            empresa = data_user["data"]["empresa"]
            recipients = []
            footer = f"Creada por {data_user['name']}\nSistema RESCUE"
            
            for item in list_users:
                nombre = str(item["nombre"])
                body_text = f"¡Hola {nombre.split()[0].upper()}!.\nAlerta de {alert_name} en {empresa}."
                data = {
                    "phone": item.get("numero", ""),
                    "body_text": body_text
                }
                recipients.append(data)
                
            buttons = [
                {
                    "id": id_alert,
                    "title": "Apagar alarma"
                }
            ]
            
            self.whatsapp_service.send_bulk_button_message(
                header_type="image",
                header_content=image,
                buttons=buttons,
                footer_text=footer,
                recipients=recipients,
                use_queue=True
            )
            self.logger.info(f"✅ Alarma {id_alert} enviada a {len(recipients)} usuarios")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando notificación de alarma: {e}")
            return False
   
    def _intermediate_to_mqtt(self,topics,alert) -> None:
        try:
            #print(json.dumps(alert,indent=4))
            #enviar alerta a mqtt
            for topic in topics:
                topic = self.pattern_topic + "/" + topic
                message_hardware = self._select_data_hardware(alert=alert,topic=topic)
                self._send_mqtt_message(message_data=message_hardware,topic=topic)

        except Exception as ex:
            self.logger.error(f"Error en el intermedario a enviar mensajes al mqtt {ex}")

    def _select_data_hardware(self, topic, alert) -> Dict:
        """Seleccionar datos específicos según el tipo de hardware"""
        alarm_color = alert.get("tipo_alerta", "")
        if "SEMAFORO" in topic:
            message_data = {
                "tipo_alarma": alarm_color,
            }
        elif "TELEVISOR" in topic:
            message_data = {
                "tipo_alarma": alarm_color,
                "prioridad": alert.get("prioridad",""),
                "ubicacion": alert.get("direccion", ""),
                "url": alert.get("direccion_open_maps", ""),
                "elementos_necesarios": alert.get("implementos_necesarios", []),
                "instrucciones": alert.get("recomendaciones", [])
            }
        else:
            message_data = {
                "action": "generic",
                "message": "notificación genérica",
            }
            
        return message_data

    def _send_deactivation_to_mqtt(self, topics: list, prioridad: str) -> None:
        """Enviar comandos de desactivación MQTT a dispositivos hardware"""
        try:
            self.logger.info(f"🔄 Enviando comandos de desactivación MQTT a {len(topics)} dispositivos")
            
            for topic in topics:
                # Agregar pattern_topic igual que en activación
                full_topic = self.pattern_topic + "/" + topic
                
                # Crear mensaje de desactivación según el tipo de dispositivo
                deactivation_message = self._create_deactivation_message(topic=topic, prioridad=prioridad)
                
                # Enviar mensaje MQTT con el topic completo
                success = self._send_mqtt_message(message_data=deactivation_message, topic=full_topic)
                
                if success:
                    self.logger.info(f"✅ Dispositivo desactivado: {topic.split('/')[-1]} ({topic.split('/')[-2]})")
                else:
                    self.logger.error(f"❌ Error desactivando dispositivo: {topic}")
                    
        except Exception as ex:
            self.logger.error(f"❌ Error enviando comandos de desactivación MQTT: {ex}")
    
    def _create_deactivation_message(self, topic: str, prioridad: str) -> Dict:
        """Crear mensaje de desactivación específico según el tipo de dispositivo"""
        if "SEMAFORO" in topic:
            # Para semáforos: solo tipo_alarma NORMAL
            return {
                "tipo_alarma": "NORMAL"
            }
        elif "TELEVISOR" in topic:
            # Para televisores: tipo_alarma NORMAL + prioridad del response
            return {
                "tipo_alarma": "NORMAL",
                "prioridad": prioridad.upper()
            }
        else:
            # Para dispositivos genéricos
            return {
                "tipo_alarma": "NORMAL",
                "action": "deactivate"
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
    
    def _send_alarm_deactivation_success_message(self, phone: str, user: str, response: Dict) -> bool:
        """Enviar mensaje personalizado de éxito en desactivación de alarma usando send_bulk_individual"""
        try:
            if not self.whatsapp_service:
                return False
            
            # Obtener información adicional de la respuesta
            fecha_desactivacion = response.get('desactivado_por', {}).get('fecha_desactivacion', '')
            numeros_telefonicos = response.get('numeros_telefonicos', [])
            
            # Preparar mensajes personalizados para todos los usuarios
            recipients = []
            for contact in numeros_telefonicos:
                phone_number = contact.get('numero', '')
                nombre = contact.get('nombre', '')
                
                # Determinar si es quien desactivó la alarma o es otra persona
                if phone_number == phone:
                    # Mensaje para quien desactivó
                    success_message = f"✅ ¡Perfecto {nombre.split()[0].upper()}!"
                    success_message += f"\n\n🎯 Alarma desactivada exitosamente"
                    success_message += f"\n🕐 Fecha: {fecha_desactivacion.split('T')[0] if fecha_desactivacion else 'Ahora'}"
                    success_message += f"\n👤 Desactivada por: TI"
                    success_message += f"\n\n🛡️ El sistema RESCUE ha registrado tu acción"
                    success_message += f"\n🚨 ¡Gracias por mantener la seguridad!"
                    success_message += f"\n\n📱 Sistema RESCUE - Siempre Vigilante"
                else:
                    # Mensaje para otros usuarios
                    success_message = f"ℹ️ ¡Hola {nombre.split()[0].upper()}!"
                    success_message += f"\n\n✅ La alarma ha sido DESACTIVADA"
                    success_message += f"\n👤 Desactivada por: {user}"
                    success_message += f"\n🕐 Momento: Ahora mismo"
                    success_message += f"\n\n🛡️ El sistema vuelve a estar en estado normal"
                    success_message += f"\n📱 Notificación automática del Sistema RESCUE"
                
                recipients.append({
                    "phone": phone_number,
                    "message": success_message
                })
            
            # Enviar usando el cliente de WhatsApp para envío masivo
            if recipients:
                response_bulk = self.whatsapp_service.send_bulk_individual(
                    recipients=recipients,
                    use_queue=True
                )
                
                if response_bulk:
                    self.logger.info(f"✅ Notificación de desactivación exitosa enviada a {len(recipients)} usuarios")
                    return True
                else:
                    self.logger.error(f"❌ Error enviando notificación masiva de desactivación exitosa")
                    # Fallback al método individual
                    if self.whatsapp_service:
                        simple_message = f"✅ Alarma desactivada exitosamente por {user}.\n\nGracias por usar el Sistema RESCUE 🚨"
                        self.whatsapp_service.send_individual_message(phone=phone, message=simple_message)
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando mensaje de éxito de desactivación: {e}")
            return False
    
    def _send_alarm_deactivation_error_message(self, phone: str, user: str, response: Optional[Dict]) -> bool:
        """Enviar mensaje personalizado de error en desactivación de alarma"""
        try:
            if not self.whatsapp_service:
                return False
            
            # Siempre enviar mensaje de alarma ya desactivada (sin importar el tipo de error)
            error_message = f"ℹ️ ¡Hola {user.split()[0].upper()}!"
            error_message += f"\n\nℹ️ Esta alarma ya fue DESACTIVADA anteriormente"
            
            # Obtener información de quién la desactivó si está disponible
            if response and response.get('desactivado_por', {}):
                desactivado_por = response.get('desactivado_por', {})
                fecha = desactivado_por.get('fecha_desactivacion', '')
                fecha_formato = fecha.split('T')[0] if fecha else 'Fecha desconocida'
                error_message += f"\n\n📅 Desactivada el: {fecha_formato}"
                error_message += f"\n👤 Por otro usuario del sistema"
            
            error_message += f"\n\n✅ ESTADO: La alarma ya está INACTIVA"
            error_message += f"\n🛡️ No hay riesgo activo en el sistema"
            error_message += f"\n\n👍 Gracias por tu atención a la seguridad"
            
            error_message += f"\n\n📱 Sistema RESCUE - Soporte Técnico"
            
            self.whatsapp_service.send_individual_message(
                phone=phone,
                message=error_message
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando mensaje de error de desactivación: {e}")
            return False
    
    def _send_bulk_deactivation_notification(self, numeros_telefonicos: list, deactivated_by: str, response: Dict, exclude_phone: str) -> bool:
        """Enviar notificación masiva a otros usuarios sobre desactivación de alarma"""
        try:
            # Preparar lista de destinatarios (excluir quien desactivó)
            recipients = []
            for contact in numeros_telefonicos:
                phone = contact.get('numero', '')
                nombre = contact.get('nombre', '')
                
                # Excluir el número de quien desactivó la alarma
                if phone != exclude_phone:
                    notification_message = f"ℹ️ ¡Hola {nombre.split()[0].upper()}!"
                    notification_message += f"\n\n✅ La alarma ha sido DESACTIVADA"
                    notification_message += f"\n👤 Desactivada por: {deactivated_by}"
                    notification_message += f"\n🕐 Momento: Ahora mismo"
                    notification_message += f"\n\n🛡️ El sistema vuelve a estar en estado normal"
                    notification_message += f"\n📱 Notificación automática del Sistema RESCUE"
                    
                    recipients.append({
                        "phone": phone,
                        "message": notification_message
                    })
            
            # Enviar usando el cliente de WhatsApp para envío masivo si hay destinatarios
            if recipients:
                response = self.whatsapp_service.send_bulk_individual(
                    recipients=recipients,
                    use_queue=True
                )
                
                if response:
                    self.logger.info(f"✅ Notificación de desactivación enviada a {len(recipients)} usuarios")
                    return True
                else:
                    self.logger.error(f"❌ Error enviando notificación masiva de desactivación")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando notificación masiva de desactivación: {e}")
            return False
