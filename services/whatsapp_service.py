"""
Servicio de WhatsApp para envío de mensajes
"""
import logging
import time
from typing import Dict, Any, Optional, List
from clients.whatsapp_client import WhatsAppClient
from config.settings import WhatsAppConfig


class WhatsAppService:
    """
    Servicio para envío de mensajes WhatsApp que se integra con la arquitectura existente
    """
    
    def __init__(self, config: WhatsAppConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Crear cliente WhatsApp
        self.client = WhatsAppClient(config)
        
        # Estadísticas del servicio
        self.stats = {
            "start_time": time.time(),
            "individual_messages_sent": 0,
            "broadcast_messages_sent": 0,
            "total_recipients": 0,
            "errors": 0
        }
    
    def send_individual_message(self, phone: str, message: str, use_queue: bool = False) -> bool:
        """
        Enviar mensaje individual de WhatsApp
        
        Args:
            phone: Número del destinatario (formato internacional)
            message: Texto del mensaje
            use_queue: Si usar cola o no
            
        Returns:
            bool: True si se envió exitosamente, False en caso contrario
        """
        try:
            if not self.config.enabled:
                self.logger.warning("⚠️ Servicio WhatsApp deshabilitado")
                return False
            
            print(f"📱 Servicio WhatsApp - Enviando mensaje individual...")
            
            response = self.client.send_individual_message(phone, message, use_queue)
            
            if response:
                self.stats["individual_messages_sent"] += 1
                self.stats["total_recipients"] += 1
                
                print(f"✅ Mensaje individual enviado exitosamente")
                self.logger.info(f"Mensaje individual enviado a {phone}")
                return True
            else:
                self.stats["errors"] += 1
                print(f"❌ Error enviando mensaje individual")
                self.logger.error(f"Error enviando mensaje individual a {phone}")
                return False
                
        except Exception as e:
            self.stats["errors"] += 1
            print(f"💥 Error en servicio WhatsApp: {e}")
            self.logger.error(f"Error en servicio WhatsApp: {e}")
            return False
    
    def send_broadcast_message(self, phones: List[str], header_type: str, header_content: str,
                             body_text: str, button_text: str, button_url: str,
                             footer_text: str, use_queue: bool = True) -> bool:
        """
        Enviar mensaje broadcast interactivo de WhatsApp
        
        Args:
            phones: Lista de números destinatarios
            header_type: Tipo de encabezado
            header_content: Texto del encabezado
            body_text: Texto principal del mensaje
            button_text: Texto del botón
            button_url: URL del botón
            footer_text: Texto de pie de página
            use_queue: Si usar cola o no
            
        Returns:
            bool: True si se envió exitosamente, False en caso contrario
        """
        try:
            if not self.config.enabled:
                self.logger.warning("⚠️ Servicio WhatsApp deshabilitado")
                return False
            
            print(f"📱 Servicio WhatsApp - Enviando broadcast a {len(phones)} números...")
            
            response = self.client.send_broadcast_message(
                phones=phones,
                header_type=header_type,
                header_content=header_content,
                body_text=body_text,
                button_text=button_text,
                button_url=button_url,
                footer_text=footer_text,
                use_queue=use_queue
            )
            
            if response:
                self.stats["broadcast_messages_sent"] += 1
                self.stats["total_recipients"] += len(phones)
                
                print(f"✅ Broadcast enviado exitosamente a {len(phones)} números")
                self.logger.info(f"Broadcast enviado a {len(phones)} números")
                return True
            else:
                self.stats["errors"] += 1
                print(f"❌ Error enviando broadcast")
                self.logger.error(f"Error enviando broadcast a {len(phones)} números")
                return False
                
        except Exception as e:
            self.stats["errors"] += 1
            print(f"💥 Error en servicio WhatsApp broadcast: {e}")
            self.logger.error(f"Error en servicio WhatsApp broadcast: {e}")
            return False
    
    def send_personalized_broadcast(self, recipients: List[Dict], header_type: str, header_content: str,
                                   button_text: str, button_url: str, footer_text: str, use_queue: bool = True) -> bool:
        """
        Enviar mensaje broadcast personalizado de WhatsApp
        
        Args:
            recipients: Lista de diccionarios con 'phone' y 'body_text'
            header_type: Tipo de encabezado
            header_content: Contenido del encabezado
            button_text: Texto del botón
            button_url: URL del botón
            footer_text: Texto de pie de página
            use_queue: Si usar cola o no
            
        Returns:
            bool: True si se envió exitosamente, False en caso contrario
        """
        try:
            if not self.config.enabled:
                self.logger.warning("⚠️ Servicio WhatsApp deshabilitado")
                return False
            
            print(f"📱 Servicio WhatsApp - Enviando broadcast personalizado a {len(recipients)} destinatarios...")
            
            response = self.client.send_personalized_broadcast(
                recipients=recipients,
                header_type=header_type,
                header_content=header_content,
                button_text=button_text,
                button_url=button_url,
                footer_text=footer_text,
                use_queue=use_queue
            )
            
            if response:
                self.stats["broadcast_messages_sent"] += 1
                self.stats["total_recipients"] += len(recipients)
                
                print(f"✅ Broadcast personalizado enviado exitosamente a {len(recipients)} destinatarios")
                self.logger.info(f"Broadcast personalizado enviado a {len(recipients)} destinatarios")
                return True
            else:
                self.stats["errors"] += 1
                print(f"❌ Error enviando broadcast personalizado")
                self.logger.error(f"Error enviando broadcast personalizado a {len(recipients)} destinatarios")
                return False
                
        except Exception as e:
            self.stats["errors"] += 1
            print(f"💥 Error en servicio WhatsApp broadcast personalizado: {e}")
            self.logger.error(f"Error en servicio WhatsApp broadcast personalizado: {e}")
            return False
    
    def send_list_message(self, phone: str, header_text: str, body_text: str, 
                         footer_text: str, button_text: str, sections: List[Dict]) -> bool:
        """
        Enviar mensaje de lista de WhatsApp
        
        Args:
            phone: Número del destinatario (formato internacional)
            header_text: Texto del encabezado
            body_text: Texto principal del mensaje
            footer_text: Texto de pie de página
            button_text: Texto del botón
            sections: Lista de secciones con sus opciones
            
        Returns:
            bool: True si se envió exitosamente, False en caso contrario
        """
        try:
            if not self.config.enabled:
                self.logger.warning("⚠️ Servicio WhatsApp deshabilitado")
                return False
            
            print(f"📱 Servicio WhatsApp - Enviando mensaje de lista...")
            
            response = self.client.send_list_message(
                phone=phone,
                header_text=header_text,
                body_text=body_text,
                footer_text=footer_text,
                button_text=button_text,
                sections=sections
            )
            
            if response:
                self.stats["individual_messages_sent"] += 1
                self.stats["total_recipients"] += 1
                
                print(f"✅ Mensaje de lista enviado exitosamente")
                self.logger.info(f"Mensaje de lista enviado a {phone}")
                return True
            else:
                self.stats["errors"] += 1
                print(f"❌ Error enviando mensaje de lista")
                self.logger.error(f"Error enviando mensaje de lista a {phone}")
                return False
                
        except Exception as e:
            self.stats["errors"] += 1
            print(f"💥 Error en servicio WhatsApp enviando lista: {e}")
            self.logger.error(f"Error en servicio WhatsApp enviando lista: {e}")
            return False
    
    def add_number_to_cache(self, phone: str, name: str = None, data: Dict = None) -> bool:
        """
        Agregar número al cache de WhatsApp
        
        Args:
            phone: Número de teléfono (formato internacional)
            name: Nombre del contacto
            data: Datos adicionales del contacto
            
        Returns:
            bool: True si se agregó exitosamente, False en caso contrario
        """
        try:
            if not self.config.enabled:
                self.logger.warning("⚠️ Servicio WhatsApp deshabilitado")
                return False
            
            print(f"📞 Servicio WhatsApp - Agregando número al cache...")
            
            response = self.client.add_number_to_cache(phone, name, data)
            
            if response:
                print(f"✅ Número agregado al cache exitosamente")
                self.logger.info(f"Número {phone} agregado al cache")
                return True
            else:
                print(f"❌ Error agregando número al cache")
                self.logger.error(f"Error agregando número {phone} al cache")
                return False
                
        except Exception as e:
            print(f"💥 Error en servicio WhatsApp agregando al cache: {e}")
            self.logger.error(f"Error en servicio WhatsApp agregando al cache: {e}")
            return False
    
    def process_whatsapp_notification(self, notification: Dict[str, Any]) -> bool:
        """
        Procesar notificación de WhatsApp desde el backend
        
        Args:
            notification: Diccionario con datos de la notificación
            
        Returns:
            bool: True si se procesó exitosamente
        """
        try:
            message_type = notification.get('type', 'individual')
            
            if message_type == 'individual':
                return self._process_individual_notification(notification)
            elif message_type == 'broadcast':
                return self._process_broadcast_notification(notification)
            else:
                print(f"⚠️ Tipo de mensaje desconocido: {message_type}")
                return False
                
        except Exception as e:
            print(f"❌ Error procesando notificación WhatsApp: {e}")
            self.logger.error(f"Error procesando notificación WhatsApp: {e}")
            return False
    
    def _process_individual_notification(self, notification: Dict[str, Any]) -> bool:
        """Procesar notificación individual"""
        try:
            phone = notification.get('phone')
            message = notification.get('message')
            use_queue = notification.get('use_queue', False)
            
            if not phone or not message:
                print(f"❌ Notificación individual incompleta: falta phone o message")
                return False
            
            return self.send_individual_message(phone, message, use_queue)
            
        except Exception as e:
            print(f"❌ Error procesando notificación individual: {e}")
            return False
    
    def _process_broadcast_notification(self, notification: Dict[str, Any]) -> bool:
        """Procesar notificación broadcast"""
        try:
            phones = notification.get('phones', [])
            header_type = notification.get('header_type', 'text')
            header_content = notification.get('header_content', '')
            body_text = notification.get('body_text', '')
            button_text = notification.get('button_text', '')
            button_url = notification.get('button_url', '')
            footer_text = notification.get('footer_text', '')
            use_queue = notification.get('use_queue', True)
            
            if not phones or not body_text:
                print(f"❌ Notificación broadcast incompleta: falta phones o body_text")
                return False
            
            return self.send_broadcast_message(
                phones=phones,
                header_type=header_type,
                header_content=header_content,
                body_text=body_text,
                button_text=button_text,
                button_url=button_url,
                footer_text=footer_text,
                use_queue=use_queue
            )
            
        except Exception as e:
            print(f"❌ Error procesando notificación broadcast: {e}")
            return False
    
    def health_check(self) -> bool:
        """Verificar estado del servicio WhatsApp"""
        try:
            if not self.config.enabled:
                return False
            
            return self.client.health_check()
            
        except Exception as e:
            self.logger.error(f"Error en health check WhatsApp: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado completo del servicio"""
        try:
            uptime = time.time() - self.stats["start_time"]
            client_status = self.client.get_status()
            
            return {
                "service": {
                    "enabled": self.config.enabled,
                    "uptime_seconds": round(uptime, 2),
                    "individual_messages_sent": self.stats["individual_messages_sent"],
                    "broadcast_messages_sent": self.stats["broadcast_messages_sent"],
                    "total_recipients": self.stats["total_recipients"],
                    "errors": self.stats["errors"],
                    "success_rate": self._calculate_success_rate()
                },
                "client": client_status
            }
            
        except Exception as e:
            return {
                "service": {
                    "enabled": False,
                    "error": str(e)
                },
                "client": {
                    "healthy": False,
                    "error": str(e)
                }
            }
    
    def _calculate_success_rate(self) -> float:
        """Calcular tasa de éxito"""
        total_attempts = (
            self.stats["individual_messages_sent"] + 
            self.stats["broadcast_messages_sent"] + 
            self.stats["errors"]
        )
        
        if total_attempts == 0:
            return 100.0
        
        successful = self.stats["individual_messages_sent"] + self.stats["broadcast_messages_sent"]
        return round((successful / total_attempts) * 100, 2)
    
    def get_simple_status(self) -> Dict[str, Any]:
        """Obtener estado simple del servicio"""
        status = self.get_status()
        return {
            "enabled": status["service"]["enabled"],
            "healthy": status["client"]["healthy"],
            "messages_sent": status["service"]["individual_messages_sent"] + status["service"]["broadcast_messages_sent"],
            "success_rate": status["service"]["success_rate"]
        }
