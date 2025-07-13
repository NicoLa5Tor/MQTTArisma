#!/usr/bin/env python3
"""
Ejemplo de uso del sistema MQTT con mensajes correctos
"""

import json
import time
from datetime import datetime

# Mensajes MQTT correctos que incluyen el nombre del hardware

# Ejemplo 1: Mensaje correcto con todos los campos
mensaje_correcto = {
    "empresa1": {
        "semaforo": {
            "sede": "principal",
            "alerta": "amarilla",
            "ubicacion": "Cruce principal",
            "nombre": "Semaforo001",  # ✅ Campo requerido
            "hardware_id": "SEM001",
            "coordenadas": {
                "lat": 4.6097,
                "lng": -74.0817
            },
            "timestamp": datetime.now().isoformat()
        }
    }
}

# Ejemplo 2: Mensaje con múltiples tipos de alertas
mensaje_multiple = {
    "empresa1": {
        "semaforo": {
            "sede": "principal", 
            "alerta": "roja",
            "nombre": "Semaforo001"
        },
        "alarma": {
            "sede": "principal",
            "tipo": "emergencia",
            "nombre": "Alarma001"
        }
    }
}

# Ejemplo 3: Mensaje con diferentes empresas
mensaje_multiples_empresas = {
    "empresa1": {
        "semaforo": {
            "sede": "principal",
            "alerta": "amarilla",
            "nombre": "Semaforo001"
        }
    },
    "empresa2": {
        "semaforo": {
            "sede": "secundaria",
            "alerta": "verde",
            "nombre": "Semaforo002"
        }
    }
}

# Ejemplo 4: Mensaje incorrecto (sin nombre de hardware)
mensaje_incorrecto = {
    "empresa1": {
        "semaforo": {
            "sede": "principal",
            "alerta": "amarilla"
            # ❌ Falta el campo "nombre"
        }
    }
}

def mostrar_ejemplos():
    """Mostrar ejemplos de uso"""
    print("=== EJEMPLOS DE MENSAJES MQTT ===\n")
    
    print("1. Mensaje correcto:")
    print(json.dumps(mensaje_correcto, indent=2))
    print("\n" + "="*50 + "\n")
    
    print("2. Mensaje con múltiples alertas:")
    print(json.dumps(mensaje_multiple, indent=2))
    print("\n" + "="*50 + "\n")
    
    print("3. Mensaje con múltiples empresas:")
    print(json.dumps(mensaje_multiples_empresas, indent=2))
    print("\n" + "="*50 + "\n")
    
    print("4. Mensaje incorrecto (sin nombre):")
    print(json.dumps(mensaje_incorrecto, indent=2))
    print("\n" + "="*50 + "\n")
    
    print("=== ESTRUCTURA REQUERIDA ===")
    print("""
    {
      "empresa_nombre": {
        "tipo_alerta": {
          "sede": "nombre_sede",
          "alerta": "tipo_alerta",
          "nombre": "nombre_hardware",  <-- REQUERIDO
          "otros_campos": "opcional"
        }
      }
    }
    """)
    
    print("\n=== FLUJO DE VERIFICACIÓN ===")
    print("1. Verificar hardware_nombre como filtro inicial")
    print("2. Si hardware no existe: autorizado=false, estado_activo=false") 
    print("3. Si hardware existe: verificar empresa y sede")
    print("4. Todo correcto: autorizado=false (pendiente), estado_activo=true")
    print("5. Hardware existe pero empresa/sede no: autorizado=false, estado_activo=false")

if __name__ == "__main__":
    mostrar_ejemplos()
