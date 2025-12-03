import logging
from logging.handlers import RotatingFileHandler
from config.configuration import config

########### Configurar logging ########################################################


def setup_standard_logger():
    # Obtener el logger estándar de Python
    logger = logging.getLogger("endpoint_logger")
    
    # Verificar si el logger ya tiene handlers (lo que significa que ya fue configurado)
    if not logger.hasHandlers():

        logger.setLevel(logging.DEBUG)

        # Configurar un handler para escribir logs en un archivo con rotación automática
        file_handler = RotatingFileHandler(filename='./logs/app.log', maxBytes=10000, backupCount=5)
        
        # Configurar el formato del log
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        
        # Agregar el handler al logger
        logger.addHandler(file_handler)
    
    return logger


my_logger = setup_standard_logger()


def setup_api_calls_logger():
    # Crear el logger para las llamadas de API
    logger = logging.getLogger("api_calls_logger")
    
    # Verificar si ya está configurado
    if not logger.hasHandlers():

        logger.setLevel(logging.INFO)
        
        # Configurar un handler para escribir logs en un archivo con rotación automática
        file_handler = RotatingFileHandler(filename='./logs/api_calls.log', maxBytes=10000, backupCount=5)
        
        # Configurar el formato del log
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
        file_handler.setFormatter(formatter)
        
        # Agregar el handler al logger
        logger.addHandler(file_handler)

    
    return logger

