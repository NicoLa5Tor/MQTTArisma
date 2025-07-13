#!/usr/bin/env python3
"""
Versión de debug para identificar problemas
"""

import sys
import os
import logging

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_main():
    print("Iniciando debug...")
    
    try:
        # Configurar logging básico
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        print("Importando configuración...")
        from config import AppConfig
        
        print("Importando aplicación...")
        from core import ScalableMQTTApp
        
        print("Creando configuración...")
        config = AppConfig()
        
        print("Creando aplicación...")
        app = ScalableMQTTApp(config)
        
        print("Iniciando aplicación...")
        if app.start():
            print("Aplicación iniciada exitosamente")
            
            # Ejecutar por 5 segundos
            import time
            time.sleep(5)
            
            print("Deteniendo aplicación...")
            app.stop()
            print("Aplicación detenida")
        else:
            print("Error iniciando aplicación")
            
    except Exception as e:
        print(f"Error en debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_main()
