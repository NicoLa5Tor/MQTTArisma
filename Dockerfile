FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorio de logs
RUN mkdir -p logs

# Exponer puerto del WebSocket (solo usado por websocket_service)
EXPOSE 8080

# Por defecto ejecutar el servicio MQTT
# Puede ser sobrescrito en docker-compose
CMD ["python", "mqtt_service.py"]
