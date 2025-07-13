#!/usr/bin/env python3
"""
Punto de entrada principal para la aplicación MQTT escalable
"""

import sys
import os
import signal
import logging

# Agregar el directorio actual al path para las importaciones
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import AppConfig
from core import ScalableMQTTApp
from utils import setup_logger

app_instance = None

def signal_handler(signum, frame):
    """Manejar señales para detener la aplicación correctamente"""
    print("\n¡Recibida señal de terminación!")
    if app_instance:
        app_instance.stop()
    sys.exit(0)

def main():
    global app_instance
    
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Configurar logging
    logger = setup_logger("mqtt_app", "INFO")
    
    try:
        # Crear configuración
        config = AppConfig()
        
        # Crear y ejecutar aplicación
        app_instance = ScalableMQTTApp(config)
        app_instance.run()
        
    except Exception as e:
        logger.error(f"Error en aplicación principal: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
