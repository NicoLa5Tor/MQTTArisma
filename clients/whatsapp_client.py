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
