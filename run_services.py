#!/usr/bin/env python3
"""
Launcher para servicios independientes MQTT y WebSocket
Cada servicio se ejecuta completamente por separado
"""

import argparse
import subprocess
import sys
import os

def run_mqtt_service():
    """Ejecutar SOLO el servicio MQTT"""
    
    mqtt_script = os.path.join(os.path.dirname(__file__), 'mqtt_service.py')
    return subprocess.run([sys.executable, mqtt_script])

def run_websocket_service():
    """Ejecutar SOLO el servicio WebSocket"""
    
    websocket_script = os.path.join(os.path.dirname(__file__), 'websocket_service.py')
    return subprocess.run([sys.executable, websocket_script])

def run_both_services():
    """Ejecutar ambos servicios en procesos separados"""
    
    import multiprocessing
    
    # Crear procesos separados
    mqtt_process = multiprocessing.Process(target=run_mqtt_service)
    websocket_process = multiprocessing.Process(target=run_websocket_service)
    
    try:
        # Iniciar ambos procesos
        mqtt_process.start()
        websocket_process.start()
        
        
        # Esperar a que terminen
        mqtt_process.join()
        websocket_process.join()
        
    except KeyboardInterrupt:
        
        # Terminar procesos
        mqtt_process.terminate()
        websocket_process.terminate()
        
        # Esperar a que terminen
        mqtt_process.join()
        websocket_process.join()
        

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Ejecutar servicios independientes')
    parser.add_argument('--mqtt', action='store_true', help='Ejecutar SOLO servicio MQTT')
    parser.add_argument('--websocket', action='store_true', help='Ejecutar SOLO servicio WebSocket')
    parser.add_argument('--both', action='store_true', help='Ejecutar ambos servicios por separado')
    
    args = parser.parse_args()
    
    if args.mqtt:
        return run_mqtt_service()
    elif args.websocket:
        return run_websocket_service()
    elif args.both:
        return run_both_services()
    else:
        # Por defecto, mostrar ayuda
        parser.print_help()
        return 0

if __name__ == "__main__":
    sys.exit(main())
