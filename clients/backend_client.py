"""
Cliente para comunicación con el backend
"""
import json
import logging
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config.settings import BackendConfig


class BackendClient:
    """Cliente para comunicación con el backend"""
    
    def __init__(self, config: BackendConfig):
        
        self.config = config
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
        # Configurar reintentos automáticos
        retry_strategy = Retry(
            total=config.retry_attempts,
            backoff_factor=config.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Configurar headers por defecto
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'MQTT-Backend-Client/1.0'
        })
        
        # Configurar API Key si está disponible
        if config.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {config.api_key}'
            })
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     params: Optional[Dict] = None) -> Optional[Dict]:
        """Realizar petición HTTP con manejo de errores"""
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.config.timeout
            )
            
            # Manejar códigos de estado específicos sin lanzar excepción
            if response.status_code == 404:
                self.logger.info(f"🔍 Recurso no encontrado (404): {method} {url}")
                try:
                    result = response.json()
                    result['_status_code'] = 404
                    return result
                except json.JSONDecodeError:
                    return {'_status_code': 404, 'raw_response': response.text, 'message': 'Recurso no encontrado'}
            
            elif response.status_code == 401:
                self.logger.info(f"🔒 No autorizado (401): {method} {url}")
                try:
                    result = response.json()
                    result['_status_code'] = 401
                    return result
                except json.JSONDecodeError:
                    return {'_status_code': 401, 'raw_response': response.text, 'message': 'No autorizado'}
            
            # Para otros códigos de error (500, 502, 503, etc.), usar raise_for_status
            # que activará los reintentos automáticos configurados
            elif response.status_code >= 500:
                response.raise_for_status()  # Esto lanzará excepción y activará reintentos
            
            # Para códigos de éxito (2xx) y otros códigos (3xx, 4xx excepto 401/404)
            # intentar parsear JSON normalmente
            try:
                result = response.json()
                result['_status_code'] = response.status_code
                return result
            except json.JSONDecodeError:
                return {'_status_code': response.status_code, 'raw_response': response.text}
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ ERROR HTTP {method} {url}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Código: {e.response.status_code}, Respuesta: {e.response.text}")
            return None
   
    def get(self,endpoint:str,data:Optional[Dict]= None) -> Optional[Dict]:
        """Realizar petición GET"""
        return self._make_request('GET',endpoint,params=data)
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Realizar petición POST"""
        return self._make_request('POST', endpoint, data=data)
    def verify_user_number(self,number) -> Optional[Dict]:
        try:
            endpoint = "/api/phone-lookup"
            data = {
                "telefono":number
            }
            response = self.get(data=data,endpoint=endpoint)
            print(f"response del verify {response}")
            
            # Si no hay respuesta (error de conexión), return None
            if response is None:
                print("❌ Sin respuesta del servidor")
                return None
            
            # Manejar códigos de estado específicos
            status_code = response.get('_status_code', 200)
            
            if status_code == 404:
                print("🔍 Usuario no encontrado (404) - respuesta válida")
                return response  # Devolver la respuesta para que se pueda manejar en el código que llama
            
            elif status_code == 401:
                print("🔒 No autorizado (401) - respuesta válida")
                return response  # Devolver la respuesta para que se pueda manejar en el código que llama
            
            # Para códigos de éxito, verificar el campo 'success'
            validate_response = response.get('success', False)
            if validate_response:
                print("✅ Verificación exitosa")
                return response
            else:
                print(f"❌ Verificación falló: {response.get('message', 'Error desconocido')}")
                return response  # Devolver la respuesta completa, no None
        
        except Exception as ex:
            self.logger.error(f"Error al tratar de verificar el numero: {ex}")
            return None
    def authenticate_hardware(self, mqtt_data: Dict[str, Any]) -> Optional[str]:
        """Autenticar hardware y obtener token"""
        try:
            # Extraer credenciales del mensaje MQTT
            auth_data = {
                'empresa': mqtt_data.get('empresa'), 
                'sede': mqtt_data.get('sede'),
                'hardware': mqtt_data.get('nombre_hardware'),
                'tipo_hardware': mqtt_data.get('tipo_hardware')
            }
            print(f"🔐 Autenticando: {auth_data['hardware']} ({auth_data['empresa']}/{auth_data['sede']})")
            
            response = self.post('/api/hardware-auth/authenticate', data=auth_data)
            
            # Si no hay respuesta (error de conexión), return None
            if response is None:
                print("❌ Sin respuesta del servidor")
                return None
            
            # Manejar códigos de estado específicos
            status_code = response.get('_status_code', 200)
            
            if status_code == 404:
                print("🔍 Hardware no encontrado (404) - credenciales inválidas")
                return None
            
            elif status_code == 401:
                print("🔒 No autorizado (401) - credenciales inválidas")
                return None
            
            # Para respuestas exitosas, verificar el token
            if response and response.get('success'):
                # Obtener token de la respuesta
                if 'token' in response:
                    token = response['token']
                    print(f"✅ Token obtenido exitosamente")
                    return token
                else:
                    print(f"❌ No se encontró token en respuesta")
                    return None
            else:
                error_msg = response.get('message', 'Error desconocido') if response else 'Sin respuesta'
                print(f"❌ Autenticación fallida: {error_msg}")
                return None
                
        except Exception as e:
            print(f"💥 Error autenticación: {e}")
            return None
    
    def send_alarm_data(self, mqtt_data: Dict[str, Any], token: str) -> Optional[Dict]:
        """Enviar datos de alarma al backend usando token"""
        try:
            # Establecer token en headers
            self.session.headers.update({
                'Authorization': f'Bearer {token}'
            })
            
            # Endpoint para enviar datos de alarma
            endpoint = '/api/mqtt-alerts'
            
            print(f"🚨 Enviando alarma: {mqtt_data['nombre_hardware']}")
            
            # Enviar datos (esto consumirá el token)
            response = self.post(endpoint, data=mqtt_data)
            
            # Limpiar token después de usar
            self._clear_token()
            
            if response:
                alert_id = response.get('alert_id', 'N/A')
                print(f"✅ Alarma creada: ID {alert_id}")
                return response
            else:
                print(f"❌ Sin respuesta del backend")
                return None
                
        except Exception as e:
            print(f"💥 Error enviando alarma: {e}")
            self._clear_token()
            return None
    
    def health_check(self) -> bool:
        """Verificar que el backend esté disponible"""
        try:
            response = self.session.get(f'{self.config.base_url}/api/mqtt-alerts/test-flow')
            if response.status_code == 200:
                return True
            else:
                self.logger.error(f"Health check falló con status: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Error en health check: {e}")
            return False
    
    def create_user_alert(self, usuario_id: str, tipo_alerta: str, descripcion: str, prioridad: str = "media") -> Optional[Dict]:
        """
        Crear una alerta de usuario y obtener topics e ID de alerta
        
        Args:
            usuario_id: ID del usuario (obligatorio)
            tipo_alerta: Tipo de alerta (obligatorio)
            descripcion: Descripción de la alerta (obligatorio)
            prioridad: Prioridad de la alerta (opcional, por defecto 'media')
            
        Returns:
            Dict con la respuesta del backend incluyendo topics e ID de alerta
        """
        try:
            endpoint = '/api/mqtt-alerts/user-alert'
            
            data = {
                "usuario_id": usuario_id,
                "tipo_alerta": tipo_alerta,
                "descripcion": descripcion,
                "prioridad": prioridad
            }
            
            print(f"🚨 Creando alerta de usuario:")
            print(f"   🆔 Usuario ID: {usuario_id}")
            print(f"   🔔 Tipo: {tipo_alerta}")
            print(f"   📝 Descripción: {descripcion}")
            print(f"   ⚡ Prioridad: {prioridad}")
            
            response = self.post(endpoint, data=data)
            
            if response and response.get('success'):
                alert_id = response.get('alert_id', 'N/A')
                topics = response.get('topics_otros_hardware', [])
                
                print(f"✅ Alerta creada exitosamente:")
                print(f"   🆔 ID de alerta: {alert_id}")
                print(f"   📡 Topics generados: {len(topics)} topics")
                
                return response
            else:
                error_msg = response.get('message', 'Error desconocido') if response else 'Sin respuesta'
                print(f"❌ Error creando alerta: {error_msg}")
                return None
                
        except Exception as e:
            print(f"💥 Error creando alerta de usuario: {e}")
            return None
    
    def deactivate_user_alert(self, alert_id: str, desactivado_por_id: str, desactivado_por_tipo: str = "usuario") -> Optional[Dict]:
        """
        Desactivar/apagar una alerta de usuario
        
        Args:
            alert_id: ID de la alerta a desactivar (obligatorio)
            desactivado_por_id: ID del usuario que desactiva la alerta (obligatorio)
            desactivado_por_tipo: Tipo de quien desactiva la alerta (opcional, por defecto 'usuario')
            
        Returns:
            Dict con la respuesta del backend
        """
        try:
            endpoint = '/api/mqtt-alerts/user-alert/deactivate'
            
            data = {
                "alert_id": alert_id,
                "desactivado_por_id": desactivado_por_id,
                "desactivado_por_tipo": desactivado_por_tipo
            }
            
            print(f"🔄 Desactivando alerta de usuario:")
            print(f"   🆔 Alert ID: {alert_id}")
            print(f"   👤 Desactivado por ID: {desactivado_por_id}")
            print(f"   🏷️ Tipo: {desactivado_por_tipo}")
            
            response = self.put(endpoint, data=data)
            
            if response and response.get('success'):
                print(f"✅ Alerta desactivada exitosamente:")
                print(f"   🆔 ID de alerta: {alert_id}")
                print(f"   👤 Desactivado por: {desactivado_por_id}")
                print(f"   🏷️ Tipo: {desactivado_por_tipo}")
                
                # Mostrar información adicional si está disponible
                if 'message' in response:
                    print(f"   📝 Mensaje: {response['message']}")
                
                return response
            else:
                error_msg = response.get('message', 'Error desconocido') if response else 'Sin respuesta'
                print(f"❌ Error desactivando alerta: {error_msg}")
                return None
                
        except Exception as e:
            print(f"💥 Error desactivando alerta de usuario: {e}")
            return None
    
    def put(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Realizar petición PUT"""
        return self._make_request('PUT', endpoint, data=data)
    
    def _clear_token(self):
        """Limpiar el token de los headers después de usarlo"""
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
