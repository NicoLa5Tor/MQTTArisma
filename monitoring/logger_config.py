import logging
import logging.handlers
import os
from datetime import datetime
import json


class MQTTLogger:
    """
    Configuración centralizada de logging para el sistema MQTT
    """
    
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self.setup_directories()
        self.setup_loggers()
    
    def setup_directories(self):
        """Crear directorios de logs si no existen"""
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(f"{self.log_dir}/mqtt", exist_ok=True)
        os.makedirs(f"{self.log_dir}/alerts", exist_ok=True)
        os.makedirs(f"{self.log_dir}/errors", exist_ok=True)
    
    def setup_loggers(self):
        """Configurar diferentes loggers para diferentes componentes"""
        
        # Formatter común
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Logger principal del sistema
        self.main_logger = self.create_logger(
            'mqtt_system',
            f'{self.log_dir}/mqtt/system.log',
            formatter
        )
        
        # Logger para alertas
        self.alert_logger = self.create_logger(
            'mqtt_alerts',
            f'{self.log_dir}/alerts/alerts.log',
            formatter
        )
        
        # Logger para errores críticos
        self.error_logger = self.create_logger(
            'mqtt_errors',
            f'{self.log_dir}/errors/errors.log',
            formatter,
            level=logging.ERROR
        )
        
        # Logger para métricas
        self.metrics_logger = self.create_logger(
            'mqtt_metrics',
            f'{self.log_dir}/metrics.log',
            logging.Formatter('%(asctime)s - %(message)s')
        )
    
    def create_logger(self, name, filename, formatter, level=logging.INFO):
        """Crear un logger con rotación de archivos"""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Rotating file handler (10MB max, 5 backups)
        handler = logging.handlers.RotatingFileHandler(
            filename,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # También log a consola para desarrollo
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def log_mqtt_message(self, topic, payload, status="received"):
        """Log específico para mensajes MQTT"""
        self.main_logger.info(f"MQTT {status} - Topic: {topic} - Payload: {payload}")
    
    def log_alert(self, alert_data, status="created"):
        """Log específico para alertas"""
        self.alert_logger.info(f"Alert {status} - Data: {json.dumps(alert_data)}")
    
    def log_error(self, error_msg, exception=None):
        """Log específico para errores"""
        if exception:
            self.error_logger.error(f"{error_msg} - Exception: {str(exception)}")
        else:
            self.error_logger.error(error_msg)
    
    def log_metrics(self, metric_name, value, unit="", metadata=None):
        """Log específico para métricas"""
        metric_data = {
            "metric": metric_name,
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            metric_data["metadata"] = metadata
        
        self.metrics_logger.info(json.dumps(metric_data))


# Instancia global del logger
mqtt_logger = MQTTLogger()
