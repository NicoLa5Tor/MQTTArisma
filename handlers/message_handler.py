"""
Manejador de mensajes MQTT para BOTONERA
"""
import json
import logging
from typing import Dict, Any, Optional

class MessageHandler:
    """Manejador de mensajes MQTT para BOTONERA"""
    
    def __init__(self, backend_client, websocket_receiver=None):
        
        self.backend_client = backend_client
        self.websocket_receiver = websocket_receiver
        self.logger = logging.getLogger(__name__)
        
        # Estadísticas
        self.processed_messages = 0
        self.error_count = 0

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
                    
                    print(f"🚨 BOTONERA: {hardware_name} - {topic}")
                    
                    # Procesar JSON de BOTONERA (cualquier estructura)
                    try:
                        json_data = json.loads(payload)
                        
                        # ENVIAR DATOS AL BACKEND
                        success = self._send_botonera_to_backend(hardware_name, json_data, topic, payload)
                        
                        if success:
                            print(f"✅ Procesado exitosamente")
                        else:
                            print(f"❌ Error en procesamiento")
                        
                        self.processed_messages += 1
                        return success
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON inválido: {e}")
                        self.error_count += 1
                        return False
                    except Exception as e:
                        print(f"❌ Error procesando: {e}")
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
            return True  # Retorna True pero no hace nada

    def _send_botonera_to_backend(self, hardware_name: str, data: Dict, topic: str, payload: str) -> bool:
        """Enviar mensaje de BOTONERA al backend"""
        try:
            # Extraer datos reales del topic: empresas/nombre_empresa/sede_empresa/BOTONERA/nombre_hardware
            topic_parts = topic.split("/")
            
            # Validar estructura del topic
            if len(topic_parts) < 5 or topic_parts[0] != "empresas":
                print(f"❌ Formato de topic inválido")
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
                print(f"❌ Autenticación fallida")
                return False
            
            response = self.backend_client.send_alarm_data(mqtt_data, token)
            
            if response:
                return True
            else:
                print(f"❌ Error enviando alarma")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del manejador"""
        return {
            "processed_messages": self.processed_messages,
            "error_count": self.error_count,
            "error_rate": round(self.error_count / max(self.processed_messages, 1) * 100, 2),
            "hardware_types_count": 1  # Solo BOTONERA
        }

    def add_company(self, company_code: str, company_name: str):
        """Compatibilidad - agregar empresa (no hace nada real)"""
        self.logger.info(f"Empresa agregada: {company_code} - {company_name}")

