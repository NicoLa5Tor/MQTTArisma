"""
Utilidades para configurar logging
"""
import logging
import sys
from datetime import datetime


def setup_logger(name: str = "mqtt_app", level: str = "INFO", 
                log_file: str = None, format_string: str = None) -> logging.Logger:
    """
    Configurar logger para la aplicación
    
    Args:
        name: Nombre del logger
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Archivo de log opcional
        format_string: Formato personalizado de log
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Limpiar handlers existentes
    logger.handlers.clear()
    
    # Formato por defecto
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(format_string)
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para archivo si se especifica
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_timestamped_filename(base_name: str, extension: str = "log") -> str:
    """
    Generar nombre de archivo con timestamp
    
    Args:
        base_name: Nombre base del archivo
        extension: Extensión del archivo
    
    Returns:
        Nombre de archivo con timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}.{extension}"
