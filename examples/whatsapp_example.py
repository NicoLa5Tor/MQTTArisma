#!/usr/bin/env python3
"""
Ejemplo de uso del servicio WhatsApp
"""
import sys
import os
import asyncio

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AppConfig
from services.whatsapp_service import WhatsAppService


async def main():
    """Ejemplo de uso del servicio WhatsApp"""
    print("🚀 Iniciando ejemplo de WhatsApp Service...")
    
    # Crear configuración
    config = AppConfig()
    
    # Crear servicio WhatsApp
    whatsapp_service = WhatsAppService(config.whatsapp)
    
    # Verificar estado del servicio
    print(f"\n📊 Estado del servicio:")
    status = whatsapp_service.get_status()
    print(f"   - Habilitado: {status['service']['enabled']}")
    print(f"   - API disponible: {status['client']['healthy']}")
    print(f"   - URL: {status['client']['api_url']}")
    
    if not status['client']['healthy']:
        print("❌ API de WhatsApp no disponible. Verifique que esté corriendo en el puerto 5050.")
        return
    
    # Ejemplo 1: Enviar mensaje individual
    print(f"\n📱 Ejemplo 1: Mensaje individual")
    phone = "573001234567"  # Número de ejemplo
    message = "¡Hola! Este es un mensaje de prueba desde el servicio MQTT."
    
    success = whatsapp_service.send_individual_message(phone, message)
    print(f"   - Resultado: {'✅ Éxito' if success else '❌ Error'}")
    
    # Ejemplo 2: Enviar broadcast interactivo
    print(f"\n📱 Ejemplo 2: Broadcast interactivo")
    phones = ["573001234567", "573007654321"]  # Números de ejemplo
    
    success = whatsapp_service.send_broadcast_message(
        phones=phones,
        header_type="text",
        header_content="🚨 ALERTA DE SEGURIDAD",
        body_text="Se ha detectado una emergencia en su zona. Manténgase seguro y siga las indicaciones.",
        button_text="Ver Más Info",
        button_url="https://ejemplo.com/emergencia",
        footer_text="Sistema de Alertas ECOES"
    )
    print(f"   - Resultado: {'✅ Éxito' if success else '❌ Error'}")
    
    # Ejemplo 3: Procesar notificación desde backend
    print(f"\n📱 Ejemplo 3: Procesar notificación")
    
    # Notificación individual
    notification_individual = {
        "type": "individual",
        "phone": "573001234567",
        "message": "Mensaje procesado desde notificación del backend",
        "use_queue": False
    }
    
    success = whatsapp_service.process_whatsapp_notification(notification_individual)
    print(f"   - Notificación individual: {'✅ Éxito' if success else '❌ Error'}")
    
    # Notificación broadcast
    notification_broadcast = {
        "type": "broadcast",
        "phones": ["573001234567"],
        "header_type": "text",
        "header_content": "Notificación Automática",
        "body_text": "Este mensaje fue enviado automáticamente desde el backend.",
        "button_text": "Confirmar",
        "button_url": "https://ejemplo.com/confirmar",
        "footer_text": "Sistema Automático"
    }
    
    success = whatsapp_service.process_whatsapp_notification(notification_broadcast)
    print(f"   - Notificación broadcast: {'✅ Éxito' if success else '❌ Error'}")
    
    # Ejemplo 4: Enviar bulk list message (NUEVO)
    print(f"\n📱 Ejemplo 4: Bulk List Message (Lista Masiva)")
    
    # Definir secciones de lista (común para todos)
    sections = [
        {
            "title": "Servicios técnicos",
            "rows": [
                {
                    "id": "ROJO",
                    "title": "Alerta Roja",
                    "description": "Emergencia crítica - Ayuda inmediata"
                },
                {
                    "id": "AMARILLO",
                    "title": "Alerta Amarilla",
                    "description": "Precaución - Situación a monitorear"
                },
                {
                    "id": "VERDE",
                    "title": "Alerta Verde",
                    "description": "Todo normal - Estado seguro"
                }
            ]
        },
        {
            "title": "Acciones",
            "rows": [
                {
                    "id": "STATUS",
                    "title": "Ver Estado",
                    "description": "Consultar estado actual del sistema"
                },
                {
                    "id": "HELP",
                    "title": "Ayuda",
                    "description": "Obtener asistencia técnica"
                }
            ]
        }
    ]
    
    # Definir destinatarios con mensajes personalizados
    recipients = [
        {
            "phone": "573001234567",
            "body_text": "Hola Juan, selecciona el tipo de alerta que deseas activar:"
        },
        {
            "phone": "573007654321",
            "body_text": "Hola María, ¿qué tipo de alerta necesitas configurar?"
        }
    ]
    
    success = whatsapp_service.send_bulk_list_message(
        header_text="🚨 Sistema de Alertas RESCUE",
        footer_text="Powered by ECOES - Sistema MQTT",
        button_text="Ver opciones disponibles",
        sections=sections,
        recipients=recipients,
        use_queue=True
    )
    print(f"   - Bulk list message: {'✅ Éxito' if success else '❌ Error'}")
    
    # Ejemplo 5: Enviar bulk button message (NUEVO)
    print(f"\n📱 Ejemplo 5: Bulk Button Message (Botones Masivos)")
    
    # Definir botones (común para todos)
    buttons = [
        {
            "id": "confirm_yes",
            "title": "Confirmar"
        },
        {
            "id": "confirm_no",
            "title": "Cancelar"
        },
        {
            "id": "more_info",
            "title": "Más info"
        }
    ]
    
    # Definir destinatarios con mensajes personalizados
    recipients_button = [
        {
            "phone": "573001234567",
            "body_text": "Hola Juan, ¿confirmas tu cita del lunes a las 10:00 AM?"
        },
        {
            "phone": "573007654321",
            "body_text": "Hola María, ¿confirmas tu reserva para el evento del miércoles?"
        }
    ]
    
    success = whatsapp_service.send_bulk_button_message(
        header_type="text",
        header_content="📋 Confirmación Requerida",
        buttons=buttons,
        footer_text="Responde por favor - Sistema ECOES",
        recipients=recipients_button,
        use_queue=True
    )
    print(f"   - Bulk button message: {'✅ Éxito' if success else '❌ Error'}")
    
    # Ejemplo 6: Agregar número al cache y actualizar información (NUEVO)
    print(f"\n📱 Ejemplo 6: Gestión de Cache de Usuarios")
    
    # Agregar número al cache
    phone_cache = "573123456789"
    success = whatsapp_service.add_number_to_cache(
        phone=phone_cache,
        name="Juan Pérez",
        data={
            "email": "juan@email.com",
            "company": "ECOES Tech",
            "role": "Developer",
            "location": "Medellín"
        },
        empresa_id="empresa-demo-id"
    )
    print(f"   - Agregar número al cache: {'✅ Éxito' if success else '❌ Error'}")
    
    # Actualizar información del cache
    success = whatsapp_service.update_number_cache(
        phone=phone_cache,
        data={
            "email": "nuevo.juan@email.com",
            "company": "Nueva Empresa ECOES",
            "last_update": "2024-01-15",
            "status": "active"
        },
        empresa_id="empresa-demo-id"
    )
    print(f"   - Actualizar cache: {'✅ Éxito' if success else '❌ Error'}")
    
    # Mostrar estadísticas finales
    print(f"\n📊 Estadísticas finales:")
    final_status = whatsapp_service.get_simple_status()
    print(f"   - Mensajes enviados: {final_status['messages_sent']}")
    print(f"   - Tasa de éxito: {final_status['success_rate']}%")
    print(f"   - Servicio saludable: {final_status['healthy']}")
    
    print(f"\n✅ Ejemplo completado")


if __name__ == "__main__":
    asyncio.run(main())
