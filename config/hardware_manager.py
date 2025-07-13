# """
# Gestor de tipos de hardware para configuración dinámica
# """
# import json
# import logging
# import os
# from typing import Dict, List, Optional, Any
# from dataclasses import dataclass


# @dataclass
# class HardwareType:
#     """Estructura para tipo de hardware"""
#     name: str
#     description: str
#     enabled: bool
#     priority: str
#     alert_types: List[str]


# class HardwareManager:
#     """Gestor de tipos de hardware"""
    
#     def __init__(self, config_file: str = "config/hardware_types.json"):
#         self.config_file = config_file
#         self.logger = logging.getLogger(__name__)
#         self.hardware_types: Dict[str, HardwareType] = {}
#         self.default_settings: Dict[str, Any] = {}
        
#         # Cargar configuración inicial
#         self.load_config()
    
#     def load_config(self) -> bool:
#         """Cargar configuración desde archivo JSON"""
#         try:
#             if not os.path.exists(self.config_file):
#                 self.logger.error(f"Archivo de configuración no encontrado: {self.config_file}")
#                 return False
            
#             with open(self.config_file, 'r', encoding='utf-8') as f:
#                 config_data = json.load(f)
            
#             # Cargar tipos de hardware
#             hardware_types_data = config_data.get('hardware_types', {})
#             self.hardware_types = {}
            
#             for hw_type, hw_config in hardware_types_data.items():
#                 self.hardware_types[hw_type] = HardwareType(
#                     name=hw_config.get('name', hw_type),
#                     description=hw_config.get('description', ''),
#                     enabled=hw_config.get('enabled', True),
#                     priority=hw_config.get('priority', 'medium'),
#                     alert_types=hw_config.get('alert_types', [])
#                 )
            
#             # Cargar configuraciones por defecto
#             self.default_settings = config_data.get('default_settings', {})
            
#             self.logger.info(f"Configuración cargada: {len(self.hardware_types)} tipos de hardware")
#             return True
            
#         except Exception as e:
#             self.logger.error(f"Error cargando configuración: {e}")
#             return False
    
#     def reload_config(self) -> bool:
#         """Recargar configuración desde archivo"""
#         self.logger.info("Recargando configuración de tipos de hardware...")
#         return self.load_config()
    
#     def is_hardware_type_supported(self, hardware_type: str) -> bool:
#         """Verificar si un tipo de hardware está soportado y habilitado"""
#         # # SOLO procesar BOTONERAS - filtrar todo lo demás
#         if hardware_type.upper() == "BOTONERAS":
#             self.logger.info(f"✅ BOTONERA detectada: {hardware_type}")
#             return True
        
#         # Ignorar direcciones IP y otros tipos de hardware
#         if self._is_valid_ip(hardware_type):
#             self.logger.debug(f"🚫 IP ignorada: {hardware_type}")
#             return False
            
#         # Ignorar cualquier otro tipo de hardware
#         self.logger.debug(f"🚫 Hardware ignorado: {hardware_type}")
#         return False
    
#     def get_hardware_type(self, hardware_type: str) -> Optional[HardwareType]:
#         """Obtener información de un tipo de hardware"""
#         # SOLO procesar BOTONERAS
#         if hardware_type.upper() == "BOTONERAS":
#             # Devolver configuración específica para botoneras
#             return HardwareType(
#                 name="Botoneras de Emergencia",
#                 description="Dispositivos de botones de emergencia",
#                 enabled=True,
#                 priority="high",
#                 alert_types=["emergencia", "presionado", "liberado", "falla"]
#             )
        
#         # Para cualquier otro tipo, devolver None
#         return None
    
#     def get_supported_types(self) -> List[str]:
#         """Obtener lista de tipos de hardware soportados"""
#         return [hw_type for hw_type, hw_config in self.hardware_types.items() if hw_config.enabled]
    
#     def get_all_types(self) -> Dict[str, HardwareType]:
#         """Obtener todos los tipos de hardware"""
#         return self.hardware_types.copy()
    
#     def add_hardware_type(self, hardware_type: str, config: Dict[str, Any]) -> bool:
#         """Agregar nuevo tipo de hardware dinámicamente"""
#         try:
#             self.hardware_types[hardware_type.lower()] = HardwareType(
#                 name=config.get('name', hardware_type),
#                 description=config.get('description', ''),
#                 enabled=config.get('enabled', True),
#                 priority=config.get('priority', 'medium'),
#                 alert_types=config.get('alert_types', [])
#             )
            
#             self.logger.info(f"Tipo de hardware agregado: {hardware_type}")
#             return True
            
#         except Exception as e:
#             self.logger.error(f"Error agregando tipo de hardware {hardware_type}: {e}")
#             return False
    
#     def save_config(self) -> bool:
#         """Guardar configuración actual al archivo"""
#         try:
#             config_data = {
#                 "hardware_types": {},
#                 "default_settings": self.default_settings
#             }
            
#             # Convertir tipos de hardware a diccionario
#             for hw_type, hw_config in self.hardware_types.items():
#                 config_data["hardware_types"][hw_type] = {
#                     "name": hw_config.name,
#                     "description": hw_config.description,
#                     "enabled": hw_config.enabled,
#                     "priority": hw_config.priority,
#                     "alert_types": hw_config.alert_types
#                 }
            
#             with open(self.config_file, 'w', encoding='utf-8') as f:
#                 json.dump(config_data, f, indent=2, ensure_ascii=False)
            
#             self.logger.info("Configuración guardada exitosamente")
#             return True
            
#         except Exception as e:
#             self.logger.error(f"Error guardando configuración: {e}")
#             return False
    
#     def get_hardware_priority(self, hardware_type: str) -> str:
#         """Obtener prioridad de un tipo de hardware"""
#         hw_type = self.get_hardware_type(hardware_type)
#         return hw_type.priority if hw_type else "medium"
    
#     def get_alert_types_for_hardware(self, hardware_type: str) -> List[str]:
#         """Obtener tipos de alerta soportados para un tipo de hardware"""
#         hw_type = self.get_hardware_type(hardware_type)
#         return hw_type.alert_types if hw_type else []
    
#     def validate_alert_type(self, hardware_type: str, alert_type: str) -> bool:
#         """Validar si un tipo de alerta es válido para un tipo de hardware"""
#         supported_alerts = self.get_alert_types_for_hardware(hardware_type)
#         return alert_type.lower() in [alert.lower() for alert in supported_alerts]
    
#     def _is_valid_ip(self, ip_string: str) -> bool:
#         """Validar si una cadena es una dirección IP válida"""
#         import ipaddress
#         try:
#             ipaddress.ip_address(ip_string)
#             return True
#         except ValueError:
#             return False
