import time
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json
from .logger_config import mqtt_logger


class MetricsCollector:
    """
    Recolector de métricas para el sistema MQTT
    """
    
    def __init__(self):
        self.metrics = defaultdict(lambda: defaultdict(int))
        self.time_series = defaultdict(lambda: deque(maxlen=1000))  # Últimas 1000 muestras
        self.alerts_per_minute = deque(maxlen=60)  # Últimos 60 minutos
        self.response_times = deque(maxlen=100)  # Últimos 100 tiempos de respuesta
        self.lock = threading.Lock()
        self.start_time = datetime.now()
        
        # Inicializar contador de alertas por minuto
        self.current_minute = datetime.now().minute
        self.current_alerts_count = 0
        
        # Iniciar hilo de recolección periódica
        self.collection_thread = threading.Thread(target=self._periodic_collection, daemon=True)
        self.collection_thread.start()
    
    def increment_counter(self, metric_name, tags=None):
        """Incrementar un contador"""
        with self.lock:
            key = f"{metric_name}_{tags}" if tags else metric_name
            self.metrics[metric_name][key] += 1
            
            # Log de la métrica
            mqtt_logger.log_metrics(metric_name, self.metrics[metric_name][key], "count", tags)
    
    def record_gauge(self, metric_name, value, tags=None):
        """Registrar un valor de gauge"""
        with self.lock:
            key = f"{metric_name}_{tags}" if tags else metric_name
            self.metrics[metric_name][key] = value
            
            # Agregar a serie temporal
            self.time_series[key].append({
                'timestamp': datetime.now().isoformat(),
                'value': value
            })
            
            # Log de la métrica
            mqtt_logger.log_metrics(metric_name, value, "gauge", tags)
    
    def record_histogram(self, metric_name, value, tags=None):
        """Registrar un valor de histograma (para tiempos de respuesta)"""
        with self.lock:
            key = f"{metric_name}_{tags}" if tags else metric_name
            
            if key not in self.time_series:
                self.time_series[key] = deque(maxlen=100)
            
            self.time_series[key].append({
                'timestamp': datetime.now().isoformat(),
                'value': value
            })
            
            # Log de la métrica
            mqtt_logger.log_metrics(metric_name, value, "histogram", tags)
    
    def record_alert(self):
        """Registrar una nueva alerta"""
        current_time = datetime.now()
        
        with self.lock:
            # Verificar si cambió el minuto
            if current_time.minute != self.current_minute:
                self.alerts_per_minute.append(self.current_alerts_count)
                self.current_alerts_count = 0
                self.current_minute = current_time.minute
            
            self.current_alerts_count += 1
            self.increment_counter("alerts_total")
    
    def record_response_time(self, response_time):
        """Registrar tiempo de respuesta"""
        with self.lock:
            self.response_times.append(response_time)
            self.record_histogram("response_time", response_time)
    
    def get_metrics_summary(self):
        """Obtener resumen de métricas"""
        with self.lock:
            uptime = datetime.now() - self.start_time
            
            # Calcular estadísticas de tiempo de respuesta
            response_stats = {}
            if self.response_times:
                response_stats = {
                    'avg': sum(self.response_times) / len(self.response_times),
                    'min': min(self.response_times),
                    'max': max(self.response_times),
                    'count': len(self.response_times)
                }
            
            # Calcular alertas por minuto
            alerts_per_min = sum(self.alerts_per_minute) / len(self.alerts_per_minute) if self.alerts_per_minute else 0
            
            summary = {
                'uptime_seconds': uptime.total_seconds(),
                'uptime_formatted': str(uptime),
                'total_alerts': self.metrics.get('alerts_total', {}).get('alerts_total', 0),
                'alerts_per_minute': alerts_per_min,
                'response_time_stats': response_stats,
                'counters': dict(self.metrics),
                'timestamp': datetime.now().isoformat()
            }
            
            return summary
    
    def get_health_status(self):
        """Obtener estado de salud del sistema"""
        with self.lock:
            summary = self.get_metrics_summary()
            
            # Determinar estado basado en métricas
            status = "healthy"
            issues = []
            
            # Verificar tiempo de respuesta promedio
            if summary['response_time_stats']:
                avg_response = summary['response_time_stats']['avg']
                if avg_response > 5.0:  # Más de 5 segundos
                    status = "degraded"
                    issues.append(f"High response time: {avg_response:.2f}s")
                elif avg_response > 10.0:  # Más de 10 segundos
                    status = "unhealthy"
                    issues.append(f"Very high response time: {avg_response:.2f}s")
            
            # Verificar carga de alertas
            if summary['alerts_per_minute'] > 100:  # Más de 100 alertas por minuto
                status = "degraded"
                issues.append(f"High alert rate: {summary['alerts_per_minute']:.1f} alerts/min")
            
            return {
                'status': status,
                'issues': issues,
                'summary': summary
            }
    
    def _periodic_collection(self):
        """Recolección periódica de métricas"""
        while True:
            try:
                # Recolectar métricas cada 30 segundos
                time.sleep(30)
                
                # Log del estado actual
                health = self.get_health_status()
                mqtt_logger.log_metrics("system_health", health['status'], metadata=health)
                
            except Exception as e:
                mqtt_logger.log_error("Error in periodic metrics collection", e)


# Instancia global del recolector de métricas
metrics_collector = MetricsCollector()
