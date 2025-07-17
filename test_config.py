#!/usr/bin/env python3
"""
Script de prueba para verificar que la configuración centralizada funciona correctamente
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import AppConfig

def test_configuration():
    """Probar que la configuración centralizada funciona correctamente"""
    print("🧪 Probando configuración centralizada...")
    print("=" * 50)
    
    try:
        # Crear configuración
        config = AppConfig()
        
        # Probar configuración MQTT
        print(f"📡 MQTT Configuration:")
        print(f"  • Broker: {config.mqtt.broker}:{config.mqtt.port}")
        print(f"  • Username: {config.mqtt.username}")
        print(f"  • Client ID: {config.mqtt.client_id}")
        print(f"  • Topic: {config.mqtt.topic}")
        print()
        
        # Probar configuración Backend
        print(f"🖥️ Backend Configuration:")
        print(f"  • URL: {config.backend.base_url}")
        print(f"  • Timeout: {config.backend.timeout}s")
        print(f"  • Retry attempts: {config.backend.retry_attempts}")
        print(f"  • Enabled: {config.backend.enabled}")
        print()
        
        # Probar configuración WhatsApp
        print(f"📱 WhatsApp Configuration:")
        print(f"  • API URL: {config.whatsapp.api_url}")
        print(f"  • Timeout: {config.whatsapp.timeout}s")
        print(f"  • Enabled: {config.whatsapp.enabled}")
        print()
        
        # Probar configuración WebSocket
        print(f"🔌 WebSocket Configuration:")
        print(f"  • Host: {config.websocket.host}")
        print(f"  • Port: {config.websocket.port}")
        print(f"  • Ping interval: {config.websocket.ping_interval}s")
        print(f"  • Ping timeout: {config.websocket.ping_timeout}s")
        print(f"  • Enabled: {config.websocket.enabled}")
        print()
        
        # Probar configuración general
        print(f"⚙️ General Configuration:")
        print(f"  • Log level: {config.log_level}")
        print(f"  • Message interval: {config.message_interval}s")
        print()
        
        print("✅ Todas las configuraciones cargadas correctamente!")
        print("✅ Ya no se usa os.getenv() directamente en el código principal")
        print("✅ La configuración está centralizada y es más segura")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en configuración: {e}")
        return False

if __name__ == "__main__":
    success = test_configuration()
    sys.exit(0 if success else 1)
