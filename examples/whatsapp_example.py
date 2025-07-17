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
    
    # Mostrar estadísticas finales
    print(f"\n📊 Estadísticas finales:")
    final_status = whatsapp_service.get_simple_status()
    print(f"   - Mensajes enviados: {final_status['messages_sent']}")
    print(f"   - Tasa de éxito: {final_status['success_rate']}%")
    print(f"   - Servicio saludable: {final_status['healthy']}")
    
    print(f"\n✅ Ejemplo completado")


if __name__ == "__main__":
    asyncio.run(main())
