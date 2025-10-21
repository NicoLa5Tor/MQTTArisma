"""
Manejador de mensajes WebSocket puro - SIN MQTT
Solo procesa mensajes entrantes de WhatsApp desde webhooks
"""
import json
import logging
import asyncio
import time
from asyncio import Queue
from typing import Dict, Any, Optional, Set, List
from utils.redis_queue_manager import RedisQueueManager
from clients.mqtt_publisher_lite import MQTTPublisherLite
from config.settings import MQTTConfig
from handlers.empresa_alert_handler import EmpresaAlertHandler
from datetime import datetime, timedelta


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
        
        # Handler específico para alertas desactivadas por empresa
        self.empresa_handler = None
        if enable_mqtt_publisher and config:
            self.empresa_handler = EmpresaAlertHandler(
                whatsapp_service=whatsapp_service,
                config=config,
                enable_mqtt_publisher=enable_mqtt_publisher
            )
        
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
        #print(f"🔍 DEBUG: Mensaje recibido en WebSocket: {message}")
        try:
            # Primero verificar si es un mensaje de empresa
            try:
                json_message = json.loads(message)
                message_type = json_message.get("type")
                
                if message_type == "alert_deactivated_by_empresa":
                    self.logger.info("🏢 Detectado mensaje de desactivación por empresa")
                    return self._handle_empresa_message_sync(json_message)
                elif message_type == "create_empresa_alert":
                    self.logger.info("🏢 Detectado mensaje para crear alerta de empresa")
                    return self._handle_create_empresa_alert_sync(json_message)
            except (json.JSONDecodeError, KeyError):
                # Si no es JSON válido o no tiene type, procesar como mensaje normal
                pass
            
            # Procesar como mensaje normal de WhatsApp
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
                    self._process_single_whatsapp_message_sync(message)
                    
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

    def _has_creator_permission(self, payload: Optional[Dict]) -> bool:
        """Determinar si el payload contiene permisos de creador"""
        if not isinstance(payload, dict):
            return False

        role_data = None
        if "rol" in payload:
            role_data = payload.get("rol")
        elif "data" in payload and isinstance(payload["data"], dict):
            role_data = payload["data"].get("rol")

        if isinstance(role_data, dict):
            return bool(role_data.get("is_creator"))

        return False

    def _send_permission_denied_message(self, phone: str, user: str, action: str) -> None:
        """Notificar al usuario que no tiene privilegios para la acción solicitada"""
        if not self.whatsapp_service:
            return

        friendly_user = user or "Usuario"
        message = (
            f"Lo siento {friendly_user}, no tienes permisos para {action}."
            "\nContacta al administrador si necesitas acceso."
        )
        self.whatsapp_service.send_individual_message(phone=phone, message=message)

    def _process_single_whatsapp_message_sync(self, message: str) -> bool:
        """Procesar un solo mensaje de WhatsApp (versión síncrona para Redis)"""
        try:
            # Parsear JSON
            json_message = json.loads(message)
            
            # PRIMERO: Verificar si es un mensaje de empresa
            message_type = json_message.get("type")
            if message_type == "alert_deactivated_by_empresa":
                self.logger.info("🏢 Detectado mensaje de desactivación por empresa (Redis)")
                return self._handle_empresa_message_sync(json_message)
            
            # Validar estructura del mensaje antes de procesar como WhatsApp webhook
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
    def _alarm_back_save(self,entry_alarm:Dict,cached_info:Dict) -> bool:
        """Guardar la alerta antes de crearla"""
        try:
            self.logger.info("Procesando en alarm_back_save")
            number = cached_info["phone"]
            new_data = {
                "alert_active" : False,
                "info_alert" :{
                    "type_alert": entry_alarm["id"],
                    "description": entry_alarm["description"],
                    "datetime": str(datetime.now()),
                    "alert_title": entry_alarm["title"]
                }
            }
            # print(json.dumps(cached_info,indent=4))
            body_message = f"¡{cached_info['name']}!\nPara crear la alerta de {entry_alarm['title']}\nPrimero debes proporcionar la ubicación"
            self.whatsapp_service.update_number_cache(
                phone=number,
                data=new_data,
                empresa_id=cached_info.get("data", {}).get("empresa_id")
            )
            self.whatsapp_service.send_location_request(phone=number,body_text=body_message)
            return True
        except Exception as ex:
            self.logger.error(f"Hubo un error en alarm_back_save {ex}")
            return False
    def _create_bulk_cache(self,alarm_info:Dict,list_users: Dict,cache_creator:Dict) -> None:
        try:
            # print(json.dumps(alarm_info,indent=3))
            # print(json.dumps(list_users,indent=3))
            data_cache = cache_creator["data"]
            """
            Este es un ejemplo del data del cache
               "data": {
                    "alert_active": false,
                    "empresa": "Nicolas Empresa",
                    "id": "6875e231a37810d0a8dc508e",
                    "info_alert": {
                        "alert_title": "Inundaci\u00f3n",
                        "datetime": "2025-07-29 17:49:28.002298",
                        "description": "Alerta por inundaci\u00f3n",
                        "type_alert": "AZUL"
                    },
                    "sede": "Secundaria"
                },
      

            """
            empresa_id = data_cache.get("empresa_id")

            for user in list_users:
                data_user = {
                    "id" : user["usuario_id"],
                    "alert_active":True,
                    "empresa" : data_cache["empresa"],
                    "disponible" : user["disponible"],
                    "embarcado" : user["embarcado"],
                    "info_alert" : {
                        "alert_id" : alarm_info["_id"]
                    }
                }

                role_info = user.get("rol") if isinstance(user, dict) else None
                if isinstance(role_info, dict):
                    data_user["rol"] = {
                        "nombre": role_info.get("nombre") or role_info.get("name", ""),
                        "is_creator": bool(role_info.get("is_creator"))
                    }
                if empresa_id:
                    data_user["empresa_id"] = empresa_id
                self.whatsapp_service.add_number_to_cache(phone = user["numero"]
                                                          , name = user["nombre"]
                                                          , data = data_user
                                                          , empresa_id = empresa_id)
        except Exception as ex:
            self.logger.error(f"Error en _create_bulk_cache {ex}")
    def _create_alarm(self,cached_info:Dict,ubication:Dict) -> bool:
        try:
            #print(json.dumps(ubication,indent=3))
            alert_info = cached_info["data"]["info_alert"]
            response_alarm = self._create_alarm_in_back(
                descripcion=alert_info["description"],
                latitud=str(ubication["latitude"]),
                longitud=str(ubication["longitude"]),
                tipo_alerta=alert_info["type_alert"],
                usuario_id=cached_info["data"]["id"]
            )
           
   
            data_alert = response_alarm.get("alert",{})
            list_users = data_alert.get("numeros_telefonicos",{})
         
            
       
            # print(f"data_alert: {json.dumps(data_alert, indent=2)}")
            # print(f"list_users: {json.dumps(list_users, indent=2)}")
            # print(f"hardware_location: {json.dumps(hardware_location, indent=2)}")
 
            numero_excluido = cached_info["phone"]
            usuarios_filtrados = [u for u in list_users if u["numero"] != numero_excluido]
            if list_users:
                creator_name = data_alert.get("activacion_alerta", {}).get("nombre")
                recipients_template = [u for u in list_users if u.get("numero") != numero_excluido]
                self._send_alert_created_template(
                    recipients=recipients_template,
                    alert_info=data_alert,
                    creator_name=creator_name
                )
                time.sleep(20)
                self._send_location_personalized_message(
                    numeros_data=list_users,
                    tipo_alarma_info=data_alert,
                )
                time.sleep(2)
            else:
                self.logger.error("⚠️ NO se envió mensaje de ubicación - faltan datos")

            self._send_create_active_user(
                alert=data_alert,
                list_users=usuarios_filtrados,
                data_user=cached_info
            )
            
            # print(f"list_users exists: {bool(list_users)}")
            # print(f"hardware_location exists: {bool(hardware_location)}")
            # print(f"data_alert has direccion_url: {bool(data_alert.get('direccion_url'))}")
            # print(f"Enviando ubicación: {bool(list_users and data_alert.get('direccion_url'))}")
            #print(json.dumps(response_alarm,indent=4))
           
            self._create_bulk_cache(list_users=list_users,alarm_info=data_alert,cache_creator=cached_info)
            topics = data_alert.get("topics_otros_hardware",{})
            self._intermediate_to_mqtt(alert=data_alert,topics=topics)
            return True
        except Exception as ex:
            self.logger.error(f"Error en create_alarm {ex}")
            return False
    def _send_bulk_text_message(self,body:str,list_users: list[Dict],name_made:str) -> bool:
        try:
            recipients = []
            for user in list_users:
                message = {
                    "phone":user["numero"],
                    "message" : f"*{name_made}*\n{body}"
                }
                recipients.append(message)
            self.whatsapp_service.send_bulk_individual(recipients = recipients)

        except Exception as ex:
            self.logger.error(f"Error en _send_bulk_text_message {ex}")
            return False
    def _send_bulk_team(self,type_message:str,name_made:str,list_users:list[Dict],message)-> bool:
        try:
            list_validate = [u for u in list_users if u["disponible"]]
            if not list_validate: 
                self.logger.info("No hay usuario a quien enviarle informacion")
                return True
            match type_message:
                case "text":
                    self._send_bulk_text_message(list_users=list_validate,body=message,name_made=name_made)
            return True
        except Exception as ex:
            self.logger.error(f"Error en _send_bulk_team {ex}")
            return False
    def _process_save_number(self, entry: Dict, cached_info: Dict) -> None:
        """Procesar mensaje de número guardado"""
        if not cached_info or not self.whatsapp_service:
            return
        number = cached_info["phone"]
        user = cached_info["name"]
        type_message = entry["type"]
        message = None
        #print(f"el entry es {entry}")
        is_list = entry[type_message].get("list_reply", False)
        is_button = entry[type_message].get("button_reply", False)
        #es para crear alarma
        exist_alert = cached_info["data"]
        is_creator = self._has_creator_permission(cached_info)
        if "alert_active" in exist_alert:
            id_user = exist_alert["id"]
            alert_create = exist_alert["alert_active"]
            if alert_create:
                """ esto es porque la alerta ya se creo"""
                id_alert = exist_alert["info_alert"]["alert_id"]
                #aqui se valida si es un boton lo que llega
                if is_button:
                    type_button = is_button["id"]
                    #esto valida si es para activacion de un usuario
                    if type_button == "Activar_User":
                        self.backend_client.update_user_status( alert_id = id_alert,
                                                                usuario_id = id_user,
                                                                disponible = True)
                        data_update = {
                            "disponible" : True
                        }
                        self.whatsapp_service.update_number_cache(
                            phone=number,
                            data=data_update,
                            empresa_id=cached_info.get("data", {}).get("empresa_id")
                        )
                        self.whatsapp_service.send_individual_message(phone = number,
                                                                      message = "Ahora recibiras mensajes de los miembros del equipo")
                    elif type_button == "APAGAR ALARMA":
                        if not is_creator:
                            self._send_permission_denied_message(number, user, "apagar la alarma")
                            return
                        try:
                            response_desactivate = self._desactivate_alarm_to_back(id_alert=id_alert,cached=cached_info)
                            
                            # Verificar si la desactivación fue exitosa
                            if response_desactivate and response_desactivate.get('success', False):
                                # Verificar que tenemos los datos necesarios
                                list_users = response_desactivate.get("numeros_telefonicos", [])
                                if not list_users:
                                    self.logger.warning("⚠️ No se encontraron usuarios en la respuesta de desactivación")
                                    self.whatsapp_service.send_individual_message(phone=number, message="Alarma desactivada exitosamente")
                                    return  # Salir temprano para evitar más procesamiento
                                
                                # Limpiar cache de usuarios
                                try:
                                    self._clean_bulk_cache_alert(list_user=list_users)
                                except Exception as cache_error:
                                    self.logger.error(f"❌ Error limpiando cache: {cache_error}")
                                
                                # Enviar mensajes a otros usuarios
                                try:
                                    list_not_you = [u for u in list_users if u["numero"] != number]
                                    if list_not_you:
                                        self._send_bulk_team(list_users=list_not_you,
                                                             name_made=user,type_message="text",
                                                             message="Alerta desactivada.\nConversación grupal concluida.")
                                except Exception as msg_error:
                                    self.logger.error(f"❌ Error enviando mensajes bulk: {msg_error}")
                                
                                # Enviar confirmación al usuario que desactivó
                                try:
                                    self.whatsapp_service.send_individual_message(phone=number,
                                                                                  message="Desactivaste la alarma exitosamente\nConversación grupal concluida.")
                                except Exception as confirm_error:
                                    self.logger.error(f"❌ Error enviando confirmación: {confirm_error}")
                                
                                # Debug response
                                # try:
                                #     print(json.dumps(response_desactivate,indent=4))
                                # except Exception as json_error:
                                #     self.logger.error(f"❌ Error imprimiendo JSON: {json_error}")
                                
                                # Enviar comando MQTT de desactivación
                                try:
                                    topics = response_desactivate.get("topics", [])
                                    if topics:
                                        prioridad = response_desactivate.get("prioridad", "media")
                                        self._send_deactivation_to_mqtt(topics=topics, prioridad=prioridad)
                                    else:
                                        self.logger.info("ℹ️ No hay topics MQTT para desactivar")
                                except Exception as mqtt_error:
                                    self.logger.error(f"❌ Error enviando comandos MQTT: {mqtt_error}")
                                
                                self.logger.info(f"✅ Alarma {id_alert} desactivada exitosamente por usuario {user}")
                            else:
                                # Error en la desactivación - enviar mensaje de error
                                error_msg = response_desactivate.get('message', 'Error desconocido') if response_desactivate else 'Sin respuesta del servidor'
                                self.logger.error(f"❌ Error desactivando alarma {id_alert}: {error_msg}")
                                
                                # Enviar mensaje personalizado de error al usuario
                                try:
                                    self.whatsapp_service.send_individual_message(
                                        phone=number,
                                        message=f"⚠️ {user}, no se pudo desactivar la alarma.\n\nPosibles causas:\n• La alarma ya fue desactivada por otro usuario\n• Error temporal del sistema\n\nPor favor intenta nuevamente o contacta al administrador."
                                    )
                                except Exception as error_msg_error:
                                    self.logger.error(f"❌ Error enviando mensaje de error: {error_msg_error}")
                        
                        except Exception as general_error:
                            # Capturar cualquier error no manejado para evitar que Redis reintente
                            self.logger.error(f"💥 Error general en desactivación de alarma: {general_error}")
                            try:
                                self.whatsapp_service.send_individual_message(
                                    phone=number,
                                    message=f"❌ {user}, ocurrió un error inesperado al desactivar la alarma. Por favor contacta al administrador."
                                )
                            except Exception:
                                pass  # Si ni siquiera podemos enviar el mensaje de error, no hacer nada
                elif is_list:
                    #Esto es para si es una lista despues de que ya se activo
                    opcion = is_list["id"]
                    data_alert = self.backend_client.get_alert_by_id(alert_id = id_alert,user_id=id_user).get("alert",{})
                    data_user = [u for u in data_alert["numeros_telefonicos"] if u["numero"] == number]
                    if opcion == "APAGAR":
                        if not is_creator:
                            self._send_permission_denied_message(number, user, "apagar la alarma")
                            self._send_options_user(number=number, user=user, can_manage_alarm=False)
                            return
                        self._send_create_down_alarma(alert=data_alert,data_user=cached_info,list_users=data_user)
                    elif opcion == "UBICACION":
                        self._send_location_personalized_message(numeros_data=data_user,tipo_alarma_info=data_alert)
                    elif opcion == "EMBARCADO":
                        data_user_not_you = [u for u in data_alert["numeros_telefonicos"] if u["numero"] != number]
                        self.backend_client.update_user_status(alert_id=exist_alert["info_alert"]["alert_id"],
                                                                usuario_id = exist_alert["id"], 
                                                                embarcado = True)
                        self.whatsapp_service.update_number_cache(
                            phone = number,
                            data = {"embarcado" : True},
                            empresa_id=cached_info.get("data", {}).get("empresa_id")
                        )
                        self._send_bulk_team(list_users=data_user_not_you,message="Estoy camino a la emergencia",name_made=user,type_message="text")

                
                elif isinstance(exist_alert.get("disponible"), bool) and not exist_alert["disponible"]:
                    #quiere decir que mando un mensaje cuando aun no puede hablar 
                    data_alert = self.backend_client.get_alert_by_id(alert_id = id_alert,user_id=id_user).get("alert",{})
                    #print(json.dumps(data_alert,indent=4))
                    data_user = [u for u in data_alert["numeros_telefonicos"] if u["numero"] == number]
                    self._send_create_active_user(alert=data_alert,list_users=data_user,data_user=cached_info)
                else:
                    """Aqui se deberia colocar el envio de mensaje a todos los usuarios, pero..
                    por ahora se procesa solo mensajes de texto"""
                    if type_message:
                        body_text = entry[type_message]["body"]
                        comandos_opciones = [
                            "OPCIONES",
                            "MENU",
                            "MENÚ",
                            "OPCION",
                            "OPCIÓN",
                            "LISTA",
                            "LISTADO",
                            "MOSTRAR",
                            "MOSTRAR OPCIONES",
                            "MOSTRAR MENU",
                            "MOSTRAR MENÚ",
                            "VER OPCIONES",
                            "VER MENÚ",
                            "INSTRUCCIONES",
                            "AYUDA",
                            "HELP"
                        ]
                        if body_text.upper() in comandos_opciones:
                            self._send_options_user(number=number,user=user,can_manage_alarm=is_creator)
                        else:
                            data_alert = self.backend_client.get_alert_by_id(alert_id = id_alert,user_id=id_user).get("alert",{})
                            data_user = [u for u in data_alert["numeros_telefonicos"] if u["numero"] != number]
                            if data_user:
                                self._send_bulk_team(name_made=user,message=body_text,list_users=data_user,type_message=type_message)
                            else:
                                self.logger.info("El mensaje no tiene destinatarios")
                return
            else:
                #No se ha creado la alerma pero ya se escogio
                fecha_crear_str = exist_alert["info_alert"]["datetime"]
                fecha_crear = datetime.fromisoformat(fecha_crear_str)
                ahora = datetime.now()

                if ahora - fecha_crear < timedelta(minutes=5):
                    #Han pasado menos de 5 minutos
                    #print(json.dumps(entry,indent=4))
                    location = entry.get("location",False)
                    if location:
                        if not is_creator:
                            self._send_permission_denied_message(number, user, "activar la alarma")
                            return
                        self._create_alarm(cached_info=cached_info,ubication=location)
                    else:
                        if not is_creator:
                            self._send_permission_denied_message(number, user, "activar la alarma")
                        else:
                            message_location = f"{user}\nPara crear la alerta {exist_alert['info_alert']['alert_title']}\nDebes enviar la ubicacion."
                            self.whatsapp_service.send_location_request(phone=number,body_text=message_location)
                    return
                else:
                    #Ya pasaron 5 minutos o más
                    message = f"Lo siento {user}.\nPero excediste el tiempo límite de 5 min."
                    data_delete = {
                        "info_alert":"__DELETE__",
                        "alert_active":"__DELETE__"
                    }
                    self.whatsapp_service.update_number_cache(
                        phone=number,
                        data=data_delete,
                        empresa_id=cached_info.get("data", {}).get("empresa_id")
                    )
        else:
            if is_list:
                if not is_creator:
                    self._send_permission_denied_message(number, user, "activar una alarma")
                    return
                self._alarm_back_save(entry_alarm=is_list,cached_info=cached_info)
                self.logger.info("Procesando selección de alarma")
                return
            # if is_button:
            #     self.logger.info("Procesando apagar alarma")
            #     #print(f"es para apagar {json.dumps(entry,indent=4)}")
            #     response = self._desactivate_alarm_to_back(entry=is_button,cached=cached_info)
            #     if response and response.get('success'):
            #         # Si se desactivó exitosamente, enviar confirmación personalizada
            #         self._send_alarm_deactivation_success_message(number, user, response)
            #         # También enviar comando de desactivación a los dispositivos MQTT
            #         topics = response.get("topics", [])
            #         prioridad = response.get("prioridad", "media")
            #         if topics:
            #             self._send_deactivation_to_mqtt(topics=topics, prioridad=prioridad)
                    
            #         return  # No enviar lista de alarmas después de desactivar
            #     else:
            #         # Si falló, enviar mensaje de error personalizado 
            #         self._send_alarm_deactivation_error_message(number, user, response)
            #         return  # No enviar lista de alarmas si hubo error
        
        

        # Enviar lista de alarmas solo si NO es una desactivación
        if not is_creator:
            self._send_permission_denied_message(number, user, "activar una alarma")
            return
        self._send_create_alarma(
            number=number,
            usuario=user,
            is_in_cached=True,
            message_time=message,
            empresa_id=cached_info.get("data", {}).get("empresa_id")
        )
    def _clean_bulk_cache_alert(self,list_user:list[Dict]) -> None:
        try:
            data = {
                "info_alert" : "__DELETE__",
                "alert_active": "__DELETE__",
                "disponible": "__DELETE__",
                "embarcado": "__DELETE__"
            }
            list_phones = [n["numero"] for n in list_user]
            self.whatsapp_service.bulk_update_numbers(phones = list_phones,data=data )
        except Exception as ex:
            self.logger.error(f"Error en _clean_bulk_cache_alert {ex}")
    def _desactivate_alarm_to_back(self,id_alert, cached:Dict) ->Optional[Dict]:
        try:
            user_id = cached["data"]["id"]
            response = self.backend_client.deactivate_user_alert(
                alert_id = id_alert,
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

        # Normalizar información de empresa (puede venir como string o dict)
        empresa_info = verify_number.get("empresa")
        empresa_id = verify_number.get("empresa_id")
        empresa_nombre = ""

        if isinstance(empresa_info, dict):
            empresa_id = empresa_id or empresa_info.get("id") or empresa_info.get("_id")
            empresa_nombre = empresa_info.get("nombre") or empresa_info.get("name") or ""
        else:
            empresa_nombre = empresa_info or ""

        # Normalizar información de sede (igual puede venir como string o dict)
        sede_info = verify_number.get("sede")
        sede_nombre = ""
        if isinstance(sede_info, dict):
            sede_nombre = sede_info.get("nombre") or sede_info.get("name") or ""
        else:
            sede_nombre = sede_info or ""
        
        # Preparar información de rol (por defecto sin privilegios)
        raw_role = verify_number.get("rol")
        normalized_role = {}
        if isinstance(raw_role, dict):
            normalized_role = {
                "nombre": raw_role.get("nombre") or raw_role.get("name", ""),
                "is_creator": bool(raw_role.get("is_creator"))
            }
        else:
            normalized_role = {"is_creator": False}

        is_creator = normalized_role.get("is_creator", False)

        # Agregar número al cache de WhatsApp
        if self.whatsapp_service:
            response_verify = self.whatsapp_service.add_number_to_cache(
                phone=verify_number["telefono"],           
                name=verify_number.get("nombre", ""),           
                data={
                    "id": verify_number.get("id"),
                    "empresa": empresa_nombre,
                    "sede": sede_nombre,
                    "rol": normalized_role,
                    **({"empresa_id": empresa_id} if empresa_id else {})
                },
                empresa_id=empresa_id
            )
            if not response_verify:
                return False
        # # Procesar tipo de mensaje si existe
        # if entry:
        #     type_message = entry["type"]
        #     # Procesar desactivación de alarma (apagar)
        #     is_down_alarm = entry[type_message].get("button_reply", False)
        #     if is_down_alarm:
        #         self.logger.info("Procesando apagar alarma (usuario nuevo)")
                
        #         # DEBUG: Imprimir datos del usuario nuevo
        #         print(f"\n=== DEBUG USUARIO NUEVO DESACTIVACION ===")
        #         print(f"Usuario: {usuario}")
        #         print(f"Numero: {number}")
        #         print(f"verify_number: {json.dumps(verify_number, indent=2)}")
        #         print(f"is_down_alarm: {json.dumps(is_down_alarm, indent=2)}")
        #         print("=== END DEBUG USUARIO NUEVO DESACTIVACION ===")
                
        #         # Desactivar alarma igual que usuarios cached
        #         response = self._desactivate_alarm_to_back(
        #             entry=is_down_alarm,
        #             cached={"data": {"id": verify_number.get("id")}}
        #         )
                
        #         # DEBUG: Imprimir respuesta de desactivación
        #         print(f"\n=== DEBUG RESPONSE DESACTIVACION USUARIO NUEVO ===")
        #         #print(f"Response: {json.dumps(response, indent=2)}")
        #         print("=== END DEBUG RESPONSE DESACTIVACION USUARIO NUEVO ===")
                
        #         if response and response.get('success'):
        #             # Si se desactivó exitosamente, enviar confirmación personalizada
        #             self._send_alarm_deactivation_success_message(number, usuario, response)
                    
        #             # También enviar comando de desactivación a los dispositivos MQTT
        #             topics = response.get("topics", [])
        #             prioridad = response.get("prioridad", "media")
        #             if topics:
        #                 self._send_deactivation_to_mqtt(topics=topics, prioridad=prioridad)
        #         else:
        #             # Si falló, enviar mensaje de error personalizado 
        #             print("⚠️ Desactivación falló, enviando mensaje de error")
        #             self._send_alarm_deactivation_error_message(number, usuario, response)
                
        #         return True
        
        if not is_creator:
            self._send_permission_denied_message(number, usuario, "crear alertas")
            return True

        # Enviar lista de alarmas
        self._send_create_alarma(number=number, usuario=usuario, empresa_id=empresa_id)
        return True

    def _send_options_user(self, number: str, user: str, can_manage_alarm: bool) -> bool:
        if not self.whatsapp_service:
            self.logger.warning("⚠️ WhatsApp service no disponible")
            return False
        try:
            rows = []
            if can_manage_alarm:
                rows.append({
                    "id": "APAGAR",
                    "title": "Apagar Alarma",
                    "description": "Al seleccionar esta opción, la alarma en cuestión se apagará."
                })

            rows.extend([
                {
                    "id": "UBICACION",
                    "title": "Ubicación de la alarma",
                    "description": "Obtener la ubicación de la alarma"
                },
                {
                    "id": "EMBARCADO",
                    "title": "Embarcarme",
                    "description": "Indica que ya estás en camino a la emergencia"
                }
            ])

            sections = [
                {
                    "title": "Servicios técnicos",
                    "rows": rows
                }
            ]
            body_text = f"{user}\nEstas son las opciones disponibles"
            self.whatsapp_service.send_list_message(
                        phone=number,
                        header_text=body_text,
                        body_text="Selecciona la opción que deseas",
                        footer_text="RESCUE SYSTEM",
                        button_text="Ver opciones",
                        sections=sections
                    )
   

        except Exception  as ex:
            self.logger.error(f"Error en _send_options_user {ex}")
            return False
    def _resolve_empresa_id(self, phone: str, current_empresa_id: Optional[str] = None) -> Optional[str]:
        """Obtener empresa_id a partir del número de teléfono"""
        if current_empresa_id:
            return current_empresa_id

        if not self.backend_client:
            self.logger.error("❌ No hay backend_client para resolver empresa_id")
            return None

        try:
            response = self.backend_client.verify_user_number(phone)
        except Exception as ex:
            self.logger.error(f"❌ Error verificando número {phone} para obtener empresa_id: {ex}")
            return None

        if not response:
            self.logger.error("❌ Respuesta vacía al verificar número para empresa_id")
            return None

        status_code = response.get('_status_code', 200)
        if status_code in (401, 404):
            self.logger.error(f"❌ Backend devolvió status {status_code} al verificar número {phone}")
            return None

        if not response.get('success', False):
            self.logger.error("❌ Verificación de número no exitosa, no se puede obtener empresa_id")
            return None

        data = response.get('data', {}) or {}
        empresa_id = data.get('empresa_id')
        empresa_info = data.get('empresa')

        if isinstance(empresa_info, dict):
            empresa_id = empresa_id or empresa_info.get('id') or empresa_info.get('_id')

        if not empresa_id and isinstance(empresa_info, str):
            self.logger.warning(f"⚠️ Empresa proporcionada sin identificador para {phone}: {empresa_info}")

        return empresa_id

    def _ensure_unique_row_id(
        self,
        base_id: str,
        alert_type: Dict[str, Any],
        seen_ids: Set[str],
        index: int,
        empresa_id: Optional[str],
    ) -> str:
        """Garantizar que el ID de la fila sea único en la sección"""
        candidates = [
            alert_type.get("id"),
            alert_type.get("_id"),
            alert_type.get("uuid"),
            alert_type.get("uid"),
            alert_type.get("codigo"),
            alert_type.get("code"),
            alert_type.get("tipo_alerta"),
            alert_type.get("identificador")
        ]

        for candidate in candidates:
            candidate_str = str(candidate).strip() if candidate is not None else ""
            if candidate_str and candidate_str not in seen_ids:
                self.logger.warning(
                    "⚠️ ID duplicado en lista WhatsApp (%s). Ajustando a '%s'",
                    base_id,
                    candidate_str,
                )
                return candidate_str

        suffix = 1
        unique_id = f"{base_id or 'option'}-{index + 1}"
        while unique_id in seen_ids:
            suffix += 1
            unique_id = f"{base_id or 'option'}-{index + 1}-{suffix}"

        self.logger.warning(
            "⚠️ ID duplicado en lista WhatsApp (%s) para empresa %s. Se asigna '%s'",
            base_id,
            empresa_id,
            unique_id,
        )
        return unique_id


    def _send_alert_created_template(
        self,
        recipients: List[Dict],
        alert_info: Dict,
        creator_name: Optional[str]
    ) -> None:
        """Enviar plantilla de alerta creada antes de otros mensajes"""
        if not self.whatsapp_service:
            return

        template_recipients = []
        alert_name = alert_info.get("nombre_alerta") or alert_info.get("nombre") or "Alerta"
        empresa = alert_info.get("empresa_nombre") or alert_info.get("empresa") or "la empresa"
        creator = creator_name or alert_info.get("activacion_alerta", {}).get("nombre", "un miembro autorizado")

        for usuario in recipients:
            numero = usuario.get("numero")
            if not numero:
                continue

            
            template_recipients.append({
                "phone": numero,
                "template_name": "alerta_creada",
                "language": "es_CO",
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": alert_name},
                            {"type": "text", "text": empresa},
                            {"type": "text", "text": creator}
                        ]
                    }
                ]
            })

        if template_recipients:
            self.whatsapp_service.send_bulk_template(
                recipients=template_recipients,
                use_queue=True
            )

    def _map_backend_alert_type(self, alert_type: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Convertir un tipo de alerta del backend al formato de WhatsApp list"""
        if not isinstance(alert_type, dict):
            return None

        row_id = (
            alert_type.get("id")
            or alert_type.get("_id")
            or alert_type.get("uuid")
            or alert_type.get("uid")
            or alert_type.get("codigo")
            or alert_type.get("code")
            or alert_type.get("tipo_alerta")
            or alert_type.get("identificador")
        )

        if not row_id:
            return None

        row_id_str = str(row_id).strip()
        if not row_id_str:
            return None

        title = alert_type.get("nombre") or alert_type.get("titulo") or alert_type.get("name") or str(row_id)
        description = alert_type.get("descripcion") or alert_type.get("description") or ""

        return {
            "id": row_id_str,
            "title": str(title),
            "description": str(description)
        }

    def _build_alert_sections(self, phone: str, empresa_id: Optional[str]) -> list[Dict[str, Any]]:
        """Obtener secciones de alertas consultando el backend"""
        sections: list[Dict[str, Any]] = []

        resolved_empresa_id = self._resolve_empresa_id(phone, empresa_id)

        if not resolved_empresa_id:
            self.logger.error("❌ No se recibió empresa_id para obtener tipos de alerta")
            return sections

        if not self.backend_client or not hasattr(self.backend_client, "get_empresa_alarm_types"):
            self.logger.error("❌ Backend client no soporta consulta de tipos de alerta")
            return sections

        try:
            response = self.backend_client.get_empresa_alarm_types(resolved_empresa_id)
        except Exception as ex:
            self.logger.error(f"❌ Error consultando tipos de alerta para empresa {empresa_id}: {ex}")
            return sections

        if not response:
            self.logger.error("❌ Respuesta vacía al consultar tipos de alerta")
            return sections

        success_value = response.get("success")
        if success_value is False:
            error_msg = response.get("message", "Respuesta inválida")
            self.logger.error(f"❌ Backend rechazó la consulta de tipos de alerta: {error_msg}")
            return sections

        alert_types_raw = response.get("data")

        potential_lists = []
        if isinstance(alert_types_raw, list):
            potential_lists.append(alert_types_raw)
        elif isinstance(alert_types_raw, dict):
            for key in ("tipos", "tipos_alerta", "alert_types", "items", "results", "data"):
                value = alert_types_raw.get(key)
                if isinstance(value, list):
                    potential_lists.append(value)
            # some APIs return {'success': True, 'data': {'items': [...] }} and also include list under same dict
            if not potential_lists and all(isinstance(v, dict) for v in alert_types_raw.values()):
                potential_lists.append(list(alert_types_raw.values()))

        for alert_type_list in potential_lists:
            rows = []
            seen_row_ids: Set[str] = set()
            for index, alert_type in enumerate(alert_type_list):
                mapped_row = self._map_backend_alert_type(alert_type)
                if not mapped_row:
                    continue

                row_id = mapped_row.get("id", "").strip()
                if not row_id:
                    row_id = f"option-{index + 1}"

                if row_id in seen_row_ids:
                    row_id = self._ensure_unique_row_id(
                        base_id=row_id,
                        alert_type=alert_type,
                        seen_ids=seen_row_ids,
                        index=index,
                        empresa_id=resolved_empresa_id,
                    )

                mapped_row["id"] = row_id
                seen_row_ids.add(row_id)
                rows.append(mapped_row)

            if rows:
                sections.append({"title": "Servicios técnicos", "rows": rows})
                break

        if not sections:
            self.logger.error("❌ No se encontraron tipos de alerta válidos en la respuesta del backend")

        return sections

    def _send_create_alarma(self, number, usuario, is_in_cached: bool = False, message_time=None, empresa_id: Optional[str] = None) -> bool:
        """Crear y enviar lista de alarmas por WhatsApp"""
        if not self.whatsapp_service:
            self.logger.warning("⚠️ WhatsApp service no disponible")
            return False
            
        try:
            resolved_empresa_id = empresa_id or self._resolve_empresa_id(number)

            if not resolved_empresa_id:
                self.logger.error("❌ No se enviará menú de alertas: empresa_id desconocido")
                self.whatsapp_service.send_individual_message(
                    phone=number,
                    message=(
                        "⚠️ No se pudo identificar la empresa asociada a tu cuenta. "
                        "Contacta al administrador para validar tu registro."
                    ),
                    use_queue=True
                )
                return False

            if not empresa_id:
                try:
                    self.whatsapp_service.update_number_cache(
                        phone=number,
                        data={"empresa_id": resolved_empresa_id},
                        empresa_id=resolved_empresa_id
                    )
                except Exception as ex:
                    self.logger.warning(f"⚠️ No se pudo actualizar el cache con empresa_id: {ex}")

            sections = self._build_alert_sections(number, resolved_empresa_id)
            if not sections:
                self.logger.error("❌ No se enviará menú de alertas por falta de datos dinámicos")
                if self.whatsapp_service:
                    info_message = (
                        "⚠️ No se encontraron tipos de alerta configurados para tu empresa. "
                        "Contacta al administrador para habilitarlos."
                    )
                    self.whatsapp_service.send_individual_message(
                        phone=number,
                        message=info_message,
                        use_queue=True
                    )
                return False
  
            if message_time is not None:
                body_text = message_time
            else:
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

    def _create_alarm_in_back(self, usuario_id: str, tipo_alerta: str, descripcion: str, 
                            latitud: str = "0.0", longitud: str = "0.0") -> Dict:
        """
        Crear alerta en el backend con ubicación.
        Si no se proporcionan coordenadas, se usan valores por defecto.
        """
        prioridad = "media"
        try:
            response = self.backend_client.create_user_alert(
                usuario_id=usuario_id,
                latitud=latitud,
                longitud=longitud,
                tipo_alerta=tipo_alerta, 
                descripcion=descripcion, 
                prioridad=prioridad
            )
            self.logger.info(f"Alerta {tipo_alerta}, creada por {usuario_id} en ubicación ({latitud}, {longitud})")
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
        stats = {
            "processed_messages": self.whatsapp_processed_count,
            "error_count": self.whatsapp_error_count,
            "error_rate": round(self.whatsapp_error_count / max(self.whatsapp_processed_count, 1) * 100, 2),
            "queue_size": self.whatsapp_queue.qsize(),
            "queue_max_size": self.whatsapp_queue.maxsize,
            "is_processing": self.is_processing
        }
        
        # Agregar estadísticas del handler de empresa si está disponible
        if self.empresa_handler:
            empresa_stats = self.empresa_handler.get_statistics()
            stats["empresa_handler"] = empresa_stats
        
        return stats
    
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
  
    def _send_create_down_alarma(self,list_users: list, alert: Dict, data_user: Dict = {}) -> bool:
        """Crear notificación de alarma por WhatsApp"""
        if not self.whatsapp_service:
            self.logger.warning("⚠️ WhatsApp service no disponible")
            return False

        if not self._has_creator_permission(data_user):
            return False
        try:
           # print(json.dumps(alert,indent=4))
            image = alert["image_alert"]
            alert_name = alert["nombre_alerta"]
            empresa = data_user["data"]["empresa"]
            recipients = []
            for item in list_users:
                body_text = f"¡Hola {item['nombre']}!.\nAlerta de {alert_name} {empresa}"
                data = {
                    "phone": item.get("numero", ""),
                    "body_text": body_text
                }
                recipients.append(data)
                
            buttons = [
                {
                    "id": "APAGAR ALARMA",
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
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando notificación de alarma: {e}")
            return False
    def _send_create_active_user(self, list_users: list, alert: Dict, data_user: Dict = {}) -> bool:
        """Crear notificación de alarma por WhatsApp"""
        if not self.whatsapp_service or not self.backend_client:
            self.logger.warning("⚠️ WhatsApp service o backend client no disponibles")
            return False
            
        try:
            print(f"La alerta es {json.dumps(alert,indent=4)}")
            data_create = alert.get("activacion_alerta",{})
            image = alert["image_alert"]
            alert_name = alert["nombre_alerta"]
            empresa = data_user["data"]["empresa"]
            recipients = []
            footer = f"Creada por {data_create['nombre']}\nEquipo RESCUE"
            
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
                    "id": "Activar_User",
                    "title": "Estoy disponible"
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
            self.logger.info(f"✅notificacion de activacion de usuario enviada a {len(recipients)} usuarios")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando notificación de activacion de usuario: {e}")
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

    def _select_data_hardware(self, topic, alert:Dict) -> Dict:
        """Seleccionar datos específicos según el tipo de hardware"""
        alarm_color = alert.get("tipo_alerta", "")
        location = alert.get("ubicacion",{})
        if "SEMAFORO" in topic:
            message_data = {
                "tipo_alarma": alarm_color,
            }
        elif "PANTALLA" in topic:
            message_data = {
                "tipo_alarma": alarm_color,
                "prioridad": alert.get("prioridad",""),
                "ubicacion": location.get("direccion", ""),
                "url": location.get("url_maps", ""),
                "elementos_necesarios": alert.get("elementos_necesarios", []),
                "instrucciones": alert.get("instrucciones", [])
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
        elif "PANTALLA" in topic:
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

    def _handle_create_empresa_alert_sync(self, message_data: Dict) -> bool:
        """Manejar mensaje de creación de alerta de empresa con alert_data incluido"""
        try:
            self.logger.info("🏢 Procesando comando de crear alerta de empresa")
            
            # Validar campos requeridos en el nuevo formato
            required_fields = ["type", "alert_data"]
            for field in required_fields:
                if field not in message_data:
                    self.logger.error(f"❌ Campo requerido faltante: {field}")
                    return False
            
            # Extraer alert_data completo del mensaje
            alert_data = message_data["alert_data"]
            
            # Validar que alert_data tenga los campos mínimos necesarios
            required_alert_fields = ["_id", "tipo_alerta", "descripcion"]
            for field in required_alert_fields:
                if field not in alert_data:
                    self.logger.error(f"❌ Campo requerido en alert_data faltante: {field}")
                    return False
            
            # Extraer información básica para logging
            alert_id = alert_data.get("_id", "N/A")
            tipo_alerta = alert_data.get("tipo_alerta", "N/A")
            descripcion = alert_data.get("descripcion", "N/A")
            prioridad = alert_data.get("prioridad", "media")
            empresa_nombre = alert_data.get("empresa_nombre", "N/A")
            sede = alert_data.get("sede", "N/A")
            
            self.logger.info(f"📋 Procesando alerta de empresa recibida:")
            self.logger.info(f"   🆔 Alert ID: {alert_id}")
            self.logger.info(f"   🏢 Empresa: {empresa_nombre}")
            self.logger.info(f"   🏛️ Sede: {sede}")
            self.logger.info(f"   🔔 Tipo: {tipo_alerta}")
            self.logger.info(f"   📝 Descripción: {descripcion}")
            self.logger.info(f"   ⚡ Prioridad: {prioridad}")
            
            # Ya no es necesario crear la alerta en el backend, solo procesarla
            self.logger.info(f"✅ Alert data recibido completo, procesando con empresa handler...")
            
            # Crear estructura compatible con empresa handler
            empresa_message = {
                "type": "alert_created_by_empresa",
                "timestamp": alert_data.get("fecha_creacion", ""),
                "alert": alert_data
            }
            
            # Procesar con el empresa handler
            if not self.empresa_handler:
                self.logger.error("❌ Empresa handler no disponible")
                return False
            
            success = self.empresa_handler.process_empresa_activation(empresa_message)
            
            if success:
                self.whatsapp_processed_count += 1
                self.logger.info("✅ Alerta de empresa procesada exitosamente")
            else:
                self.whatsapp_error_count += 1
                self.logger.error("❌ Error procesando alerta con empresa handler")
                
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Error manejando creación de alerta de empresa: {e}")
            self.whatsapp_error_count += 1
            return False
    
    def _handle_empresa_message_sync(self, message_data: Dict) -> bool:
        """Manejar mensaje de desactivación por empresa (versión síncrona para Redis)"""
        try:
            if not self.empresa_handler:
                self.logger.error("❌ Empresa handler no disponible")
                return False
            
            # Procesar con el handler específico de empresa (ahora maneja activación y desactivación)
            success = self.empresa_handler.process_empresa_alert(message_data)
            
            if success:
                self.whatsapp_processed_count += 1
                self.logger.info("✅ Mensaje de empresa procesado exitosamente")
            else:
                self.whatsapp_error_count += 1
                self.logger.error("❌ Error procesando mensaje de empresa")
                
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Error manejando mensaje de empresa: {e}")
            self.whatsapp_error_count += 1
            return False


    async def stop_whatsapp_processing(self):
        """Detener el procesamiento de la cola de WhatsApp"""
        # Detener workers de Redis si existen
        if self.redis_queue:
            self.redis_queue.stop_workers()
        
        # Detener empresa handler si existe
        if self.empresa_handler:
            self.empresa_handler.stop()
        
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
                    success_message = f"¡Perfecto {nombre.split()[0].upper()}!"
                    success_message += f"\n\nAlarma desactivada exitosamente"
                    success_message += f"\nFecha: {fecha_desactivacion.split('T')[0] if fecha_desactivacion else 'Ahora'}"
                    success_message += f"\n\nEl sistema RESCUE ha registrado tu acción"
                    success_message += f"\n¡Gracias por mantener la seguridad!"
                    success_message += f"\n\nSistema RESCUE - Siempre Vigilante"
                else:
                    # Mensaje para otros usuarios
                    success_message = f"¡Hola {nombre.split()[0].upper()}!"
                    success_message += f"\n\nLa alarma ha sido DESACTIVADA"
                    success_message += f"\nDesactivada por: {user}"
                    success_message += f"\nMomento: Ahora mismo"
                    success_message += f"\n\nEl sistema vuelve a estar en estado normal"
                    success_message += f"\nEQUIPO RESCUE"
                
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
            error_message = f"¡Hola {user.split()[0].upper()}!"
            error_message += f"\n\nℹEsta alarma ya fue DESACTIVADA anteriormente"
            
            # Obtener información de quién la desactivó si está disponible
            if response and response.get('desactivado_por', {}):
                desactivado_por = response.get('desactivado_por', {})
                fecha = desactivado_por.get('fecha_desactivacion', '')
                fecha_formato = fecha.split('T')[0] if fecha else 'Fecha desconocida'
                error_message += f"\n\nDesactivada el: {fecha_formato}"
                error_message += f"\nPor otro usuario del sistema"
            
            error_message += f"\n\nESTADO: La alarma ya está INACTIVA"
            error_message += f"\nNo hay riesgo activo en el sistema"
            error_message += f"\n\nGracias por tu atención a la seguridad"
            
            error_message += f"\n\nEQUIPO RESCUE"
            
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
                    notification_message = f"ℹ¡Hola {nombre.split()[0].upper()}!"
                    notification_message += f"\n\nLa alarma ha sido DESACTIVADA"
                    notification_message += f"\nDesactivada por: {deactivated_by}"
                    notification_message += f"\nMomento: Ahora mismo"
                    notification_message += f"\n\nEl sistema vuelve a estar en estado normal"
                    notification_message += f"\nEQUIPO RESCUE"
                    
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
    
    def _send_location_personalized_message(self, numeros_data: list, tipo_alarma_info: Dict) -> bool:
        """Enviar ubicación por WhatsApp usando CTA 'Abrir en Maps'"""

        if not self.whatsapp_service:
            self.logger.warning("⚠️ WhatsApp service no disponible")
            return False

        try:
            ubicacion = tipo_alarma_info.get("ubicacion", {}) if tipo_alarma_info else {}
            url_maps = ubicacion.get("url_maps") if isinstance(ubicacion, dict) else None

            if not url_maps:
                self.logger.warning("⚠️ No hay URL de ubicación disponible")
                return False

            success = self.whatsapp_service.send_bulk_location_button_message(
                recipients=numeros_data,
                url_maps=url_maps,
                footer_text="Equipo RESCUE",
                use_queue=True
            )

            if not success:
                self.logger.error("❌ Error enviando mensaje de ubicación con CTA")

            return success

        except Exception as e:
            self.logger.error(f"❌ Error enviando mensaje de ubicación: {e}")
            return False
