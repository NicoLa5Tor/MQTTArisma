"""
Handler específico para alertas desactivadas por empresa
Solo maneja WhatsApp Service y MQTT Publisher
"""
import json
import logging
from typing import Dict, Any, Optional, List
from clients.mqtt_publisher_lite import MQTTPublisherLite
from config.settings import MQTTConfig


class EmpresaAlertHandler:
    """Handler específico para alertas desactivadas por empresa"""
    
    def __init__(self, whatsapp_service=None, config=None, enable_mqtt_publisher=True):
        self.whatsapp_service = whatsapp_service
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Estadísticas específicas
        self.processed_count = 0
        self.error_count = 0
        
        # Configurar pattern topic igual que en websocket handler
        self.pattern_topic = config.mqtt.topic if config else "empresas"
        
        # MQTT Publisher para envío a dispositivos
        self.mqtt_publisher = None
        if enable_mqtt_publisher and config:
            try:
                publisher_config = MQTTConfig(
                    broker=config.mqtt.broker,
                    port=config.mqtt.port,
                    topic=config.mqtt.topic,
                    username=config.mqtt.username,
                    password=config.mqtt.password,
                    client_id=f"{config.mqtt.client_id}_empresa_handler",
                    keep_alive=config.mqtt.keep_alive
                )
                self.mqtt_publisher = MQTTPublisherLite(publisher_config)
                if self.mqtt_publisher.connect():
                    self.logger.info("✅ MQTT Publisher conectado desde Empresa Handler")
                else:
                    self.logger.warning("⚠️ Error conectando MQTT Publisher en Empresa Handler")
                    self.mqtt_publisher = None
            except Exception as e:
                self.logger.error(f"❌ Error iniciando MQTT Publisher en Empresa Handler: {e}")
                self.mqtt_publisher = None
        
        self.logger.info("🏢 Empresa Alert Handler iniciado")
        self.logger.info("📱 WhatsApp Service + MQTT Publisher habilitados")

    def process_empresa_deactivation(self, message_data: Dict) -> bool:
        """Procesar desactivación de alerta por empresa"""
        try:
            self.logger.info("🏢 Procesando desactivación de alerta por empresa")
            
            # Validar estructura del mensaje
            if not self._validate_empresa_message(message_data):
                self.logger.error("❌ Estructura de mensaje inválida para empresa")
                return False
            
            # Extraer datos principales de la nueva estructura
            alert = message_data.get("alert", {})
            timestamp = message_data.get("timestamp", "")
            
            alert_id = alert.get("id", "N/A")
            alert_name = alert.get("nombre", "Alerta")
            empresa = alert.get("empresa", "La Empresa")
            sede = alert.get("sede", "")
            prioridad = alert.get("prioridad", "media")
            usuarios = alert.get("usuarios", [])
            hardware_vinculado = alert.get("hardware_vinculado", [])
            desactivado_por = alert.get("desactivado_por", {})
            
            self.logger.info(f"📋 Datos extraídos:")
            self.logger.info(f"   🚨 Alert ID: {alert_id}")
            self.logger.info(f"   📛 Nombre: {alert_name}")
            self.logger.info(f"   👥 Usuarios: {len(usuarios)}")
            self.logger.info(f"   📡 Hardware: {len(hardware_vinculado)}")
            self.logger.info(f"   🏢 Empresa: {empresa}")
            self.logger.info(f"   🏛️ Sede: {sede}")
            
            # 1. Limpiar caché de usuarios afectados (igual que WebSocket handler)
            cache_success = self._clean_users_cache_after_deactivation(usuarios)
            
            # 2. Enviar notificación WhatsApp a usuarios
            whatsapp_success = self._send_empresa_deactivation_notification(
                usuarios=usuarios,
                alert_info={
                    "id": alert_id,
                    "nombre": alert_name,
                    "empresa": empresa,
                    "sede": sede,
                    "timestamp": timestamp,
                    "desactivado_por": desactivado_por
                }
            )
            
            # 3. Enviar comandos MQTT a dispositivos hardware
            mqtt_success = self._send_mqtt_deactivation_commands(
                hardware_list=hardware_vinculado,
                prioridad=prioridad
            )
            
            # Actualizar estadísticas
            if cache_success and whatsapp_success and mqtt_success:
                self.processed_count += 1
                self.logger.info("✅ Desactivación por empresa procesada exitosamente")
                return True
            else:
                self.error_count += 1
                self.logger.warning("⚠️ Desactivación parcialmente exitosa")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error procesando desactivación por empresa: {e}")
            self.error_count += 1
            return False

    def _validate_empresa_message(self, message_data: Dict) -> bool:
        """Validar estructura del mensaje de empresa"""
        # Verificar campos principales
        if "type" not in message_data or message_data["type"] != "alert_deactivated_by_empresa":
            self.logger.error("❌ Tipo de mensaje incorrecto")
            return False
            
        if "alert" not in message_data:
            self.logger.error("❌ Campo 'alert' faltante")
            return False
        
        alert = message_data["alert"]
        
        # Validar campos requeridos en alert
        required_alert_fields = ["id", "usuarios", "hardware_vinculado"]
        for field in required_alert_fields:
            if field not in alert:
                self.logger.error(f"❌ Campo requerido faltante en alert: {field}")
                return False
        
        # Validar que usuarios sea una lista
        if not isinstance(alert["usuarios"], list):
            self.logger.error("❌ alert.usuarios debe ser una lista")
            return False
            
        # Validar que hardware_vinculado sea una lista
        if not isinstance(alert["hardware_vinculado"], list):
            self.logger.error("❌ alert.hardware_vinculado debe ser una lista")
            return False
        
        return True

    def _clean_users_cache_after_deactivation(self, usuarios: List[Dict]) -> bool:
        """Limpiar caché de usuarios después de desactivación (igual que WebSocket handler)"""
        if not self.whatsapp_service:
            self.logger.warning("⚠️ WhatsApp service no disponible para limpieza de caché")
            return False
            
        try:
            # Crear estructura de datos igual que en WebSocket handler
            list_user_format = []
            for usuario in usuarios:
                telefono = usuario.get("telefono", "")
                nombre = usuario.get("nombre", "Usuario")
                
                # Limpiar formato del teléfono si es necesario
                if telefono.startswith("+"):
                    telefono = telefono[1:]  # Remover el +
                
                if telefono:
                    list_user_format.append({
                        "numero": telefono,
                        "nombre": nombre
                    })
            
            if not list_user_format:
                self.logger.warning("⚠️ No hay usuarios válidos para limpiar caché")
                return False
            
            # Usar la misma estructura de datos de limpieza que el WebSocket handler
            data_to_delete = {
                "info_alert": "__DELETE__",
                "alert_active": "__DELETE__", 
                "disponible": "__DELETE__",
                "embarcado": "__DELETE__"
            }
            
            # Extraer solo los números de teléfono
            list_phones = [user["numero"] for user in list_user_format]
            
            # Usar el método bulk_update_numbers igual que en WebSocket handler
            self.whatsapp_service.bulk_update_numbers(phones=list_phones, data=data_to_delete)
            
            self.logger.info(f"✅ Caché limpiado para {len(list_phones)} usuarios")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error limpiando caché de usuarios: {e}")
            return False

    def _send_empresa_deactivation_notification(self, usuarios: List[Dict], alert_info: Dict) -> bool:
        """Enviar notificación de desactivación por empresa via WhatsApp"""
        if not self.whatsapp_service:
            self.logger.warning("⚠️ WhatsApp service no disponible")
            return False
            
        try:
            alert_id = alert_info.get("id", "N/A")
            alert_name = alert_info.get("nombre", "Alerta")
            empresa = alert_info.get("empresa", "La Empresa")
            sede = alert_info.get("sede", "")
            timestamp = alert_info.get("timestamp", "")
            desactivado_por = alert_info.get("desactivado_por", {})
            
            # Formatear fecha si existe
            fecha_formato = "Ahora"
            if timestamp:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    fecha_formato = dt.strftime("%d/%m/%Y %H:%M")
                except:
                    fecha_formato = timestamp
            
            recipients = []
            
            for usuario in usuarios:
                nombre = usuario.get("nombre", "Usuario")
                telefono = usuario.get("telefono", "")
                
                # Limpiar formato del teléfono si es necesario
                if telefono.startswith("+"):
                    telefono = telefono[1:]  # Remover el +
                
                if not telefono:
                    self.logger.warning(f"⚠️ Usuario {nombre} no tiene teléfono válido")
                    continue
                    
                # Mensaje personalizado para cada usuario
                notification_message = f"¡Hola {nombre.split()[0].upper()}!\n\n"
                notification_message += f"ALERTA DESACTIVADA POR {empresa.upper()}\n\n"
                notification_message += f"Detalles:\n"
                notification_message += f"Alerta: {alert_name}\n"
                
                if sede:
                    notification_message += f"Sede: {sede}\n"
                    
                notification_message += f"Momento: {fecha_formato}\n"
                notification_message += f"Desactivada por: {desactivado_por.get('nombre', empresa)}\n\n"
                notification_message += f"El sistema ha vuelto a estado normal\n"
                notification_message += f"SISTEMA RESCUE"
                
                recipients.append({
                    "phone": telefono,
                    "message": notification_message
                })
            
            if not recipients:
                self.logger.warning("⚠️ No hay destinatarios válidos para WhatsApp")
                return False
            
            # Enviar usando el cliente de WhatsApp para envío masivo
            response = self.whatsapp_service.send_bulk_individual(
                recipients=recipients,
                use_queue=True
            )
            
            if response:
                self.logger.info(f"✅ Notificación de empresa enviada a {len(recipients)} usuarios")
                return True
            else:
                self.logger.error("❌ Error enviando notificación masiva de empresa")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error enviando notificación WhatsApp de empresa: {e}")
            return False

    def _send_mqtt_deactivation_commands(self, hardware_list: List[Dict], prioridad: str) -> bool:
        """Enviar comandos de desactivación MQTT a dispositivos hardware"""
        if not self.mqtt_publisher:
            self.logger.warning("⚠️ MQTT Publisher no disponible")
            return False
            
        if not hardware_list:
            self.logger.info("ℹ️ No hay hardware para procesar")
            return True
            
        try:
            success_count = 0
            
            self.logger.info(f"🔄 Enviando comandos de desactivación MQTT a {len(hardware_list)} dispositivos")
            
            for hardware in hardware_list:
                topic = hardware.get("topic", "")
                hardware_name = hardware.get("nombre", "Hardware desconocido")
                hardware_id = hardware.get("id_origen", "N/A")
                
                if not topic:
                    self.logger.warning(f"⚠️ Hardware {hardware_name} no tiene topic definido")
                    continue
                
                # Usar el topic directamente (ya viene con la estructura completa)
                # Solo agregar el pattern_topic si no lo tiene
                if not topic.startswith(self.pattern_topic):
                    full_topic = f"{self.pattern_topic}/{topic}"
                else:
                    full_topic = topic
                
                # Crear mensaje de desactivación según el tipo de dispositivo
                deactivation_message = self._create_deactivation_message(
                    topic=topic, 
                    prioridad=prioridad
                )
                
                # No agregar información adicional - solo el mensaje básico
                
                # Enviar mensaje MQTT
                success = self._send_mqtt_message(message_data=deactivation_message, topic=full_topic)
                
                if success:
                    success_count += 1
                    self.logger.info(f"✅ Hardware desactivado: {hardware_name} ({hardware_id})")
                else:
                    self.logger.error(f"❌ Error desactivando hardware: {hardware_name} - Topic: {full_topic}")
            
            self.logger.info(f"📊 MQTT: {success_count}/{len(hardware_list)} dispositivos desactivados")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando comandos MQTT de empresa: {e}")
            return False

    def _create_deactivation_message(self, topic: str, prioridad: str) -> Dict:
        """Crear mensaje de desactivación específico según el tipo de dispositivo"""
        if "SEMAFORO" in topic:
            # Para semáforos: solo tipo_alarma NORMAL
            return {
                "tipo_alarma": "NORMAL"
            }
        elif "PANTALLA" in topic:
            # Para televisores: tipo_alarma NORMAL + prioridad
            return {
                "tipo_alarma": "NORMAL",
                "prioridad": prioridad.upper()
            }
        else:
            # Para dispositivos genéricos: solo tipo_alarma NORMAL
            return {
                "tipo_alarma": "NORMAL"
            }

    def _send_mqtt_message(self, topic: str, message_data: Dict, qos: int = 0) -> bool:
        """Enviar mensaje MQTT a un topic específico"""
        try:
            if not self.mqtt_publisher:
                return False
                
            success = self.mqtt_publisher.publish_json(topic, message_data, qos)
            
            if success:
                self.logger.debug(f"✅ Mensaje MQTT enviado a topic: {topic}")
                return True
            else:
                self.logger.error(f"❌ Error enviando mensaje MQTT a topic: {topic}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error enviando mensaje MQTT: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del handler de empresa"""
        return {
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "error_rate": round(self.error_count / max(self.processed_count + self.error_count, 1) * 100, 2),
            "mqtt_publisher_available": self.mqtt_publisher is not None,
            "whatsapp_service_available": self.whatsapp_service is not None
        }

    def stop(self):
        """Detener el handler y cerrar conexiones"""
        try:
            if self.mqtt_publisher:
                self.mqtt_publisher.disconnect()
                self.logger.info("🔌 MQTT Publisher desconectado en Empresa Handler")
                
            self.logger.info("🛑 Empresa Alert Handler detenido")
            
        except Exception as e:
            self.logger.error(f"❌ Error deteniendo Empresa Handler: {e}")
