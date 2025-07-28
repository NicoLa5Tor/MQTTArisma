#!/usr/bin/env python3
"""
Script de prueba para el EmpresaAlertHandler
Envía un mensaje de prueba por WebSocket para validar el flujo completo
"""

import asyncio
import json
import websockets
from pathlib import Path

async def test_empresa_handler():
    """Enviar mensaje de prueba al WebSocket server"""
    
    # Leer el JSON de ejemplo
    example_file = Path(__file__).parent / "examples" / "empresa_message_example.json"
    
    try:
        with open(example_file, 'r', encoding='utf-8') as f:
            test_message = json.load(f)
        
        print("🔧 Mensaje de prueba cargado:")
        print(json.dumps(test_message, indent=2, ensure_ascii=False))
        print("\n" + "="*50)
        
        # Conectar al WebSocket server
        uri = "ws://localhost:8080"
        
        print(f"📡 Conectando a {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al WebSocket server")
            
            # Enviar el mensaje de prueba
            message_str = json.dumps(test_message, ensure_ascii=False)
            await websocket.send(message_str)
            
            print("📤 Mensaje enviado exitosamente")
            print("\n🔍 Revisa los logs del servicio WebSocket para ver el procesamiento")
            print("Archivo de logs: logs/websocket_service.log")
            
    except FileNotFoundError:
        print(f"❌ No se encontró el archivo de ejemplo: {example_file}")
        print("Asegúrate de que el archivo existe en examples/empresa_message_example.json")
    except json.JSONDecodeError as e:
        print(f"❌ Error parseando JSON: {e}")
    except websockets.exceptions.ConnectionRefused:
        print("❌ No se pudo conectar al WebSocket server")
        print("Asegúrate de que el servicio esté corriendo:")
        print("python websocket_service.py")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

async def test_empresa_handler_offline():
    """Test del handler sin conexión WebSocket (solo validación)"""
    print("🧪 Modo de prueba offline - Solo validación del handler")
    
    # Simular configuración mínima
    class MockConfig:
        class mqtt:
            broker = "localhost"
            port = 1883
            topic = "empresas"
            username = ""
            password = ""
            client_id = "test_empresa_handler"
            keep_alive = 60
    
    # Simular servicio WhatsApp
    class MockWhatsAppService:
        def send_bulk_individual(self, recipients, use_queue=True):
            print(f"📱 [MOCK] Enviaría mensajes a {len(recipients)} usuarios:")
            for r in recipients:
                print(f"  - {r['phone']}: {r['message'][:50]}...")
            return True
    
    # Cargar JSON de ejemplo
    example_file = Path(__file__).parent / "examples" / "empresa_message_example.json"
    
    try:
        with open(example_file, 'r', encoding='utf-8') as f:
            test_message = json.load(f)
        
        print("📋 Datos del mensaje de prueba:")
        alert = test_message["alert"]
        print(f"  - Alert ID: {alert['id']}")
        print(f"  - Empresa: {alert['empresa']}")
        print(f"  - Usuarios: {len(alert['usuarios'])}")
        print(f"  - Hardware: {len(alert['hardware_vinculado'])}")
        
        # Importar y crear el handler
        from handlers.empresa_alert_handler import EmpresaAlertHandler
        
        mock_config = MockConfig()
        mock_whatsapp = MockWhatsAppService()
        
        # Crear handler sin MQTT para test offline
        handler = EmpresaAlertHandler(
            whatsapp_service=mock_whatsapp,
            config=mock_config,
            enable_mqtt_publisher=False  # Deshabilitado para test offline
        )
        
        print("\n🔄 Procesando mensaje...")
        
        # Procesar el mensaje
        success = handler.process_empresa_deactivation(test_message)
        
        if success:
            print("✅ Mensaje procesado exitosamente")
        else:
            print("❌ Error procesando mensaje")
        
        # Mostrar estadísticas
        stats = handler.get_statistics()
        print(f"\n📊 Estadísticas del handler:")
        print(f"  - Procesados: {stats['processed_count']}")
        print(f"  - Errores: {stats['error_count']}")
        print(f"  - Tasa de error: {stats['error_rate']}%")
        
        handler.stop()
        
    except Exception as e:
        print(f"❌ Error en test offline: {e}")

def main():
    print("🧪 Test del Empresa Alert Handler")
    print("="*50)
    
    # Verificar si el usuario quiere test online u offline
    print("Opciones de prueba:")
    print("1. Test online (requiere WebSocket server corriendo)")
    print("2. Test offline (solo validación del handler)")
    
    try:
        choice = input("\nSelecciona una opción (1/2): ").strip()
        
        if choice == "1":
            print("\n🌐 Ejecutando test online...")
            asyncio.run(test_empresa_handler())
        elif choice == "2":
            print("\n💻 Ejecutando test offline...")
            asyncio.run(test_empresa_handler_offline())
        else:
            print("❌ Opción inválida")
            
    except KeyboardInterrupt:
        print("\n👋 Test cancelado por el usuario")
    except Exception as e:
        print(f"\n❌ Error ejecutando test: {e}")

if __name__ == "__main__":
    main()
