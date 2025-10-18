"""
Manejador de mensajes MQTT puro - SIN WHATSAPP
Solo procesa mensajes MQTT de BOTONERA y comunica con el backend
"""
import json
import logging
import threading
import time
from typing import Dict, Any, Optional


class MQTTMessageHandler:
    """Manejador de mensajes MQTT puro - SIN dependencias de WhatsApp"""
    
    def __init__(self, backend_client, mqtt_publisher=None, whatsapp_service=None, config=None):
        self.backend_client = backend_client
        self.mqtt_publisher = mqtt_publisher
        self.whatsapp_service = whatsapp_service  # Solo para ENVIAR cuando el backend lo requiera
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Estadísticas
        self.processed_messages = 0
        self.error_count = 0
        
        # Usar settings en lugar de .env directo
        self.pattern_topic = config.mqtt.topic if config else "empresas"
        
        self.logger.info("🎯 MQTT Message Handler - SOLO procesamiento MQTT")
        self.logger.info("❌ SIN procesamiento de mensajes WhatsApp entrantes")

    def process_mqtt_message(self, topic: str, payload: str, json_data: Optional[Dict] = None) -> bool:
        """FILTRO ABSOLUTO PARA BOTONERA - Solo procesar topics que terminen después del hardware"""
        
        # SOLO PROCESAR SI EL TOPIC CONTIENE "BOTONERA" Y TIENE MENSAJES APROPIADOS
        if "BOTONERA" in topic:
            topic_parts = topic.split("/")
            
            # Buscar la posición de BOTONERA
            botonera_index = -1
            for i, part in enumerate(topic_parts):
                if "BOTONERA" in part:
                    botonera_index = i
                    break
            
            # Verificar que después de BOTONERA hay exactamente 1 parte más (el nombre del hardware)
            if botonera_index != -1 and botonera_index + 1 < len(topic_parts):
                # Obtener partes después de BOTONERA
                parts_after_botonera = topic_parts[botonera_index + 1:]
                
                # Filtrar partes vacías (por barras al final como "/")
                parts_after_botonera = [part for part in parts_after_botonera if part.strip()]
                
                # Solo procesar si hay exactamente 1 parte después de BOTONERA
                if len(parts_after_botonera) == 1:
                    hardware_name = parts_after_botonera[0]
                    
                    self.logger.info(f"🚨 BOTONERA: {hardware_name} - {topic}")
                    
                    # Verificar que el payload no sea de tipo desactivación
                    if payload and isinstance(payload, str):
                        try:
                            json_data = json.loads(payload)
                            if json_data.get("tipo_alarma") == "NORMAL":
                                self.logger.info(f"⚠️ Ignorando mensaje de tipo NORMAL para {hardware_name}")
                                return True
                        except json.JSONDecodeError:
                            self.logger.error(f"❌ JSON inválido en payload: {payload}")
                            return False
                        except Exception as e:
                            self.logger.error(f"❌ Error al procesar payload: {e}")
                            return False
                    
                    # Procesar JSON de BOTONERA (cualquier estructura)
                    try:
                        #json_data = json.loads(payload)
                        
                        # ENVIAR DATOS AL BACKEND (usando hilo)
                        self._send_botonera_to_backend(hardware_name, json_data, topic, payload)
                        
                        self.processed_messages += 1
                        return True
                        
                    except json.JSONDecodeError as e:
                        self.logger.error(f"❌ JSON inválido: {e}")
                        self.error_count += 1
                        return False
                    except Exception as e:
                        self.logger.error(f"❌ Error procesando: {e}")
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
            return True

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
                self.logger.error(f"❌ Formato de topic inválido")
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
                self.logger.error(f"❌ Autenticación fallida")
                return False
            
            response = self.backend_client.send_alarm_data(mqtt_data, token)
            #print(json.dumps(response,indent=4))
            if response:
                self._handle_alarm_notifications(response, mqtt_data)
                return True
            else:
                self.logger.error(f"❌ Error enviando alarma")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error: {e}")
            return False

    def _handle_alarm_notifications(self, response: Dict, mqtt_data: Dict) -> None:
        """Procesar respuesta del backend y enviar notificaciones - COMPLETO como WebSocket handler"""
        try:
            # ENVIAR MENSAJES MQTT A OTROS HARDWARE
            self._send_mqtt_message(data=response, mqtt_data=mqtt_data)
            
            # PROCESAR NOTIFICACIONES WHATSAPP (replicando WebSocket handler)
            if self.whatsapp_service:
                alert_data = response.get("alert", {})
                list_users = alert_data.get("numeros_telefonicos", [])
                if list_users and alert_data:
                    hardware_location = alert_data.get("ubicacion", {})
                    if hardware_location:
                        self._send_location_personalized_message(
                            numeros_data=list_users,
                            hardware_location=hardware_location
                        )
                        time.sleep(2)  
                    # 1. ENVIAR MENSAJE DE UBICACIÓN
                    else:
                        self.logger.warning("⚠️ No hay datos de ubicación para enviar")
                    self._send_create_active_user(
                        alert=alert_data,
                        list_users=list_users,
                        mqtt_data=mqtt_data 
                    )
                  
                    
                    
                    # 3. CREAR CACHE MASIVO PARA TODOS LOS USUARIOS
                    self._create_bulk_cache(
                        alarm_info=alert_data,
                        list_users=list_users,
                        mqtt_data=mqtt_data
                    )
                    
                    # 4. ENVIAR COMANDOS MQTT A OTROS HARDWARE (usando método limpio)
                    topics = alert_data.get("topics_otros_hardware", [])
                    if topics:
                        self._intermediate_to_mqtt(alert_data, topics)
                    else:
                        self.logger.info("ℹ️ No hay topics adicionales de hardware para activar")
                else:
                    self.logger.warning("⚠️ No hay usuarios o datos de alerta para procesar")
            else:
                self.logger.info("ℹ️ WhatsApp service no disponible - solo procesamiento MQTT")
            
            self.logger.info(f"✅ Procesamiento completo de notificaciones completado")
            
        except Exception as e:
            self.logger.error(f"❌ Error manejando notificaciones: {e}")
    
    def _intermediate_to_mqtt(self, alert, topics) -> None:
        """Enviar alertas a MQTT - IGUAL al WebSocket handler"""
        try:
            # Enviar alerta a mqtt usando el mismo método que WebSocket
            for topic in topics:
                full_topic = self.pattern_topic + "/" + topic
                message_hardware = self._select_data_hardware(alert=alert, topic=full_topic)
                self.send_mqtt_message(topic=full_topic, message_data=message_hardware)

        except Exception as ex:
            self.logger.error(f"❌ Error en el intermediario a enviar mensajes al mqtt: {ex}")

    def _send_mqtt_message(self, data, mqtt_data) -> None:
        """Enviar mensajes MQTT a otros hardware - IGUAL al WebSocket handler"""
        try:
            # Obtener datos de la alerta desde la respuesta
            alert_data = data.get("alert", {})
            if not alert_data:
                self.logger.warning("⚠️ No hay datos de alert en la respuesta")
                return
            
            # Obtener topics desde alert_data (igual que WebSocket)
            topics = alert_data.get("topics_otros_hardware", [])
            if not topics:
                self.logger.info("ℹ️ No hay topics adicionales de hardware para activar")
                return
                
            # Enviar mensajes usando el mismo método que WebSocket
            self._intermediate_to_mqtt(alert=alert_data, topics=topics)
                    
        except Exception as e:
            self.logger.error(f"❌ Error enviando mensajes MQTT: {e}")

    def _select_data_hardware(self, topic, alert: Dict) -> Dict:
        """Seleccionar datos específicos según el tipo de hardware - IGUAL al WebSocket handler"""
      #  print(json.dumps(alert,indent=4))
        data_alert = alert.get("data",{})
        alarm_color = data_alert.get("tipo_alarma", "")
        location = alert.get("ubicacion", {})
        
        if "SEMAFORO" in topic:
            message_data = {
                "tipo_alarma": alarm_color,
            }
        elif "PANTALLA" in topic:
            message_data = {
                "tipo_alarma": alarm_color,
                "prioridad": alert.get("prioridad", ""),
                "ubicacion": location.get("direccion", ""),
                "url": location.get("url_open_maps", ""),
                "elementos_necesarios": alert.get("elementos_necesarios", []),
                "instrucciones": alert.get("instrucciones", [])
            }
        else:
            message_data = {
                "action": "generic",
                "message": "notificación genérica",
            }
            
        return message_data
  
    def _send_location_personalized_message(self, numeros_data: list, hardware_location: Dict) -> bool:
        """Enviar mensaje personalizado de ubicación por WhatsApp"""
    
        if not self.whatsapp_service:
            self.logger.warning("⚠️ WhatsApp service no disponible")
            return False
            
        try:
            url_maps = hardware_location.get("url_maps", "")
            parametro = url_maps.split("place/")[1]
            recipients = []
            
            for item in numeros_data:
                nombre = str(item.get("nombre", ""))
                recipient = {
                    "phone": item["numero"],
                    "template_name": "location_alert",
                    "language": "es_CO",
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": nombre}
                            ]
                        },
                        {
                            "type": "button",
                            "sub_type": "url",
                            "index": "0",
                            "parameters": [
                                {"type": "text", "text": parametro}
                            ]
                        }
                    ]
                }
            
                recipients.append(recipient)
            
            result = self.whatsapp_service.send_bulk_template(recipients=recipients)
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando mensaje de ubicación: {e}")
            return False

    def _send_create_down_alarma(self, list_users: list, alert: Dict, data_user: Dict = {},alert_id = str) -> bool:
        """Crear notificación de alarma por WhatsApp"""
        if not self.whatsapp_service:
            self.logger.warning("⚠️ WhatsApp service no disponible")
            return False
            
        try:
           # print(json.dumps(alert,indent=4))
            id_alert = alert_id
            image = alert["imagen_base64"]
            alert_name = alert["nombre"]
            empresa = "en " + data_user.get("empresa", "la empresa")
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
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando notificación de alarma: {e}")
            return False

    def send_mqtt_message(self, topic: str, message_data: Dict, qos: int = 0) -> bool:
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
   
    def _send_create_active_user(self, alert: Dict, list_users: list, mqtt_data: Dict) -> bool:
        """Crear notificación de activación de usuario por WhatsApp - IGUAL al WebSocket handler"""
        if not self.whatsapp_service:
            self.logger.warning("⚠️ WhatsApp service no disponible")
            return False
            
        try:
            # Usar los mismos campos que el WebSocket handler
            data_create = alert.get("activacion_alerta", {})
            image = alert["image_alert"]
            alert_name = alert["nombre_alerta"]
            empresa = mqtt_data.get("empresa", "la empresa")
            recipients = []
            footer = f"Creada por {data_create.get('nombre', 'Hardware')}\nEquipo RESCUE"
            
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
            self.logger.info(f"✅ Notificación de activación de usuario enviada a {len(recipients)} usuarios")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando notificación de activación de usuario: {e}")
            return False

    def _create_bulk_cache(self, alarm_info: Dict, list_users: list, mqtt_data: Dict) -> None:
        """Crear cache masivo actualizado para todos los usuarios"""
        try:
            empresa_id = alarm_info.get("empresa_id")
            if not empresa_id:
                empresa_data = alarm_info.get("empresa")
                if isinstance(empresa_data, dict):
                    empresa_id = empresa_data.get("id") or empresa_data.get("_id")

            for user in list_users:
                user_id = user.get("usuario_id", "")
                cache_data = {
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),  # Fecha de creacion
                    "data": {
                        "alert_active": True,
                        "disponible": user.get("disponible", True),
                        "embarcado": user.get("embarcado", False),
                        "empresa": mqtt_data.get("empresa", ""),
                        "id": user_id,
                        "info_alert": {
                            "alert_id": alarm_info.get("_id", "")
                        }
                    },
                    "name": user.get("nombre", ""),
                    "phone": user.get("numero", "")
                }

                if empresa_id:
                    cache_data["data"]["empresa_id"] = empresa_id
                
                # Simular guardar en el cache
                self.whatsapp_service.add_number_to_cache(
                    phone=user.get("numero", ""),
                    name=user.get("nombre", ""),
                    data=cache_data["data"],
                    empresa_id=empresa_id
                )
                self.logger.info(f'📝 Cache creado para usuario {user.get("numero")}: {json.dumps(cache_data, indent=2)}')
            self.logger.info(f'✅ Cache masivo actualizado creado para {len(list_users)} usuarios')
        except Exception as e:
            self.logger.error(f'❌ Error creando cache masivo actualizado: {e}')
            return False


    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del manejador MQTT"""
        return {
            "processed_messages": self.processed_messages,
            "error_count": self.error_count,
            "error_rate": round(self.error_count / max(self.processed_messages, 1) * 100, 2),
            "hardware_types_count": 1  # Solo BOTONERA
        }
