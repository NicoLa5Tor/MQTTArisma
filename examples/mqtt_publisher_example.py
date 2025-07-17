#!/usr/bin/env python3
"""
Ejemplo de uso del servicio independiente de publicación MQTT
"""

import sys
import os
import time
import signal
import asyncio

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mqtt_publisher_service import MQTTPublisherService
from utils import setup_logger

# Instancia global del servicio
service_instance = None

def signal_handler(signum, frame):
    """Manejar señales para detener el servicio"""
    print("\n¡Recibida señal de terminación!")
    if service_instance:
        service_instance.stop()
    sys.exit(0)

async def test_publishing():
    """Función para probar la publicación de mensajes"""
    global service_instance
    
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Configurar logging
    logger = setup_logger("mqtt_publisher_example", "INFO")
    
    # Crear servicio
    service_instance = MQTTPublisherService()
    
    try:
        # Iniciar servicio
        if not service_instance.start():
            print("❌ Error iniciando servicio")
            return
        
        print("✅ Servicio iniciado correctamente")
        print("=" * 50)
        
        # Mostrar estado inicial
        status = service_instance.get_simple_status()
        print(f"📊 Estado inicial: {status}")
        print("=" * 50)
        
        # Ejemplos de publicación
        print("\n🚀 Iniciando ejemplos de publicación...")
        
        # 1. Publicar mensaje simple
        print("\n1️⃣ Publicando mensaje simple:")
        success = service_instance.publish_message(
            "test/simple", 
            "¡Hola desde el servicio independiente!"
        )
        print(f"Resultado: {'✅ Exitoso' if success else '❌ Error'}")
        
        # 2. Publicar JSON
        print("\n2️⃣ Publicando JSON:")
        test_data = {
            "timestamp": time.time(),
            "message": "Mensaje JSON desde servicio independiente",
            "level": "INFO",
            "source": "mqtt_publisher_example",
            "data": {
                "temperature": 25.5,
                "humidity": 60,
                "active": True
            }
        }
        success = service_instance.publish_json("test/json", test_data)
        print(f"Resultado: {'✅ Exitoso' if success else '❌ Error'}")
        
        # 3. Publicar varios mensajes
        print("\n3️⃣ Publicando varios mensajes:")
        for i in range(5):
            message = f"Mensaje batch #{i+1}"
            success = service_instance.publish_message(f"test/batch/{i}", message)
            print(f"  Mensaje {i+1}: {'✅' if success else '❌'}")
            await asyncio.sleep(1)  # Esperar 1 segundo entre mensajes
        
        # 4. Mostrar estadísticas
        print("\n📊 Estadísticas del servicio:")
        status = service_instance.get_status()
        print(f"  🏃 Corriendo: {status['service']['running']}")
        print(f"  📡 Conectado: {status['mqtt_publisher']['connected']}")
        print(f"  📤 Mensajes publicados: {status['mqtt_publisher']['messages_published']}")
        print(f"  ✅ Tasa de éxito: {status['service']['success_rate']}%")
        print(f"  ⏱️ Uptime: {status['service']['uptime_seconds']} segundos")
        
        # 5. Publicar con QoS diferentes
        print("\n4️⃣ Publicando con diferentes QoS:")
        qos_tests = [0, 1, 2]
        for qos in qos_tests:
            success = service_instance.publish_message(
                f"test/qos/{qos}", 
                f"Mensaje con QoS {qos}",
                qos=qos
            )
            print(f"  QoS {qos}: {'✅' if success else '❌'}")
        
        # 6. Verificar salud del servicio
        print(f"\n🏥 Servicio saludable: {'✅' if service_instance.is_healthy() else '❌'}")
        
        print("\n=" * 50)
        print("🎉 Ejemplo completado exitosamente!")
        print("💡 El servicio seguirá corriendo... Presiona Ctrl+C para detener")
        print("=" * 50)
        
        # Mantener el servicio corriendo y mostrar estadísticas periódicamente
        while True:
            await asyncio.sleep(10)
            status = service_instance.get_simple_status()
            if status['messages_published'] > 0:
                print(f"📊 Mensajes publicados: {status['messages_published']}, Tasa éxito: {status['success_rate']}%")
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupción del usuario")
    except Exception as e:
        logger.error(f"❌ Error en ejemplo: {e}")
    finally:
        # Mostrar estadísticas finales
        if service_instance:
            final_status = service_instance.get_status()
            print(f"\n📊 ESTADÍSTICAS FINALES:")
            print(f"  📤 Total mensajes: {final_status['mqtt_publisher']['messages_published']}")
            print(f"  ✅ Tasa de éxito: {final_status['service']['success_rate']}%")
            print(f"  ⏱️ Tiempo total: {final_status['service']['uptime_seconds']} segundos")
            
            # Detener servicio
            service_instance.stop()
            print("✅ Servicio detenido")

if __name__ == "__main__":
    print("🚀 Iniciando ejemplo del servicio independiente de publicación MQTT")
    print("=" * 60)
    
    try:
        asyncio.run(test_publishing())
    except KeyboardInterrupt:
        print("\n👋 Adiós!")
