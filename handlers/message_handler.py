"""
Manejador de mensajes para estructura empresas/nombre_empresa/sede_empresa/tipo_hardware/
"""
import json
import logging
import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
# from config.hardware_manager import HardwareManager  # ELIMINADO


@dataclass
class ProcessedMessage:
    """Estructura para mensajes procesados"""
    empresa: str
    sede: str
    hardware_type: str
    data: Dict[str, Any]
    raw_payload: str
    raw_topic: str
    timestamp: str
    priority: str = "medium"


class MessageHandler:
    """Manejador de mensajes MQTT para estructura empresas/nombre_empresa/sede_empresa/tipo_hardware/"""
    
    def __init__(self, backend_client, websocket_receiver=None):
        self.backend_client = backend_client
        self.websocket_receiver = websocket_receiver
        self.logger = logging.getLogger(__name__)
        
        # Gestor de tipos de hardware - ELIMINADO
        # self.hardware_manager = HardwareManager()
        
        # Token de autenticación
        self.auth_token = None
        
        # Estadísticas
        self.processed_messages = 0
        self.error_count = 0

    def authenticate(self, username: str, password: str) -> bool:
        """Autenticar y obtener token de BOTONERA"""
        auth_data = {
            'username': username,
            'password': password
        }
        response = self.backend_client.post('/api/login', data=auth_data)
        if response and 'token' in response:
            self.auth_token = response['token']
            self.logger.info("Autenticación exitosa. Token obtenido.")
            return True
        self.logger.error("Error en autenticación.")
        return False
        
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
                    
                    print("="*100)
                    print(f"🚨 MENSAJE DE BOTONERA DETECTADO 🚨")
                    print(f"TOPIC: {topic}")
                    print(f"PAYLOAD: {payload}")
                    print(f"HARDWARE DETECTADO: {hardware_name}")
                    
                    # Procesar JSON de BOTONERA (cualquier estructura)
                    try:
                        json_data = json.loads(payload)
                        print(f"DATOS RECIBIDOS DE {hardware_name}:")
                        print(f"Contenido: {json_data}")
                        print(f"🚨 LANZANDO ALARMA PARA {hardware_name} 🚨")
                        print("="*100)
                        
                        self.processed_messages += 1
                        return True
                        
                    except json.JSONDecodeError as e:
                        print(f"ERROR: JSON inválido en mensaje de BOTONERA")
                        print(f"Error: {e}")
                        print(f"Payload: {payload}")
                        self.error_count += 1
                        return False
                    except Exception as e:
                        print(f"ERROR procesando mensaje de BOTONERA: {e}")
                        self.error_count += 1
                        return False
                else:
                    # Ignorar si hay más de 1 parte después de BOTONERA
                    # print(f"IGNORADO - Topic con subtopics después del hardware: {topic}")
                    return True
            else:
                # No hay partes después de BOTONERA, ignorar
                return True
        
        # IGNORAR CUALQUIER TOPIC QUE NO CONTENGA "BOTONERA"
        else:
            # No mostrar ni procesar otros topics
            return True  # Retorna True pero no hace nada


    def _parse_topic(self, topic: str) -> Optional[Tuple[str, str, str, str]]:
        """Parsear topic con estructura empresas/nombre_empresa/sede/tipo_hardware"""
        try:
            # Soportar tanto 3 como 4 partes
            pattern_4 = r'^empresas/([^/]+)/([^/]+)/([^/]+)/([^/]+)/?$'
            pattern_3 = r'^empresas/([^/]+)/([^/]+)/([^/]+)/?$'
            
            match_4 = re.match(pattern_4, topic)
            match_3 = re.match(pattern_3, topic)
            
            if match_4:
                # Formato: empresas/empresa/sede/tipo/nombre_hardware
                empresa = match_4.group(1).strip()
                sede = match_4.group(2).strip()
                tipo_dispositivo = match_4.group(3).strip().upper()
                nombre_hardware = match_4.group(4).strip()
            elif match_3:
                # Formato: empresas/empresa/sede/tipo_hardware
                empresa = match_3.group(1).strip()
                sede = match_3.group(2).strip()
                tipo_dispositivo = match_3.group(3).strip().upper()
                nombre_hardware = "default"
            else:
                self.logger.error(f"Formato de topic inválido: {topic}")
                self.logger.info("Formato esperado: empresas/empresa/sede/tipo_hardware o empresas/empresa/sede/tipo/nombre_hardware")
                return None
            
            if not all([empresa, sede, tipo_dispositivo]):
                self.logger.error(f"Partes del topic vacías: empresa='{empresa}', sede='{sede}', tipo='{tipo_dispositivo}'")
                return None
            
            self.logger.debug(f"Topic parseado: empresa={empresa}, sede={sede}, tipo={tipo_dispositivo}, hardware={nombre_hardware}")
            return (empresa, sede, tipo_dispositivo, nombre_hardware)
            
        except Exception as e:
            self.logger.error(f"Error parseando topic {topic}: {e}")
            return None

    def _process_hardware_message(self, empresa: str, sede: str, hardware_type: str, topic: str, payload: str, json_data: Optional[Dict] = None) -> bool:
        """Procesar mensaje de hardware"""
        try:
            if json_data is None:
                try:
                    json_data = json.loads(payload)
                except json.JSONDecodeError:
                    self.logger.error(f"Error parseando JSON: {payload}")
                    return False
            
            # hardware_info = self.hardware_manager.get_hardware_type(hardware_type)
            # priority = hardware_info.priority if hardware_info else "medium"
            priority = "high"  # Prioridad fija para BOTONERA
            
            # Crear mensaje procesado
            processed_msg = ProcessedMessage(
                empresa=empresa,
                sede=sede,
                hardware_type=hardware_type,
                data=json_data,
                raw_payload=payload,
                raw_topic=topic,
                timestamp=self._get_current_timestamp(),
                priority=priority
            )
            
            return self._send_to_backend(processed_msg)
            
        except Exception as e:
            self.logger.error(f"Error procesando {hardware_type}: {e}")
            self.error_count += 1
            return False

    def _send_to_backend(self, msg: ProcessedMessage) -> bool:
        """Enviar mensaje al backend"""
        try:
            mqtt_data = {
                "empresa": msg.empresa,
                "sede": msg.sede,
                "hardware_type": msg.hardware_type,
                "data": msg.data,
                "topic": msg.raw_topic,
                "timestamp": msg.timestamp,
                "priority": msg.priority
            }
            
            self.logger.info("🚀 ENVIANDO DATOS AL BACKEND:")
            self.logger.info(f"   🏢 Empresa: {msg.empresa}")
            self.logger.info(f"   🏗️  Sede: {msg.sede}")
            self.logger.info(f"   🔧 Hardware: {msg.hardware_type}")
            self.logger.info(f"   📊 Datos: {json.dumps(mqtt_data, indent=2)}")
            
            response = self.backend_client.send_mqtt_data(mqtt_data)
            
            if response:
                self.logger.info(f"Datos de {msg.hardware_type} procesados exitosamente")
                
                # Enviar por WebSocket si está configurado
                if self.websocket_receiver and hasattr(self.websocket_receiver, 'send'):
                    websocket_data = {
                        "type": "hardware_alert",
                        "empresa": msg.empresa,
                        "sede": msg.sede,
                        "hardware_type": msg.hardware_type,
                        "priority": msg.priority,
                        "timestamp": msg.timestamp,
                        "data": msg.data
                    }
                    self.websocket_receiver.send(json.dumps(websocket_data))
                
                return True
            else:
                self.logger.error(f"Error enviando datos de {msg.hardware_type} al backend")
                return False
                
        except Exception as e:
            self.logger.error(f"Error enviando mensaje al backend: {e}")
            return False

    def _get_current_timestamp(self) -> str:
        """Obtener timestamp actual"""
        from datetime import datetime
        return datetime.now().isoformat()

    # MÉTODOS DE HARDWARE MANAGER - COMENTADOS
    # def reload_hardware_config(self) -> bool:
    #     """Recargar configuración de hardware"""
    #     self.logger.info("Recargando configuración de tipos de hardware...")
    #     return self.hardware_manager.reload_config()

    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del manejador"""
        return {
            "processed_messages": self.processed_messages,
            "error_count": self.error_count,
            "error_rate": round(self.error_count / max(self.processed_messages, 1) * 100, 2),
            "hardware_types_count": 1  # Solo BOTONERA
        }

    # def add_hardware_type(self, hardware_type: str, config: Dict[str, Any]) -> bool:
    #     """Agregar nuevo tipo de hardware"""
    #     self.logger.info(f"Agregando nuevo tipo de hardware: {hardware_type}")
    #     return self.hardware_manager.add_hardware_type(hardware_type.lower(), config)

    # def get_supported_hardware_types(self) -> list:
    #     """Obtener lista de tipos de hardware soportados"""
    #     return self.hardware_manager.get_supported_types()

    # def validate_hardware_type(self, hardware_type: str) -> bool:
    #     """Validar si un tipo de hardware es soportado"""
    #     return self.hardware_manager.is_hardware_type_supported(hardware_type)
