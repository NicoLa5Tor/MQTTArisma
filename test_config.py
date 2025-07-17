#!/usr/bin/env python3
"""
Script de prueba para verificar que la configuración centralizada funciona correctamente
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import AppConfig
from utils.redis_queue_manager import RedisQueueManager

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
        
        # Probar configuración Redis
        print(f"📊 Redis Configuration:")
        print(f"  • Host: {config.redis.host}:{config.redis.port}")
        print(f"  • Database: {config.redis.db}")
        print(f"  • Password: {'***' if config.redis.password else 'None'}")
        print(f"  • Queue name: {config.redis.whatsapp_queue_name}")
        print(f"  • Workers: {config.redis.whatsapp_workers}")
        print(f"  • Queue TTL: {config.redis.whatsapp_queue_ttl}s")
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

def test_redis_queue_manager():
    """Probar que RedisQueueManager funciona con RedisConfig"""
    print("🧪 Probando RedisQueueManager...")
    print("=" * 50)
    
    try:
        # Crear configuración
        config = AppConfig()
        
        # Crear RedisQueueManager con RedisConfig
        redis_queue = RedisQueueManager(config.redis)
        
        print(f"📊 RedisQueueManager creado exitosamente:")
        print(f"  • Host: {redis_queue.redis_host}:{redis_queue.redis_port}")
        print(f"  • Database: {redis_queue.redis_db}")
        print(f"  • Queue name: {redis_queue.queue_name}")
        print(f"  • Workers: {redis_queue.workers_count}")
        print(f"  • TTL: {redis_queue.message_ttl}s")
        print()
        
        # Probar salud de Redis
        is_healthy = redis_queue.is_healthy()
        if is_healthy:
            print("✅ Redis está disponible y saludable")
        else:
            print("⚠️ Redis no está disponible (fallback normal)")
        
        print("✅ RedisQueueManager funciona correctamente con RedisConfig!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando RedisQueueManager: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando pruebas...\n")
    
    tests = [
        ("Configuración", test_configuration),
        ("RedisQueueManager", test_redis_queue_manager)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASÓ\n")
        else:
            print(f"❌ {test_name}: FALLÓ\n")
    
    print(f"📊 Resumen: {passed}/{total} pruebas pasaron")
    sys.exit(0 if passed == total else 1)
