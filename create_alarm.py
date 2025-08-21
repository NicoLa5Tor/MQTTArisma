#!/usr/bin/env python3
"""
Script simple para crear una alarma ficticia
Uso: python create_alarm.py "empresas/empresa/sede/BOTONERA/hardware"
"""

import json
import sys
import time
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import paho.mqtt.client as mqtt
    from config.settings import AppConfig
except ImportError as e:
    print(f"❌ Error: {e}")
    print("💡 Instala paho-mqtt: pip install paho-mqtt")
    sys.exit(1)

def create_alarm(topic):
    """Crear y enviar alarma ficticia"""
    
    # Datos de alarma ficticia - estructura simple que será procesada por el MQTT handler
    alarm_data = {
    "tipo_mensaje": "alarma",
    "id_origen": "BOTONERA_XXX",
    "tipo_alarma": "AZUL",  
    "ubicacion": "Oficina Principal"
  }
    
    try:
        config = AppConfig()
        client = mqtt.Client()
        
        # Configurar credenciales si existen
        if hasattr(config.mqtt, 'username') and config.mqtt.username:
            client.username_pw_set(config.mqtt.username, config.mqtt.password)
        
        print(f"🔄 Conectando a {config.mqtt.broker}:{config.mqtt.port}")
        client.connect(config.mqtt.broker, config.mqtt.port, 60)
        
        # Enviar alarma
        payload = json.dumps(alarm_data)
        print(f"📤 Enviando alarma a: {topic}")
        print(f"📋 Datos: {payload}")
        
        result = client.publish(topic, payload, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("✅ ¡Alarma enviada exitosamente!")
            time.sleep(1)
        else:
            print(f"❌ Error enviando: {result.rc}")
            return False
        
        client.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("🚨 CREAR ALARMA FICTICIA")
        print("Uso: python create_alarm.py \"topic\"")
        print("Ejemplo: python create_alarm.py \"empresas/ecoes/sede1/BOTONERA/boton01\"")
        sys.exit(1)
    
    topic = sys.argv[1]
    
    print(f"🚨 Creando alarma ficticia para: {topic}")
    
    if create_alarm(topic):
        print("🎉 ¡Listo! Revisa los logs del sistema")
    else:
        print("❌ Error creando la alarma")
        sys.exit(1)

if __name__ == "__main__":
    main()
