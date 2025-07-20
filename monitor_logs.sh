#!/bin/bash

# Script para monitorear logs de ambos servicios

echo "🚀 Iniciando monitoreo de logs de servicios MQTT y WebSocket"
echo "============================================================"

# Crear directorio de logs si no existe
mkdir -p logs

# Función para limpiar al salir
cleanup() {
    echo "🛑 Deteniendo monitoreo..."
    kill $(jobs -p) 2>/dev/null
    exit 0
}

# Capturar señales de terminación
trap cleanup SIGINT SIGTERM

# Iniciar servicios en background
echo "📡 Iniciando servicios en background..."
python run_services.py --both &
SERVICES_PID=$!

# Esperar un poco a que se creen los archivos de log
sleep 3

# Mostrar logs en tiempo real con prefijos de colores
echo "📊 Mostrando logs en tiempo real (Ctrl+C para salir)..."
echo "🔵 MQTT = Azul | 🟢 WebSocket = Verde"
echo "============================================================"

# Usar tail con prefijos de color
tail -f logs/mqtt_service.log | sed 's/^/[🔵 MQTT] /' &
tail -f logs/websocket_service.log | sed 's/^/[🟢 WebSocket] /' &

# Esperar a que termine
wait $SERVICES_PID

# Limpiar al salir
cleanup
