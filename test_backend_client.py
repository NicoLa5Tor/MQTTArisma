#!/usr/bin/env python3
"""
Prueba directa del BackendClient sin MQTT
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import BackendConfig
from clients.backend_client import BackendClient

def test_backend_client():
    print("INICIANDO PRUEBA DEL BACKEND CLIENT")
    print("="*50)
    
    # Crear configuración
    config = BackendConfig()
    print(f"Configuración creada: {config}")
    
    # Crear cliente
    client = BackendClient(config)
    print(f"Cliente creado exitosamente")
    
    # Datos de prueba
    test_data = {
        "empresa": "nicolas",
        "sede": "Secundaria", 
        "tipo_hardware": "BOTONERA",
        "nombre_hardware": "TestHardwareConDireccion",
        "data": {
            "tipo_mensaje": "alarma",
            "id_origen": "Semaforo bodega",
            "tipo_alarma": "NARANJA",
            "ubicacion": "Semaforo bodega"
        }
    }
    
    print("🔐 PROBANDO AUTENTICACIÓN...")
    print("="*50)
    
    # Probar autenticación
    token = client.authenticate_hardware(test_data)
    
    if token:
        print(f"AUTENTICACIÓN EXITOSA - Token: {token}")
        
        print("PROBANDO ENVÍO DE ALARMA...")
        print("="*50)
        
        # Probar envío de alarma
        response = client.send_alarm_data(test_data, token)
        
        if response:
            print(f"ALARMA ENVIADA EXITOSAMENTE")
        else:
            print(f"ERROR ENVIANDO ALARMA")
    else:
        print(f"AUTENTICACIÓN FALLÓ")
    
    print("🏁 PRUEBA TERMINADA")

if __name__ == "__main__":
    test_backend_client()
