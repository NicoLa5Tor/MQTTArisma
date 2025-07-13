#!/usr/bin/env python3
"""
Script de inicio rápido para el sistema MQTT
"""

import os
import sys
import time
import subprocess
import signal
import threading
from pathlib import Path

def check_dependencies():
    """Verificar que las dependencias están instaladas"""
    required_packages = ['pymongo', 'flask', 'paho-mqtt']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Faltan las siguientes dependencias: {', '.join(missing_packages)}")
        print("Instálalas con: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ Todas las dependencias están instaladas")
    return True

def check_mongodb():
    """Verificar que MongoDB está corriendo"""
    try:
        from pymongo import MongoClient
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✅ MongoDB está corriendo")
        return True
    except Exception as e:
        print(f"❌ MongoDB no está disponible: {e}")
        print("Inicia MongoDB con: sudo systemctl start mongod")
        return False

def check_mqtt_broker():
    """Verificar que el broker MQTT está corriendo"""
    try:
        import paho.mqtt.client as mqtt
        
        def on_connect(client, userdata, flags, rc):
            client.connected = (rc == 0)
            client.disconnect()
        
        client = mqtt.Client()
        client.on_connect = on_connect
        client.connected = False
        
        client.connect("localhost", 1883, 60)
        client.loop_start()
        
        # Esperar un poco para la conexión
        time.sleep(1)
        client.loop_stop()
        
        if client.connected:
            print("✅ Broker MQTT está corriendo")
            return True
        else:
            print("❌ No se pudo conectar al broker MQTT")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando broker MQTT: {e}")
        print("Inicia Mosquitto con: sudo systemctl start mosquitto")
        return False

def setup_directories():
    """Crear directorios necesarios"""
    directories = [
        'logs',
        'logs/mqtt',
        'logs/alerts',
        'logs/errors'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directorios creados")

def start_mqtt_server():
    """Iniciar el servidor MQTT"""
    try:
        print("🚀 Iniciando servidor MQTT...")
        if os.path.exists('servidor_mqtt.py'):
            process = subprocess.Popen([sys.executable, 'servidor_mqtt.py'])
            time.sleep(2)  # Dar tiempo para que inicie
            return process
        else:
            print("❌ No se encontró servidor_mqtt.py")
            return None
    except Exception as e:
        print(f"❌ Error iniciando servidor MQTT: {e}")
        return None

def start_dashboard():
    """Iniciar el dashboard de monitoreo"""
    try:
        print("🚀 Iniciando dashboard de monitoreo...")
        process = subprocess.Popen([sys.executable, '-m', 'monitoring.dashboard'])
        time.sleep(2)  # Dar tiempo para que inicie
        return process
    except Exception as e:
        print(f"❌ Error iniciando dashboard: {e}")
        return None

def run_tests():
    """Ejecutar pruebas del sistema"""
    try:
        print("🧪 Ejecutando pruebas del sistema...")
        if os.path.exists('ejemplo_uso.py'):
            result = subprocess.run([sys.executable, 'ejemplo_uso.py'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print("✅ Pruebas exitosas")
                return True
            else:
                print(f"❌ Pruebas fallaron: {result.stderr}")
                return False
        else:
            print("❌ No se encontró ejemplo_uso.py")
            return False
    except Exception as e:
        print(f"❌ Error ejecutando pruebas: {e}")
        return False

def print_status():
    """Mostrar estado del sistema"""
    print("\n" + "="*50)
    print("🎯 ESTADO DEL SISTEMA")
    print("="*50)
    print("📊 Dashboard: http://localhost:5001")
    print("🌐 API Backend: http://localhost:5000")
    print("📨 MQTT Broker: localhost:1883")
    print("📋 Logs: ./logs/")
    print("="*50)

def signal_handler(signum, frame):
    """Manejar señales para cerrar procesos"""
    print(f"\n🛑 Recibida señal {signum}, cerrando procesos...")
    
    # Terminar procesos hijos
    for process in processes:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    
    print("👋 Sistema cerrado")
    sys.exit(0)

def main():
    """Función principal"""
    print("🚀 Iniciando Sistema MQTT de Alertas")
    print("="*40)
    
    # Verificar dependencias
    if not check_dependencies():
        sys.exit(1)
    
    # Verificar servicios
    if not check_mongodb():
        sys.exit(1)
    
    if not check_mqtt_broker():
        sys.exit(1)
    
    # Configurar entorno
    setup_directories()
    
    # Iniciar servicios
    global processes
    processes = []
    
    # Registrar manejador de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Iniciar servidor MQTT
    mqtt_process = start_mqtt_server()
    if mqtt_process:
        processes.append(mqtt_process)
    
    # Iniciar dashboard
    dashboard_process = start_dashboard()
    if dashboard_process:
        processes.append(dashboard_process)
    
    # Esperar un poco antes de las pruebas
    time.sleep(5)
    
    # Ejecutar pruebas
    if run_tests():
        print("✅ Sistema iniciado correctamente")
        print_status()
        
        try:
            # Mantener el sistema corriendo
            print("\n💡 Presiona Ctrl+C para cerrar el sistema")
            while True:
                # Verificar que los procesos siguen corriendo
                for i, process in enumerate(processes):
                    if process and process.poll() is not None:
                        print(f"⚠️  Proceso {i} terminó inesperadamente")
                
                time.sleep(10)
                
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)
    else:
        print("❌ Error en las pruebas, cerrando sistema")
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()
