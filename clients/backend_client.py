"""
Cliente para comunicación con el backend
"""
import json
import logging
import time
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
                return response.json()
            except json.JSONDecodeError:
                return {'raw_response': response.text}
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ ERROR EN PETICIÓN HTTP:")
            self.logger.error(f"   🔗 URL: {url}")
            self.logger.error(f"   📝 Método: {method}")
            self.logger.error(f"   ⚠️  Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"   📊 Código HTTP: {e.response.status_code}")
                self.logger.error(f"   📄 Texto respuesta: {e.response.text}")
            return None
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Realizar petición GET"""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Realizar petición POST"""
        return self._make_request('POST', endpoint, data=data)
    
    def put(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Realizar petición PUT"""
        return self._make_request('PUT', endpoint, data=data)
    
    def delete(self, endpoint: str) -> Optional[Dict]:
        """Realizar petición DELETE"""
        return self._make_request('DELETE', endpoint)
    
    # Métodos específicos para la aplicación
    def send_mqtt_data(self, mqtt_data: Dict[str, Any]) -> Optional[Dict]:
        """Enviar datos MQTT al backend para procesamiento"""
        endpoint = '/api/mqtt-alerts/process'
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        self.logger.info(f"🌐 PETICIÓN HTTP AL BACKEND:")
        self.logger.info(f"   📡 URL: {url}")
        self.logger.info(f"   📤 Método: POST")
        self.logger.info(f"   📋 Datos: {json.dumps(mqtt_data, indent=2)}")
        
        # Primero intentar sin autenticación
        response = self.post(endpoint, data=mqtt_data)
        
        # Si falla por autenticación, intentar login automático
        if not response:
            self.logger.warning("🔐 Intentando autenticación automática...")
            auth_success = self.auto_authenticate()
            if auth_success:
                self.logger.info("✅ Autenticación exitosa, reintentando envío...")
                response = self.post(endpoint, data=mqtt_data)
        
        if response:
            self.logger.info(f"✅ RESPUESTA EXITOSA DEL BACKEND:")
            self.logger.info(f"   📥 Respuesta: {json.dumps(response, indent=2)}")
            return response
        else:
            self.logger.error("❌ ERROR: No se recibió respuesta del backend")
            return None
    
    def verify_hardware(self, hardware_nombre: str) -> Optional[Dict]:
        """Verificar si el hardware existe en el backend"""
        self.logger.info(f"Verificando hardware: {hardware_nombre}")
        
        params = {'hardware_nombre': hardware_nombre}
        response = self.get('/api/mqtt-alerts/verify-hardware', params=params)
        
        if response:
            self.logger.info(f"Hardware verificado: {response.get('verification_info', {})}")
            return response
        else:
            self.logger.error(f"Error verificando hardware: {hardware_nombre}")
            return None
    
    def verify_empresa_sede(self, empresa_nombre: str, sede: str) -> Optional[Dict]:
        """Verificar si la empresa y sede existen"""
        self.logger.info(f"Verificando empresa: {empresa_nombre}, sede: {sede}")
        
        params = {'empresa_nombre': empresa_nombre, 'sede': sede}
        response = self.get('/api/mqtt-alerts/verify-empresa-sede', params=params)
        
        if response:
            self.logger.info(f"Empresa y sede verificadas: {response.get('success', False)}")
            return response
        else:
            self.logger.error(f"Error verificando empresa {empresa_nombre} y sede {sede}")
            return None
    
    def get_all_alerts(self, page: int = 1, limit: int = 50) -> Optional[Dict]:
        """Obtener todas las alertas del backend"""
        self.logger.info(f"Obteniendo alertas - página {page}, límite {limit}")
        
        params = {'page': page, 'limit': limit}
        response = self.get('/api/mqtt-alerts', params=params)
        
        if response:
            self.logger.info(f"Alertas obtenidas: {response.get('total', 0)} total")
            return response
        else:
            self.logger.error("Error obteniendo alertas")
            return None
    
    def get_alert_by_id(self, alert_id: str) -> Optional[Dict]:
        """Obtener alerta específica por ID"""
        self.logger.info(f"Obteniendo alerta ID: {alert_id}")
        
        response = self.get(f'/api/mqtt-alerts/{alert_id}')
        
        if response:
            self.logger.info(f"Alerta obtenida: {alert_id}")
            return response
        else:
            self.logger.error(f"Error obteniendo alerta {alert_id}")
            return None
    
    def test_flow(self) -> Optional[Dict]:
        """Probar el flujo completo del sistema"""
        self.logger.info("Probando flujo completo del sistema")
        
        response = self.get('/api/mqtt-alerts/test-flow')
        
        if response:
            self.logger.info("Flujo probado exitosamente")
            return response
        else:
            self.logger.error("Error probando flujo")
            return None
    
    # Métodos de compatibilidad (legacy)
    def send_semaforo_data(self, semaforo_data: Dict[str, Any]) -> bool:
        """Método legacy - usar send_mqtt_data en su lugar"""
        response = self.send_mqtt_data(semaforo_data)
        return response is not None
    
    def get_semaforo_config(self, semaforo_id: str) -> Optional[Dict]:
        """Obtener configuración de semáforo desde el backend"""
        self.logger.info(f"Obteniendo configuración para semáforo {semaforo_id}")
        
        response = self.get(f'/api/semaforos/{semaforo_id}/config')
        
        if response:
            self.logger.info("Configuración obtenida exitosamente")
            return response
        else:
            self.logger.error(f"Error obteniendo configuración para {semaforo_id}")
            return None
    
    def send_alarm(self, alarm_data: Dict[str, Any]) -> bool:
        """Enviar alarma al backend"""
        self.logger.info(f"Enviando alarma: {alarm_data}")
        
        response = self.post('/api/alarmas', data=alarm_data)
        
        if response:
            self.logger.info("Alarma enviada exitosamente")
            return True
        else:
            self.logger.error("Error enviando alarma")
            return False
    
    def get_system_status(self) -> Optional[Dict]:
        """Obtener estado del sistema"""
        return self.get('/api/mqtt-alerts/verify-empresa-sede')
    
    def auto_authenticate(self) -> bool:
        """Realizar autenticación automática con credenciales por defecto"""
        try:
            # Credenciales por defecto para BOTONERA
            auth_data = {
                'username': 'admin',  # Puedes cambiar esto
                'password': 'admin123'  # Puedes cambiar esto
            }
            
            self.logger.info(f"🔐 Intentando login con usuario: {auth_data['username']}")
            
            response = self.post('/api/login', data=auth_data)
            
            if response and 'token' in response:
                token = response['token']
                # Actualizar headers con el token
                self.session.headers.update({
                    'Authorization': f'Bearer {token}'
                })
                self.logger.info("✅ Token de autenticación obtenido y configurado")
                return True
            else:
                self.logger.error("❌ Error: No se recibió token en la respuesta")
                return False
                
        except Exception as e:
            self.logger.error(f"💥 Error en autenticación automática: {e}")
            return False
    
    def health_check(self) -> bool:
        """Verificar que el backend esté disponible"""
        try:
            response = self.get('/api/mqtt-alerts/test-flow')
            return response is not None and response.get('success', False)
        except Exception as e:
            self.logger.error(f"Error en health check: {e}")
            return False
