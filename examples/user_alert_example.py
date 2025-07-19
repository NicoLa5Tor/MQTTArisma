#!/usr/bin/env python3
"""
Ejemplo de uso del endpoint create_user_alert actualizado
"""

import sys
import os
import json

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.backend_client import BackendClient
from config import AppConfig
from utils import setup_logger

def test_create_user_alert():
    """Probar la creación de alertas de usuario con los nuevos campos"""
    
    # Configurar logging
    logger = setup_logger("user_alert_example", "INFO")
    
    # Obtener configuración
    config = AppConfig()
    
    # Crear cliente del backend
    backend_client = BackendClient(config.backend)
    
    print("🚀 Iniciando prueba de creación de alertas de usuario")
    print("=" * 60)
    
    # Ejemplos de alertas con los nuevos campos
    test_cases = [
        {
            "usuario_id": "user123",
            "tipo_alerta": "mantenimiento",
            "descripcion": "Solicitud de mantenimiento preventivo en el área de producción",
            "prioridad": "baja"
        },
        {
            "usuario_id": "user456",
            "tipo_alerta": "emergencia",
            "descripcion": "Situación de emergencia detectada en el sector norte",
            "prioridad": "alta"
        },
        {
            "usuario_id": "user789",
            "tipo_alerta": "soporte",
            "descripcion": "Solicitud de soporte técnico para resolución de incidente",
            "prioridad": "media"
        },
        {
            "usuario_id": "user101",
            "tipo_alerta": "seguridad",
            "descripcion": "Alerta de seguridad en el perímetro de la instalación"
            # prioridad no especificada, usará el valor por defecto 'media'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Caso de prueba {i}:")
        print("-" * 40)
        
        # Crear alerta
        response = backend_client.create_user_alert(
            usuario_id=test_case["usuario_id"],
            tipo_alerta=test_case["tipo_alerta"],
            descripcion=test_case["descripcion"],
            prioridad=test_case.get("prioridad", "media")  # Usar valor por defecto si no se especifica
        )
        
        if response:
            print(f"✅ Alerta creada exitosamente")
            
            # Mostrar información relevante de la respuesta
            if "alert_id" in response:
                print(f"🆔 ID de alerta: {response['alert_id']}")
            
            if "topics_otros_hardware" in response:
                topics = response["topics_otros_hardware"]
                print(f"📡 Topics generados: {len(topics)}")
                for topic in topics:
                    print(f"   - {topic}")
            
            # Mostrar respuesta completa (opcional)
            print(f"📄 Respuesta completa:")
            print(json.dumps(response, indent=2, ensure_ascii=False))
        else:
            print(f"❌ Error creando alerta")
        
        print("-" * 40)
    
    print("\n🎉 Prueba de creación completada!")
    
    # Probar desactivación de alerta
    test_deactivate_alert(backend_client)
    
    print("\n💡 Campos utilizados:")
    print("   • usuario_id: ID del usuario (obligatorio)")
    print("   • tipo_alerta: Tipo de alerta (obligatorio)")
    print("   • descripcion: Descripción de la alerta (obligatorio)")
    print("   • prioridad: Prioridad de la alerta (opcional, por defecto 'media')")
    print("\n💡 Desactivación de alerta:")
    print("   • alert_id: ID de la alerta a desactivar (obligatorio)")
    print("   • desactivado_por_id: ID del usuario que desactiva (obligatorio)")
    print("   • desactivado_por_tipo: Tipo de quien desactiva (opcional, por defecto 'usuario')")

def test_deactivate_alert(backend_client):
    """Probar la desactivación de alertas de usuario"""
    
    print("\n🔄 Iniciando prueba de desactivación de alertas")
    print("=" * 60)
    
    # Ejemplos de desactivación
    deactivate_cases = [
        {
            "alert_id": "507f1f77bcf86cd799439011",
            "desactivado_por_id": "507f1f77bcf86cd799439011",
            "desactivado_por_tipo": "usuario"
        },
        {
            "alert_id": "507f1f77bcf86cd799439012",
            "desactivado_por_id": "507f1f77bcf86cd799439012",
            "desactivado_por_tipo": "usuario"
        },
        {
            "alert_id": "507f1f77bcf86cd799439013",
            "desactivado_por_id": "507f1f77bcf86cd799439013",
            "desactivado_por_tipo": "admin"
        }
    ]
    
    for i, case in enumerate(deactivate_cases, 1):
        print(f"\n🔄 Caso de desactivación {i}:")
        print("-" * 40)
        
        # Desactivar alerta
        response = backend_client.deactivate_user_alert(
            alert_id=case["alert_id"],
            desactivado_por_id=case["desactivado_por_id"],
            desactivado_por_tipo=case["desactivado_por_tipo"]
        )
        
        if response:
            print(f"✅ Alerta desactivada exitosamente")
            print(f"📄 Respuesta:")
            print(json.dumps(response, indent=2, ensure_ascii=False))
        else:
            print(f"❌ Error desactivando alerta")
        
        print("-" * 40)
    
    print("\n🎉 Prueba de desactivación completada!")

if __name__ == "__main__":
    try:
        test_create_user_alert()
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        sys.exit(1)
