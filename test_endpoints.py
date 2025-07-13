#!/usr/bin/env python3
"""
Aplicación de prueba para verificar endpoints del backend
"""

import sys
import os
import json
import time

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import AppConfig
from clients import BackendClient
from utils import setup_logger

def main():
    """Función principal para probar endpoints"""
    
    # Configurar logging
    logger = setup_logger("endpoint_test", "INFO")
    
    # Crear configuración y cliente
    config = AppConfig()
    backend_client = BackendClient(config.backend)
    
    logger.info("=== PRUEBA DE ENDPOINTS DEL BACKEND ===")
    
    # Test 1: Health Check
    logger.info("\n--- TEST 1: Health Check ---")
    try:
        health = backend_client.health_check()
        logger.info(f"Health check: {'✅ OK' if health else '❌ Error'}")
    except Exception as e:
        logger.error(f"Error en health check: {e}")
    
    # Test 2: Test Flow
    logger.info("\n--- TEST 2: Test Flow ---")
    try:
        flow_response = backend_client.test_flow()
        if flow_response:
            logger.info(f"Test flow: ✅ OK")
            logger.info(f"Response: {json.dumps(flow_response, indent=2)}")
        else:
            logger.error("Test flow: ❌ Error")
    except Exception as e:
        logger.error(f"Error en test flow: {e}")
    
    # Test 3: Verificar Hardware
    logger.info("\n--- TEST 3: Verificar Hardware ---")
    try:
        hardware_response = backend_client.verify_hardware("Semaforo001")
        if hardware_response:
            logger.info(f"Verificación de hardware: ✅ OK")
            logger.info(f"Hardware existe: {hardware_response.get('verification_info', {}).get('hardware_exists', False)}")
        else:
            logger.error("Verificación de hardware: ❌ Error")
    except Exception as e:
        logger.error(f"Error verificando hardware: {e}")
    
    # Test 4: Verificar Empresa y Sede
    logger.info("\n--- TEST 4: Verificar Empresa y Sede ---")
    try:
        empresa_response = backend_client.verify_empresa_sede("empresa1", "principal")
        if empresa_response:
            logger.info(f"Verificación de empresa y sede: ✅ OK")
            logger.info(f"Empresa existe: {empresa_response.get('success', False)}")
        else:
            logger.error("Verificación de empresa y sede: ❌ Error")
    except Exception as e:
        logger.error(f"Error verificando empresa y sede: {e}")
    
    # Test 5: Enviar Datos MQTT
    logger.info("\n--- TEST 5: Enviar Datos MQTT ---")
    try:
        mqtt_data = {
            "empresa1": {
                "semaforo": {
                    "sede": "principal",
                    "alerta": "amarilla",
                    "ubicacion": "Cruce principal",
                    "nombre": "Semaforo001",
                    "timestamp": time.time()
                }
            }
        }
        
        mqtt_response = backend_client.send_mqtt_data(mqtt_data)
        if mqtt_response:
            logger.info(f"Envío de datos MQTT: ✅ OK")
            logger.info(f"Response: {json.dumps(mqtt_response, indent=2)}")
        else:
            logger.error("Envío de datos MQTT: ❌ Error")
    except Exception as e:
        logger.error(f"Error enviando datos MQTT: {e}")
    
    # Test 6: Obtener Alertas
    logger.info("\n--- TEST 6: Obtener Alertas ---")
    try:
        alerts_response = backend_client.get_all_alerts(page=1, limit=10)
        if alerts_response:
            logger.info(f"Obtención de alertas: ✅ OK")
            logger.info(f"Total alertas: {alerts_response.get('total', 0)}")
        else:
            logger.error("Obtención de alertas: ❌ Error")
    except Exception as e:
        logger.error(f"Error obteniendo alertas: {e}")
    
    logger.info("\n=== PRUEBA COMPLETADA ===")

if __name__ == '__main__':
    main()
