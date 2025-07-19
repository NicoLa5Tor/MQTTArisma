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
        
        # Sistema de colas Redis para mensajes de WhatsApp SOLO si tenemos WhatsApp service
        self.redis_queue = None
        if whatsapp_service:
            try:
                # Pasar configuración Redis específica si está disponible
                redis_config = config.redis if config else None
                self.redis_queue = RedisQueueManager(redis_config)
                self.redis_queue.start_workers(self._process_single_whatsapp_message_sync)
                self.logger.info("✅ Sistema de colas Redis iniciado para WhatsApp")
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
            self._send_mqtt_message(data=response,mqtt_data=mqtt_data)
            # print(json.dumps(response,indent=4))
            # time.sleep(10000)
            list_users = response["numeros_telefonicos"]
            tipo_alarma_info = response["tipo_alarma_info"]
            task_id = self._send_create_down_alarma(list_users=list_users,alert=tipo_alarma_info)
            hardware_location = response["hardware_ubicacion"]
            time.sleep(1)
            self._send_location_personalized_message(hardware_location=hardware_location,numeros_data=list_users,tipo_alarma_info=tipo_alarma_info)
            print("ℹ️ Procesamiento de notificaciones completado")
        except Exception as e:
            print(f"❌ Error manejando notificaciones: {e}")
            self.logger.error(f"Error en notificaciones: {e}")
    def _send_mqtt_message(self, data,mqtt_data) -> None:
         # Procesar topics de otros hardware (MQTT)
            #print(json.dumps(data,indent=4))
            alarm_info = data.get("tipo_alarma_info",False)
            if not alarm_info:
                return
            hardware_ubication = data["hardware_ubicacion"]
            priority = data["prioridad"]
            if "topics_otros_hardware" in data:
                other_hardwars = data["topics_otros_hardware"]
                for item in other_hardwars:
                    item = self.pathern_topic + "/" + item
                    message_data = self._select_data_hardware(item=item,
                                                              data=alarm_info,
                                                              hardware_ubication=hardware_ubication,
                                                              priority=priority)
                    self.send_mqtt_message(topic=item, message_data=message_data)
 
    def _select_data_hardware(self,item,data,hardware_ubication,priority) -> Dict:
            alarm_color = data["tipo_alerta"]
            #print(mqtt_data)
            # time.sleep(10000)
            if "SEMAFORO" in item:
                            messsage_data = {
                                "tipo_alarma": alarm_color,
                            }
            elif "TELEVISOR" in item:
                            messsage_data = {
                                
                                    "tipo_alarma": alarm_color,
                                    "prioridad" : priority,
                                    "ubicacion": hardware_ubication.get("direccion",""),
                                    "url": hardware_ubication.get("direccion_open_maps",""),
                                    "elementos_necesarios": data.get("implementos_necesarios",[]),
                                    "instrucciones": data.get("recomendaciones",[])
                            }
            else:
                            messsage_data = {
                                "action": "generic",
                                "message": "notificación genérica",
                            }
            return messsage_data
    def _send_location_personalized_message(self, numeros_data:list[Dict],tipo_alarma_info:Dict,hardware_location:Dict) -> bool:
            print(f"la data es {json.dumps(tipo_alarma_info,indent=4)}")
            url_maps = hardware_location["direccion_url"]
            recipients = []
            for item in numeros_data:
                nombre = str(item.get("nombre",""))
                data_item = {
                    "phone":item["numero"],
                    "body_text": f"¡HOLA {nombre.split()[0].upper()}!.\nRESCUE TE AYUDA A LLEGAR A LA EMERGENCIA"
                }
                recipients.append(data_item)
            
            header_content = f"¡RESCUE SYSTEM UBICACIÓN!"
            self.whatsapp_service.send_personalized_broadcast(
                recipients= recipients,
                header_type="text",
                header_content=header_content,
                button_url=url_maps,
                footer_text="Equipo RESCUE",
                button_text = "Google Maps",
                use_queue=True
            )

            return True
        
    
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
            # print(json.dumps(json_message,indent=4))
            # time.sleep(100000)
            # Validar estructura del mensaje antes de procesar
            if ("entry" not in json_message or 
                not json_message["entry"] or 
                "changes" not in json_message["entry"][0] or
                not json_message["entry"][0]["changes"] or
                "value" not in json_message["entry"][0]["changes"][0] or
                "messages" not in json_message["entry"][0]["changes"][0]["value"] or
                not json_message["entry"][0]["changes"][0]["value"]["messages"]):              
                return True  # No es un error, simplemente ignoramos
            """
             "messages": [
                            {
                                "context": {
                                    "from": "15556484140",
                                    "id": "wamid.HBgMNTczMTAzMzkxODU0FQIAERgSMDIzODkyMUMzNzI1MTg4RkYyAA=="
                                },
                                "from": "573103391854",
                                "id": "wamid.HBgMNTczMTAzMzkxODU0FQIAEhggODNCM0E5MEJEOEQ4QTVDMzA1N0FCNzdEQzEzOThEQ0IA",
                                "timestamp": "1752817791",
                                "type": "interactive",
                                "interactive": {
                                    "type": "list_reply",
                                    "list_reply": {
                                        "id": "ROJO",
                                        "title": "Alerta Roja",
                                        "description": "Ayuda con problemas t\u00e9cnicos"
                                    }
                                }
                            }
                        ]
            """
            #print(json.dumps(json_message,indent=4))
            entry = json_message["entry"][0]["changes"][0]["value"]["messages"][0]
            
            # Obtener número
            number_client = entry["from"]
            # type_message = entry["type"]
            # is_text = entry[type_message]["body"] if type_message == "text" else False
            print("llega antes de validar")
            # Validar si el usuario ya existe 
            save_message = json_message.get("save_number")
            if save_message:
                # Usuario guardado
                cached_info = json_message["cached_info"]
                self._process_save_number(entry=entry,cached_info=cached_info)
            else:
                # Usuario nuevo
                response_verify = self._process_new_number_sync(number=number_client, entry=entry)
                print(f"si verifica y pasa: {response_verify}")
                if not response_verify:
                    self.whatsapp_service.send_individual_message(
                        phone=number_client, 
                        message="Lo siento  😞, Pero actualmente no te encuentras registrado en el sistema RESCUE."
                    )
            
            print(f"📱 Mensaje WhatsApp #{self.whatsapp_processed_count + 1}:")
            print(f"   📞 Número: {number_client}")
           
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
    def _process_save_number(self,entry:Dict,cached_info:Dict) -> None:
        print(f"El entry es: {json.dumps(entry,indent=4)}")
        print(f"El cached es:{json.dumps(cached_info,indent=4)}")
        if not cached_info:
            return
        number = cached_info["phone"]
        user = cached_info["name"]
        type_message = entry["type"]
        is_alarm = entry[type_message].get("list_reply", False)
        if is_alarm:
          """
                'list_reply': 
                {'id': 'VERDE', 
                'title': 'Alerta Verde', 
                'description': 
                'Ayuda con problemas técnicos'}    
          """  
          print("Es para alarma")
          alarm_id = is_alarm["id"]
          return
        is_down_alarm = entry[type_message].get("button_reply",False)
        if is_down_alarm:
            print("es apagar a alarma")
        #mandar lista para apagar
        self._send_create_alarma(number=number,usuario=user,is_in_cached=True)
  
    async def _process_single_whatsapp_message(self, message: str) -> None:
        """Procesar un solo mensaje de WhatsApp (versión asíncrona para fallback)"""
        try:
            # Parsear JSON
            print("asincrona")
            json_message = json.loads(message)
            """
            se obtiene la llave del mendaje, si sale error es porque 
            el mensaje no es correcto entonces pasa a la exceptio y no ejecuta nada
            (este paso es necesario, a veces se envian mensajes de conexion al webhook por parte de whp)
            """
            #print(json.dumps(json_message,indent=4))
           
            # Validar estructura del mensaje antes de procesar
            if ("entry" not in json_message or 
                not json_message["entry"] or 
                "changes" not in json_message["entry"][0] or
                not json_message["entry"][0]["changes"] or
                "value" not in json_message["entry"][0]["changes"][0] or
                "messages" not in json_message["entry"][0]["changes"][0]["value"] or
                not json_message["entry"][0]["changes"][0]["value"]["messages"]):
                return  
            
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
            print(f"   📞 Número: {number_client}")
            print(f"   📋 Tipo: {type_message}")
            print("=" * 50)
            self.whatsapp_processed_count += 1
        except json.JSONDecodeError:
            print(f"❌ Error: Mensaje no es JSON válido")
            print(f"Mensaje recibido: {message}")
            self.whatsapp_error_count += 1
        except Exception as e:
            print(f"❌ Error procesando mensaje: {e}")
            self.whatsapp_error_count += 1
   
    def _process_new_number_sync(self, number: str,entry:Dict=None) -> Optional[bool]:
        """Procesar nuevo número (versión síncrona para Redis)"""
        
        response = self.backend_client.verify_user_number(number)
        print(f"El verify es: {response}")
        
        # Verificar si la respuesta es None (error de conexión)
        if response is None:
            print("❌ Sin respuesta del servidor")
            return False
            
        # Verificar códigos de estado específicos
        status_code = response.get('_status_code', 200)
        
        if status_code == 404:
            print("🔍 Usuario no encontrado (404)")
            return False
        
        elif status_code == 401:
            print("🔒 No autorizado (401)")
            return False
        
        # Para respuestas exitosas, obtener los datos
        if not response.get('success', False):
            print(f"❌ Verificación fallida: {response.get('message', 'Error desconocido')}")
            return False
        
        verify_number = response.get("data")
        if verify_number is None or "telefono" not in verify_number:
            print("❌ Datos de usuario incompletos")
            return False
        print("si pasa")
        usuario = verify_number.get("nombre","")
        
        response_verify = self.whatsapp_service.add_number_to_cache(
            phone= verify_number["telefono"],           
            name= verify_number.get("nombre",""),           
            data= {
                "id":verify_number.get("id"),
                "empresa" : verify_number.get("empresa"),
                "sede" : verify_number.get("sede")
            }          
         )   
        if not response_verify:
            return False
        #el numero existe
        #es para apagar
        """
         "messages": [
                            {
                                "context": {
                                    "from": "15556484140",
                                    "id": "wamid.HBgMNTczMTAzMzkxODU0FQIAERgSMDIzODkyMUMzNzI1MTg4RkYyAA=="
                                },
                                "from": "573103391854",
                                "id": "wamid.HBgMNTczMTAzMzkxODU0FQIAEhggODNCM0E5MEJEOEQ4QTVDMzA1N0FCNzdEQzEzOThEQ0IA",
                                "timestamp": "1752817791",
                                "type": "interactive",
                                "interactive": {
                                    "type": "list_reply",
                                    "list_reply": {
                                        "id": "ROJO",
                                        "title": "Alerta Roja",
                                        "description": "Ayuda con problemas t\u00e9cnicos"
                                    }
                                }
                            }
                        ]
        """
        type_message = entry["type"]
        is_down_alarm = entry[type_message].get("list_reply", False)
        if is_down_alarm:
            #codigo para apagar alarma
            is_normal = is_down_alarm["id"] if "NORMAL" in is_down_alarm.get("id") else False
            if is_normal:
                return True
        #no es para apagar alarma, entonces 
        self._send_create_alarma(number=number,usuario=usuario)

        return True
    """
      Esta en hardcode, pero la idea es traer los tipos de alertas 
      tal cual como el usuario empresa las adita y guarda
    """
    def _send_create_down_alarma(self,list_users : list[Dict],alert:Dict,data_user:Dict = {}) -> bool:
        try:
            id_alert = alert["id"]
            image = alert["imagen_base64"]
            alert_name = alert["nombre"]
            empresa =  "en "+ data_user.get("empresa","la empresa")
            recipients = []
            for item in list_users:
                body_text = f"¡Hola {item["nombre"]}!.\nAlerta de {alert_name} {empresa}"
                data = {
                    "phone": item.get("numero",""),
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
                footer_text="Sistema RESCUE",
                recipients=recipients,
                use_queue=True
            )
        except Exception as ex:
            self.logger.error(f"Error al tratar de enviar el bulk list message: {ex}")
   
    def _send_create_alarma(self, number, usuario,is_in_cached:bool = False) -> bool:
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
                    header_text= body_text,
                    body_text="Selecciona la alerta que deseas activar",
                    footer_text="RESCUE SYSTEM",
                    button_text="Ver alertas",
                    sections=sections
                )
            except Exception as ex:
                self.logger.error(f"error al tatrar de crear la alerta {ex}") 
    async def _process_new_number(self, number: str) -> None:
        """Procesar nuevo número (versión asíncrona para fallback)"""
        verify_number = self.backend_client.verify_user_number(number)
        print(verify_number)
    
    

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

