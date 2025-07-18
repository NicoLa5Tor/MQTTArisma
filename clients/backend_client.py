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
            
            response.raise_for_status()
            
            # Intentar parsear JSON
            try:
                result = response.json()
                return result
            except json.JSONDecodeError:
                return {'raw_response': response.text}
                
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
           # print(f"el numero es {data}")
            response = self.get(data=data,endpoint=endpoint)
            #print(response)
            if response.get('success') is True:
                print("response bien")
                # import time
                # time.sleep(10000)
                return response
            else:
                self.logger.error(f"Error al verificar numero, el response dio {response}")
                return None
        except Exception as ex:
            self.logger.error(f"Error al tratar de verificar el numero: {ex}")
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
                print(f"❌ Autenticación fallidA: {error_msg}")
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
    
    def _clear_token(self):
        """Limpiar el token de los headers después de usarlo"""
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']