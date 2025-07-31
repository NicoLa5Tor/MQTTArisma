#!/usr/bin/env python3
"""
Ejemplo de uso del método bulk_update_numbers para actualizar datos de forma masiva en WhatsApp
"""
import sys
import os

# Agregar el directorio padre al path para poder importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.whatsapp_client import WhatsAppClient
from config.settings import WhatsAppConfig


def bulk_update_example():
    """Ejemplo de actualización masiva de números de WhatsApp"""
    
    # Configurar el cliente con la URL de tu servidor de WhatsApp
    config = WhatsAppConfig()
    config.api_url = "http://localhost:5000"  # Cambiar por tu URL del servidor
    
    client = WhatsAppClient(config)
    
    print("🚀 Iniciando ejemplo de actualización masiva de números")
    print("=" * 60)
    
    # Verificar que la API esté disponible
    if not client.health_check():
        print("❌ La API de WhatsApp no está disponible")
        return False
    
    # Ejemplo 1: Actualización básica con status y campaña
    print("\n📋 Ejemplo 1: Actualización básica")
    phones_example1 = ["573123456789", "573987654321", "573111222333"]
    data_example1 = {
        "status": "active",
        "last_contact": "2024-01-20",
        "campaign": "summer_2024"
    }
    
    result1 = client.bulk_update_numbers(phones_example1, data_example1)
    if result1:
        print(f"✅ Ejemplo 1 completado: {result1}")
    else:
        print("❌ Error en ejemplo 1")
    
    # Ejemplo 2: Actualización con más campos
    print("\n📋 Ejemplo 2: Actualización con múltiples campos")
    phones_example2 = ["573555666777", "573888999000"]
    data_example2 = {
        "status": "premium",
        "plan": "gold",
        "last_purchase": "2024-01-15",
        "notifications": True,
        "language": "es",
        "region": "colombia"
    }
    
    result2 = client.bulk_update_numbers(phones_example2, data_example2)
    if result2:
        print(f"✅ Ejemplo 2 completado: {result2}")
    else:
        print("❌ Error en ejemplo 2")
    
    # Ejemplo 3: Actualización solo de estado
    print("\n📋 Ejemplo 3: Actualización solo de estado")
    phones_example3 = ["573111111111", "573222222222", "573333333333", "573444444444"]
    data_example3 = {
        "status": "inactive"
    }
    
    result3 = client.bulk_update_numbers(phones_example3, data_example3)
    if result3:
        print(f"✅ Ejemplo 3 completado: {result3}")
    else:
        print("❌ Error en ejemplo 3")
    
    print("\n🎉 Ejemplos de actualización masiva completados")
    return True


def curl_equivalent_example():
    """Mostrar el equivalente en curl del ejemplo"""
    
    print("\n" + "=" * 60)
    print("📝 EQUIVALENTE EN CURL")
    print("=" * 60)
    
    curl_command = '''curl -X PATCH http://localhost:5000/api/numbers/bulk-update \\
  -H "Content-Type: application/json" \\
  -d '{
    "phones": ["573123456789", "573987654321", "573111222333"],
    "data": {
      "status": "active",
      "last_contact": "2024-01-20",
      "campaign": "summer_2024"
    }
  }'
'''
    
    print(curl_command)


if __name__ == "__main__":
    print("🔧 Ejemplo de Actualización Masiva de Números - WhatsApp")
    print("=" * 60)
    
    # Mostrar el equivalente en curl
    curl_equivalent_example()
    
    # Ejecutar los ejemplos
    success = bulk_update_example()
    
    if success:
        print("\n✅ Todos los ejemplos se ejecutaron correctamente")
    else:
        print("\n❌ Hubo errores en la ejecución")
