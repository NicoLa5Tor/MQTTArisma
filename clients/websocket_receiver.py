"""
Clase para manejar la conexión WebSocket
"""
import logging
import websocket
from threading import Thread, Event
from typing import Callable, Optional
import time
from config.settings import WebSocketConfig


class WebSocketReceiver:
    """Clase para recibir mensajes a través de WebSocket"""

    def __init__(self, config: WebSocketConfig):
        self.config = config
        self.ws: Optional[websocket.WebSocketApp] = None
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
        self.stop_event = Event()
        self.thread: Optional[Thread] = None
        
        # Callbacks personalizables
        self.on_message_callback: Optional[Callable[[str], None]] = None
        self.on_connect_callback: Optional[Callable[[], None]] = None
        self.on_close_callback: Optional[Callable[[], None]] = None

    def _on_message(self, ws, message):
        """Callback para cuando se recibe un mensaje"""
        self.logger.info(f"Mensaje recibido: {message}")

        if self.on_message_callback:
            self.on_message_callback(message)

    def _on_open(self, ws):
        """Callback para cuando la conexión se abre"""
        self.is_connected = True
        self.logger.info("Conexión WebSocket abierta")

        if self.on_connect_callback:
            self.on_connect_callback()

    def _on_close(self, ws, close_status_code, close_msg):
        """Callback para cuando la conexión se cierra"""
        self.is_connected = False
        self.logger.info(f"Conexión WebSocket cerrada: {close_status_code} {close_msg}")

        if self.on_close_callback:
            self.on_close_callback()

        # No intentar reconectar si se está deteniendo o si fue un error de conexión inicial
        if not self.stop_event.is_set() and close_status_code != 1006:
            self._attempt_reconnect()
    
    def _on_error(self, ws, error):
        """Callback para errores"""
        self.logger.error(f"Error WebSocket: {error}")
        
    def _attempt_reconnect(self):
        """Intentar reconectar al WebSocket"""
        attempts = 0
        while attempts < self.config.reconnect_attempts and not self.is_connected and not self.stop_event.is_set():
            self.logger.info(f"Intentando reconectar... ({attempts + 1}/{self.config.reconnect_attempts})")
            time.sleep(self.config.reconnect_delay)
            if not self.stop_event.is_set():
                success = self.connect()
                if success:
                    break
            attempts += 1
            
        if attempts >= self.config.reconnect_attempts:
            self.logger.warning("Se agotaron los intentos de reconexión WebSocket")

    def connect(self):
        """Conectar al WebSocket"""
        if self.thread and self.thread.is_alive():
            self.logger.warning("Ya hay una conexión WebSocket activa")
            return False
            
        self.stop_event.clear()
        
        try:
            self.ws = websocket.WebSocketApp(
                self.config.url,
                on_message=self._on_message,
                on_open=self._on_open,
                on_close=self._on_close,
                on_error=self._on_error
            )
            
            self.thread = Thread(target=self._run_websocket)
            self.thread.daemon = True
            self.thread.start()
            
            # Esperar un poco para ver si la conexión se establece
            time.sleep(1)
            return True
            
        except Exception as e:
            self.logger.error(f"Error iniciando WebSocket: {e}")
            return False
    
    def _run_websocket(self):
        """Ejecutar WebSocket con timeout"""
        try:
            self.ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as e:
            self.logger.error(f"Error en WebSocket: {e}")

    def disconnect(self):
        """Desconectar del WebSocket"""
        self.stop_event.set()
        
        if self.ws:
            self.ws.close()
            
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
            
        self.is_connected = False

    def set_message_callback(self, callback: Callable[[str], None]):
        """Establecer callback para mensajes recibidos"""
        self.on_message_callback = callback

    def set_connect_callback(self, callback: Callable[[], None]):
        """Establecer callback para conexión abierta"""
        self.on_connect_callback = callback

    def set_close_callback(self, callback: Callable[[], None]):
        """Establecer callback para conexión cerrada"""
        self.on_close_callback = callback

