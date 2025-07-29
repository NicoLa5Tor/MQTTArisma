"""
Cliente para comunicación con la API de WhatsApp
"""
import json
import logging
from typing import Dict, Any, Optional, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class WhatsAppClient:
    """Cliente para comunicación con la API de WhatsApp"""
    
    def __init__(self, config):
        self.config = config
        self.base_url = config.api_url.rstrip('/')
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
        # Configurar reintentos automáticos
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Configurar headers por defecto
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'MQTT-WhatsApp-Client/1.0'
        })
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     params: Optional[Dict] = None) -> Optional[Dict]:
        """Realizar petición HTTP con manejo de errores"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            print(f"📱 WhatsApp API Response: {response.status_code}")
            
            # Intentar parsear JSON
            try:
                return response.json()
            except json.JSONDecodeError:
                return {'raw_response': response.text}
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ ERROR EN PETICIÓN WHATSAPP:")
            self.logger.error(f"   🔗 URL: {url}")
            self.logger.error(f"   📝 Método: {method}")
            self.logger.error(f"   ⚠️  Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"   📊 Código HTTP: {e.response.status_code}")
                self.logger.error(f"   📄 Texto respuesta: {e.response.text}")
            return None
    
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Realizar petición POST"""
        return self._make_request('POST', endpoint, data=data)
    def send_location_request(self, phone:str,body_text:str) -> Optional[Dict]:
        """
        Enviar peticion de ubicacion al usuario en especifico.
        Este servicio no usa cola
        """
        try:
            phone_clean= self._clean_phone_number(phone)
            data = {
                "phone": phone_clean,
                "body_text" : body_text
            }
            response = self.post(endpoint='/api/send-location-request',data=data)
            if response:
                print(f"✅ Mensaje individual de peticion de ubicacion enviado exitosamente")
                return response
            else:
                print(f"❌ Error enviando mensaje  de peticion de ubicacion individual")
                return None
        except Exception as e:
            print(f"💥 Error enviando mensaje de peticion de ubicaciion individual: {e}")
            self.logger.error(f"Error enviando mensaje de peticion de ubicaciion individual: {e}")
            return None
    def send_individual_message(self, phone: str, message: str, use_queue: bool = False) -> Optional[Dict]:
        """
        Enviar mensaje individual de WhatsApp
        
        Args:
            phone: Número del destinatario (formato internacional, sin + ni espacios)
            message: Texto del mensaje
            use_queue: Si usar cola o no (opcional, default False)
            
        Returns:
            Dict con respuesta de la API o None si hay error
        """
        try:
            # Validar formato del número
            phone_clean = self._clean_phone_number(phone)
            
            data = {
                "phone": phone_clean,
                "message": message,
                "use_queue": use_queue
            }
            
            print(f"📱 Enviando mensaje individual:")
            print(f"   📞 Teléfono: {phone_clean}")
            print(f"   💬 Mensaje: {message[:50]}{'...' if len(message) > 50 else ''}")
            print(f"   🔄 Cola: {use_queue}")
            
            response = self.post('/api/send-message', data=data)
            
            if response:
                print(f"✅ Mensaje individual enviado exitosamente")
                return response
            else:
                print(f"❌ Error enviando mensaje individual")
                return None
                
        except Exception as e:
            print(f"💥 Error enviando mensaje individual: {e}")
            self.logger.error(f"Error enviando mensaje individual: {e}")
            return None
    
    def send_bulk_individual(self, recipients: List[Dict], use_queue: bool = True) -> Optional[Dict]:
        """
        Enviar mensajes individuales masivos usando el endpoint send-bulk
        
        Args:
            recipients: Lista de diccionarios con 'phone' y 'message'
            use_queue: Si usar cola o no (opcional, por defecto True)
            
        Returns:
            Dict con la respuesta de la API o None si hay error
        """
        try:
            data = {
                "recipients": recipients,
                "use_queue": use_queue
            }
            
            print(f"📱 Enviando mensajes individuales masivos:")
            print(f"   📞 Destinatarios: {len(recipients)}")
            print(f"   🔄 Usar cola: {use_queue}")
            
            response = self.post('/api/send-bulk', data=data)
            
            if response:
                sent_count = response.get('sent_count', len(recipients))
                print(f"✅ Mensajes masivos enviados exitosamente:")
                print(f"   📤 Enviados: {sent_count}/{len(recipients)}")
                return response
            else:
                print(f"❌ Error enviando mensajes masivos")
                return None
                
        except Exception as e:
            print(f"💥 Error enviando mensajes masivos: {e}")
            self.logger.error(f"Error enviando mensajes masivos: {e}")
            return None
    
    def send_broadcast_message(self, phones: List[str], header_type: str, header_content: str, 
                             body_text: str, button_text: str, button_url: str, 
                             footer_text: str, use_queue: bool = True) -> Optional[Dict]:
        """
        Enviar mensaje broadcast interactivo de WhatsApp
        
        Args:
            phones: Lista de números destinatarios (formato internacional, sin + ni espacios)
            header_type: Tipo de encabezado, generalmente "text"
            header_content: Texto del encabezado
            body_text: Texto principal del mensaje
            button_text: Texto del botón de acción
            button_url: URL del botón
            footer_text: Texto de pie de página
            use_queue: Si usar cola o no (opcional, default True)
            
        Returns:
            Dict con respuesta de la API o None si hay error
        """
        try:
            # Limpiar números de teléfono
            phones_clean = [self._clean_phone_number(phone) for phone in phones]
            
            data = {
                "phones": phones_clean,
                "header_type": header_type,
                "header_content": header_content,
                "body_text": body_text,
                "button_text": button_text,
                "button_url": button_url,
                "footer_text": footer_text,
                "use_queue": use_queue
            }
            
            print(f"📱 Enviando broadcast interactivo:")
            print(f"   📞 Teléfonos: {len(phones_clean)} números")
            print(f"   📋 Encabezado: {header_content}")
            print(f"   💬 Cuerpo: {body_text[:50]}{'...' if len(body_text) > 50 else ''}")
            print(f"   🔘 Botón: {button_text}")
            print(f"   🔗 URL: {button_url}")
            print(f"   📝 Pie: {footer_text}")
            print(f"   🔄 Cola: {use_queue}")
            
            response = self.post('/api/send-broadcast-interactive', data=data)
            
            if response:
                print(f"✅ Broadcast enviado exitosamente a {len(phones_clean)} números")
                return response
            else:
                print(f"❌ Error enviando broadcast")
                return None
                
        except Exception as e:
            print(f"💥 Error enviando broadcast: {e}")
            self.logger.error(f"Error enviando broadcast: {e}")
            return None
    
    def send_personalized_broadcast(self, recipients: List[Dict], header_type: str, header_content: str, 
                                   button_text: str, button_url: str, footer_text: str, use_queue: bool = True) -> Optional[Dict]:
        """
        Enviar un broadcast personalizado usando el API de WhatsApp
        
        Args:
            recipients: Lista de diccionarios con 'phone' y 'body_text'
            header_type: Tipo de encabezado, e.g., 'text', 'image'
            header_content: Contenido del encabezado, URL o texto
            button_text: Texto del botón
            button_url: URL del botón
            footer_text: Texto del pie de página
            use_queue: Si usar cola o no (default True)
            
        Returns:
            Dict con respuesta de la API o None si hay error
        """
        try:
            data = {
                "recipients": recipients,
                "header_type": header_type,
                "header_content": header_content,
                "button_text": button_text,
                "button_url": button_url,
                "footer_text": footer_text,
                "use_queue": use_queue
            }
            
            print(f"📱 Enviando broadcast personalizado:")
            print(f"   📋 Recipients: {len(recipients)}")
            print(f"   📋 Encabezado: {header_content}")
            print(f"   🔘 Botón: {button_text}")
            print(f"   🔗 URL: {button_url}")
            print(f"   📝 Pie: {footer_text}")
            print(f"   🔄 Cola: {use_queue}")
            
            response = self.post('/api/send-personalized-broadcast', data=data)
            
            if response:
                print(f"✅ Broadcast personalizado enviado exitosamente")
                return response
            else:
                print(f"❌ Error enviando broadcast personalizado")
                return None
                
        except Exception as e:
            print(f"💥 Error enviando broadcast personalizado: {e}")
            self.logger.error(f"Error enviando broadcast personalizado: {e}")
            return None
    
    def send_list_message(self, phone: str, header_text: str, body_text: str, 
                         footer_text: str, button_text: str, sections: List[Dict]) -> Optional[Dict]:
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
            Dict con respuesta de la API o None si hay error
        """
        try:
            # Validar formato del número
            phone_clean = self._clean_phone_number(phone)
            
            data = {
                "phone": phone_clean,
                "header_text": header_text,
                "body_text": body_text,
                "footer_text": footer_text,
                "button_text": button_text,
                "sections": sections
            }
            
            print(f"📱 Enviando mensaje de lista:")
            print(f"   📞 Teléfono: {phone_clean}")
            print(f"   📋 Encabezado: {header_text[:50]}{'...' if len(header_text) > 50 else ''}")
            print(f"   💬 Cuerpo: {body_text[:50]}{'...' if len(body_text) > 50 else ''}")
            print(f"   📝 Pie: {footer_text[:30]}{'...' if len(footer_text) > 30 else ''}")
            print(f"   🔘 Botón: {button_text[:30]}{'...' if len(button_text) > 30 else ''}")
            print(f"   📋 Secciones: {len(sections)} secciones")
            
            response = self.post('/api/send-list', data=data)
            
            if response:
                print(f"✅ Mensaje de lista enviado exitosamente")
                return response
            else:
                print(f"❌ Error enviando mensaje de lista")
                return None
                
        except Exception as e:
            print(f"💥 Error enviando mensaje de lista: {type(e).__name__}")
            self.logger.error(f"Error enviando mensaje de lista: {str(e)[:200]}")
            return None
    def send_bulk_list_message(self, header_text: str, footer_text: str, button_text: str, 
                              sections: List[Dict], recipients: List[Dict], use_queue: bool = True) -> Optional[Dict]:
        """
        Enviar mensaje de lista de manera masiva a múltiples destinatarios con contenido personalizado
        
        Args:
            header_text: Texto del encabezado (común para todos)
            footer_text: Texto de pie de página (común para todos)
            button_text: Texto del botón (común para todos)
            sections: Lista de secciones con sus opciones (común para todos)
            recipients: Lista de diccionarios con 'phone' y 'body_text' personalizado
            use_queue: Si usar cola o no (default True)
            
        Returns:
            Dict con respuesta de la API o None si hay error
        """
        try:
            # Limpiar números de teléfono en recipients
            recipients_clean = []
            for recipient in recipients:
                phone_clean = self._clean_phone_number(recipient["phone"])
                recipients_clean.append({
                    "phone": phone_clean,
                    "body_text": recipient["body_text"]
                })
            
            data = {
                "header_text": header_text,
                "footer_text": footer_text,
                "button_text": button_text,
                "sections": sections,
                "recipients": recipients_clean,
                "use_queue": use_queue
            }
            
            print(f"📱 Enviando bulk list message:")
            print(f"   📋 Encabezado: {header_text[:50]}{'...' if len(header_text) > 50 else ''}")
            print(f"   📝 Pie: {footer_text[:30]}{'...' if len(footer_text) > 30 else ''}")
            print(f"   🔘 Botón: {button_text[:30]}{'...' if len(button_text) > 30 else ''}")
            print(f"   📋 Secciones: {len(sections)} secciones")
            print(f"   📞 Destinatarios: {len(recipients_clean)} números")
            print(f"   🔄 Cola: {use_queue}")
            
            response = self.post('/api/send-bulk-list', data=data)
            
            if response:
                print(f"✅ Bulk list message enviado exitosamente a {len(recipients_clean)} números")
                return response
            else:
                print(f"❌ Error enviando bulk list message")
                return None
                
        except Exception as e:
            print(f"💥 Error enviando bulk list message: {type(e).__name__}")
            self.logger.error(f"Error enviando bulk list message: {str(e)[:200]}")
            return None
    
    def send_bulk_button_message(self, header_type: str, header_content: str, buttons: List[Dict], 
                                footer_text: str, recipients: List[Dict], use_queue: bool = True) -> Optional[Dict]:
        """
        Enviar mensaje con botones de manera masiva a múltiples destinatarios con contenido personalizado
        
        Args:
            header_type: Tipo de encabezado (e.g., 'text')
            header_content: Contenido del encabezado (común para todos)
            buttons: Lista de botones con 'id' y 'title' (común para todos)
            footer_text: Texto de pie de página (común para todos)
            recipients: Lista de diccionarios con 'phone' y 'body_text' personalizado
            use_queue: Si usar cola o no (default True)
            
        Returns:
            Dict con respuesta de la API o None si hay error
        """
        try:
            # Limpiar números de teléfono en recipients
            recipients_clean = []
            for recipient in recipients:
                phone_clean = self._clean_phone_number(recipient["phone"])
                recipients_clean.append({
                    "phone": phone_clean,
                    "body_text": recipient["body_text"]
                })
            
            data = {
                "header_type": header_type,
                "header_content": header_content,
                "buttons": buttons,
                "footer_text": footer_text,
                "recipients": recipients_clean,
                "use_queue": use_queue
            }
            
            print(f"📱 Enviando bulk button message:")
            print(f"   📋 Encabezado tipo: {header_type}")
            print(f"   📋 Encabezado: {header_content}")
            print(f"   📝 Pie: {footer_text}")
            print(f"   🔘 Botones: {len(buttons)} botones")
            print(f"   📞 Destinatarios: {len(recipients_clean)} números")
            print(f"   🔄 Cola: {use_queue}")
            
            response = self.post('/api/send-bulk-button', data=data)
            
            if response:
                print(f"✅ Bulk button message enviado exitosamente a {len(recipients_clean)} números")
                return response
            else:
                print(f"❌ Error enviando bulk button message")
                return None
                
        except Exception as e:
            print(f"💥 Error enviando bulk button message: {type(e).__name__}")
            self.logger.error(f"Error enviando bulk button message: {str(e)[:200]}")
            return None
    
    def add_number_to_cache(self, phone: str, name: str = None, data: Dict = None) -> Optional[Dict]:
        """
        Agregar número al cache de WhatsApp
        
        Args:
            phone: Número de teléfono (formato internacional)
            name: Nombre del contacto
            data: Datos adicionales del contacto
            
        Returns:
            Dict con respuesta de la API o None si hay error
        """
        try:
            # Validar formato del número
            phone_clean = self._clean_phone_number(phone)
            
            payload = {
                "phone": phone_clean,
                "name": name,
                "data": data or {}
            }
            
            print(f"📞 Agregando número al cache:")
            print(f"   📞 Teléfono: {phone_clean}")
            print(f"   👤 Nombre: {name or 'N/A'}")
            print(f"   📋 Datos: {len(str(data or {})) if data else 0} caracteres")
            
            response = self.post('/api/numbers', data=payload)
            
            if response:
                print(f"✅ Número agregado al cache exitosamente")
                return response
            else:
                print(f"❌ Error agregando número al cache")
                return None
                
        except Exception as e:
            print(f"💥 Error agregando número al cache: {type(e).__name__}")
            self.logger.error(f"Error agregando número al cache: {str(e)[:200]}")
            return None
    
    def update_number_cache(self, phone: str, data: Dict) -> Optional[Dict]:
        """
        Actualizar información del cache de un usuario de WhatsApp
        
        Args:
            phone: Número de teléfono (formato internacional)
            data: Datos a actualizar en el cache (ej: {"email": "nuevo@email.com", "company": "Nueva Empresa"})
            
        Returns:
            Dict con respuesta de la API o None si hay error
        """
        try:
            # Validar formato del número
            phone_clean = self._clean_phone_number(phone)
            
            payload = {
                "phone": phone_clean,
                "data": data
            }
            
            print(f"🔄 Actualizando información del cache:")
            print(f"   📞 Teléfono: {phone_clean}")
            print(f"   📋 Datos a actualizar: {data}")
            
            response = self._make_request('PATCH', '/api/numbers/update', data=payload)
            
            if response:
                print(f"✅ Información del cache actualizada exitosamente")
                return response
            else:
                print(f"❌ Error actualizando información del cache")
                return None
                
        except Exception as e:
            print(f"💥 Error actualizando información del cache: {type(e).__name__}")
            self.logger.error(f"Error actualizando información del cache: {str(e)[:200]}")
            return None
    
    def _clean_phone_number(self, phone: str) -> str:
        """
        Limpiar número de teléfono (remover +, espacios, guiones)
        
        Args:
            phone: Número de teléfono en cualquier formato
            
        Returns:
            Número limpio en formato internacional
        """
        # Remover caracteres no numéricos excepto +
        cleaned = ''.join(char for char in phone if char.isdigit() or char == '+')
        
        # Remover + del inicio si existe
        if cleaned.startswith('+'):
            cleaned = cleaned[1:]
        
        # Validar que sea un número válido
        if not cleaned.isdigit():
            raise ValueError(f"Número de teléfono inválido: {phone}")
        
        # Asegurar que tenga al menos 10 dígitos
        if len(cleaned) < 10:
            raise ValueError(f"Número de teléfono muy corto: {phone}")
        
        return cleaned
    
    def health_check(self) -> bool:
        """Verificar que la API de WhatsApp esté disponible"""
        try:
            response = self.session.get(f'{self.base_url}/health', timeout=10)
            if response.status_code == 200:
                print("✅ API de WhatsApp disponible")
                return True
            else:
                print(f"❌ API de WhatsApp no disponible: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error verificando API de WhatsApp: {e}")
            self.logger.error(f"Error en health check WhatsApp: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del cliente WhatsApp"""
        try:
            health = self.health_check()
            return {
                "api_url": self.base_url,
                "healthy": health,
                "client_name": "WhatsApp-Client"
            }
        except Exception as e:
            return {
                "api_url": self.base_url,
                "healthy": False,
                "error": str(e),
                "client_name": "WhatsApp-Client"
            }
