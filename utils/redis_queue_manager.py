"""
Redis Queue Manager para mensajes de WhatsApp
Mantiene la secuencialidad pero permite múltiples workers
"""
import redis
import json
import asyncio
import logging
import time
import threading
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor
import os
from dotenv import load_dotenv
from config.settings import RedisConfig

load_dotenv()

class RedisQueueManager:
    """
    Manejador de colas Redis para mensajes de WhatsApp
    Mantiene la secuencialidad FIFO pero permite múltiples workers
    """
    
    def __init__(self, config: RedisConfig = None):
        self.logger = logging.getLogger(__name__)
        
        # Usar configuración centralizada si se proporciona
        if config:
            # Configuración Redis desde RedisConfig
            self.config = config
            self.redis_host = config.host
            self.redis_port = config.port
            self.redis_db = config.db
            self.redis_password = config.password
            
            # Configuración de colas desde RedisConfig
            self.queue_name = config.whatsapp_queue_name
            self.workers_count = config.whatsapp_workers
            self.message_ttl = config.whatsapp_queue_ttl
        else:
            # Fallback a variables de entorno directo
            self.config = None
            self.redis_host = os.getenv('REDIS_HOST', 'localhost')
            self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
            self.redis_db = int(os.getenv('REDIS_DB', '0'))
            self.redis_password = os.getenv('REDIS_PASSWORD') or None
            
            self.queue_name = os.getenv('WHATSAPP_QUEUE_NAME', 'whatsapp_messages')
            self.workers_count = int(os.getenv('WHATSAPP_WORKERS', '3'))
            self.message_ttl = int(os.getenv('WHATSAPP_QUEUE_TTL', '3600'))
        
        # Configuración de colas derivada
        self.processing_queue = f"{self.queue_name}:processing"
        self.failed_queue = f"{self.queue_name}:failed"
        
        # Conexión Redis
        self.redis_client = None
        self.workers = []
        self.is_running = False
        
        # Estadísticas
        self.stats = {
            'processed_messages': 0,
            'error_count': 0,
            'start_time': time.time()
        }
        
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Inicializar conexión Redis"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Probar conexión
            self.redis_client.ping()
            self.logger.info(f"✅ Conectado a Redis: {self.redis_host}:{self.redis_port}")
            
        except Exception as e:
            self.logger.error(f"❌ Error conectando a Redis: {e}")
            raise
    
    def is_healthy(self) -> bool:
        """Verificar si Redis está disponible"""
        try:
            return self.redis_client.ping()
        except Exception:
            return False
    
    def add_message(self, message: str, priority: int = 0) -> bool:
        """
        Agregar mensaje a la cola Redis
        
        Args:
            message: Mensaje JSON string
            priority: Prioridad (0 = normal, 1 = alta)
            
        Returns:
            bool: True si se agregó exitosamente
        """
        try:
            # Crear estructura del mensaje
            message_data = {
                'id': f"{int(time.time() * 1000)}_{threading.get_ident()}",
                'content': message,
                'priority': priority,
                'timestamp': time.time(),
                'attempts': 0
            }
            
            # Usar LPUSH para FIFO (First In, First Out)
            result = self.redis_client.lpush(
                self.queue_name, 
                json.dumps(message_data)
            )
            
            if result:
                self.logger.info(f"✅ Mensaje agregado a cola Redis: {message_data['id']}")
                return True
            else:
                self.logger.error(f"❌ Error agregando mensaje a cola Redis")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error agregando mensaje a Redis: {e}")
            return False
    
    def get_message(self, timeout: int = 2) -> Optional[Dict]:
        """
        Obtener mensaje de la cola (bloqueo hasta timeout)
        
        Args:
            timeout: Tiempo máximo de espera en segundos
            
        Returns:
            Dict con el mensaje o None si no hay mensajes
        """
        try:
            # BRPOP para obtener de forma bloqueante (FIFO)
            result = self.redis_client.brpop(self.queue_name, timeout=timeout)
            
            if result:
                queue_name, message_json = result
                message_data = json.loads(message_json)
                
                # Mover a cola de procesamiento
                self.redis_client.lpush(
                    self.processing_queue,
                    json.dumps(message_data)
                )
                
                return message_data
            else:
                return None
                
        except Exception as e:
            # Solo log si no es timeout
            if "Timeout" not in str(e):
                self.logger.error(f"❌ Error obteniendo mensaje de Redis: {e}")
            return None
    
    def mark_message_completed(self, message_id: str) -> bool:
        """Marcar mensaje como completado"""
        try:
            # Buscar y remover de la cola de procesamiento
            processing_messages = self.redis_client.lrange(self.processing_queue, 0, -1)
            
            for msg_json in processing_messages:
                msg_data = json.loads(msg_json)
                if msg_data['id'] == message_id:
                    # Remover de procesamiento
                    self.redis_client.lrem(self.processing_queue, 1, msg_json)
                    self.stats['processed_messages'] += 1
                    self.logger.info(f"✅ Mensaje completado: {message_id}")
                    return True
            
            self.logger.warning(f"⚠️ Mensaje no encontrado en procesamiento: {message_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error marcando mensaje como completado: {e}")
            return False
    
    def mark_message_failed(self, message_id: str, error: str) -> bool:
        """Marcar mensaje como fallido"""
        try:
            # Buscar en cola de procesamiento
            processing_messages = self.redis_client.lrange(self.processing_queue, 0, -1)
            
            for msg_json in processing_messages:
                msg_data = json.loads(msg_json)
                if msg_data['id'] == message_id:
                    # Incrementar intentos
                    msg_data['attempts'] += 1
                    msg_data['last_error'] = error
                    msg_data['failed_at'] = time.time()
                    
                    # Remover de procesamiento
                    self.redis_client.lrem(self.processing_queue, 1, msg_json)
                    
                    # Si no ha superado el límite, devolver a la cola
                    if msg_data['attempts'] < 3:
                        self.redis_client.lpush(self.queue_name, json.dumps(msg_data))
                        self.logger.warning(f"🔄 Mensaje devuelto a cola (intento {msg_data['attempts']}): {message_id}")
                    else:
                        # Mover a cola de fallidos
                        self.redis_client.lpush(self.failed_queue, json.dumps(msg_data))
                        self.stats['error_count'] += 1
                        self.logger.error(f"❌ Mensaje movido a fallidos: {message_id}")
                    
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error marcando mensaje como fallido: {e}")
            return False
    
    def start_workers(self, processor_function):
        """
        Iniciar workers para procesar mensajes
        
        Args:
            processor_function: Función que procesa cada mensaje
        """
        if self.is_running:
            self.logger.warning("⚠️ Workers ya están corriendo")
            return
        
        self.is_running = True
        self.logger.info(f"🚀 Iniciando {self.workers_count} workers Redis...")
        
        # Crear workers usando ThreadPoolExecutor
        self.executor = ThreadPoolExecutor(max_workers=self.workers_count)
        
        for i in range(self.workers_count):
            worker = self.executor.submit(self._worker_loop, i, processor_function)
            self.workers.append(worker)
        
        self.logger.info(f"✅ {self.workers_count} workers iniciados")
    
    def _worker_loop(self, worker_id: int, processor_function):
        """Loop principal del worker"""
        self.logger.info(f"🔄 Worker {worker_id} iniciado")
        
        while self.is_running:
            try:
                # Obtener mensaje de la cola
                message_data = self.get_message(timeout=2)
                
                if message_data:
                    message_id = message_data['id']
                    message_content = message_data['content']
                    
                    self.logger.info(f"📱 Worker {worker_id} procesando: {message_id}")
                    
                    try:
                        # Procesar mensaje
                        success = processor_function(message_content)
                        
                        if success:
                            self.mark_message_completed(message_id)
                        else:
                            self.mark_message_failed(message_id, "Procesamiento fallido")
                            
                    except Exception as e:
                        self.logger.error(f"❌ Worker {worker_id} error procesando: {e}")
                        self.mark_message_failed(message_id, str(e))
                
            except Exception as e:
                if self.is_running:  # Solo log si seguimos corriendo
                    self.logger.error(f"❌ Error en worker {worker_id}: {e}")
                    time.sleep(1)  # Esperar antes de reintentar
        
        self.logger.info(f"🛑 Worker {worker_id} detenido")
    
    def stop_workers(self):
        """Detener todos los workers"""
        if not self.is_running:
            self.logger.warning("⚠️ Workers no están corriendo")
            return
        
        self.logger.info("🛑 Deteniendo workers...")
        self.is_running = False
        
        # Esperar a que terminen
        self.executor.shutdown(wait=True)
        self.workers.clear()
        
        self.logger.info("✅ Workers detenidos")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de la cola"""
        try:
            queue_size = self.redis_client.llen(self.queue_name)
            processing_size = self.redis_client.llen(self.processing_queue)
            failed_size = self.redis_client.llen(self.failed_queue)
            
            uptime = time.time() - self.stats['start_time']
            
            return {
                'queue_size': queue_size,
                'processing_size': processing_size,
                'failed_size': failed_size,
                'processed_messages': self.stats['processed_messages'],
                'error_count': self.stats['error_count'],
                'workers_count': self.workers_count,
                'is_running': self.is_running,
                'uptime_seconds': round(uptime, 2),
                'redis_healthy': self.is_healthy()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {
                'error': str(e),
                'redis_healthy': False
            }
    
    def clear_queue(self, queue_type: str = 'main') -> int:
        """
        Limpiar cola específica
        
        Args:
            queue_type: 'main', 'processing', 'failed', o 'all'
            
        Returns:
            int: Número de mensajes eliminados
        """
        try:
            cleared_count = 0
            
            if queue_type in ['main', 'all']:
                cleared_count += self.redis_client.delete(self.queue_name)
            
            if queue_type in ['processing', 'all']:
                cleared_count += self.redis_client.delete(self.processing_queue)
            
            if queue_type in ['failed', 'all']:
                cleared_count += self.redis_client.delete(self.failed_queue)
            
            self.logger.info(f"🗑️ Cola {queue_type} limpiada: {cleared_count} mensajes")
            return cleared_count
            
        except Exception as e:
            self.logger.error(f"❌ Error limpiando cola: {e}")
            return 0
