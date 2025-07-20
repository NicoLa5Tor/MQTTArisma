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
    print("🚀 Iniciando Servicio MQTT Independiente")
    print("=" * 60)
    print("🎯 Solo procesamiento MQTT + Backend + WhatsApp")
    print("❌ Sin dependencias de WebSocket")
    print("=" * 60)
    
    mqtt_script = os.path.join(os.path.dirname(__file__), 'mqtt_service.py')
    return subprocess.run([sys.executable, mqtt_script])

def run_websocket_service():
    """Ejecutar SOLO el servicio WebSocket"""
    print("🚀 Iniciando Servicio WebSocket Independiente")
    print("=" * 60)
    print("📱 Solo procesamiento de WhatsApp")
    print("❌ Sin dependencias de MQTT")
    print("=" * 60)
    
    websocket_script = os.path.join(os.path.dirname(__file__), 'websocket_service.py')
    return subprocess.run([sys.executable, websocket_script])

def run_both_services():
    """Ejecutar ambos servicios en procesos separados"""
    print("🚀 Iniciando Ambos Servicios en Procesos Separados")
    print("=" * 60)
    print("🎯 Proceso 1: Servicio MQTT independiente")
    print("📱 Proceso 2: Servicio WebSocket independiente")
    print("❌ Sin dependencias cruzadas")
    print("=" * 60)
    
    import multiprocessing
    
    # Crear procesos separados
    mqtt_process = multiprocessing.Process(target=run_mqtt_service)
    websocket_process = multiprocessing.Process(target=run_websocket_service)
    
    try:
        # Iniciar ambos procesos
        mqtt_process.start()
        websocket_process.start()
        
        print("✅ Ambos servicios iniciados en procesos separados")
        print("📋 Presiona Ctrl+C para detener ambos servicios")
        
        # Esperar a que terminen
        mqtt_process.join()
        websocket_process.join()
        
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo ambos servicios...")
        
        # Terminar procesos
        mqtt_process.terminate()
        websocket_process.terminate()
        
        # Esperar a que terminen
        mqtt_process.join()
        websocket_process.join()
        
        print("✅ Ambos servicios detenidos")

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
        print("\n" + "=" * 60)
        print("📋 Ejemplos de uso:")
        print("  python run_services.py --mqtt          # Solo servicio MQTT")
        print("  python run_services.py --websocket     # Solo servicio WebSocket")
        print("  python run_services.py --both          # Ambos servicios separados")
        print("=" * 60)
        return 0

if __name__ == "__main__":
    sys.exit(main())
