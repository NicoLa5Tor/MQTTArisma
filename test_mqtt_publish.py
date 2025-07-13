#!/usr/bin/env python3
"""
Script para probar el envío de mensajes MQTT
"""
import json
import time
import paho.mqtt.client as mqtt

# Configuración MQTT
BROKER = "161.35.239.177"
PORT = 17090
USERNAME = "tocancipa"
PASSWORD = "B0mb3r0s"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Conectado al broker MQTT")
    else:
        print(f"❌ Error conectando: {rc}")

def on_publish(client, userdata, mid):
    print(f"📤 Mensaje publicado: {mid}")

def main():
    # Crear cliente
    client = mqtt.Client("test-publisher")
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    # Conectar
    print("🔄 Conectando al broker...")
    client.connect(BROKER, PORT, 60)
    client.loop_start()
    
    time.sleep(2)
    
    # Datos de prueba para botonera
    botonera_data = {
        "timestamp": "2025-01-10T20:45:00Z",
        "estado": "presionado",
        "ubicacion": "Entrada Principal",
        "dispositivo_id": "BOT001",
        "bateria": 85,
        "señal": "fuerte"
    }
    
    # Datos de prueba para IP (debería ser filtrada)
    ip_data = {
        "timestamp": "2025-01-10T20:45:00Z",
        "status": "online",
        "cpu": 45,
        "memoria": 78
    }
    
    # Enviar mensaje de BOTONERA (debería ser procesado)
    topic_botonera = "empresas/cota/BOTONERAS/BOTONERAS"
    print(f"📨 Enviando mensaje BOTONERA a: {topic_botonera}")
    client.publish(topic_botonera, json.dumps(botonera_data))
    
    time.sleep(1)
    
    # Enviar mensaje de IP (debería ser filtrado)
    topic_ip = "empresas/cota/BOTONERAS/192.168.1.6"
    print(f"📨 Enviando mensaje IP a: {topic_ip}")
    client.publish(topic_ip, json.dumps(ip_data))
    
    time.sleep(2)
    
    # Desconectar
    client.loop_stop()
    client.disconnect()
    print("✅ Desconectado")

if __name__ == "__main__":
    main()
