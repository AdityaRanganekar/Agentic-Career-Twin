import logging
import os
from datetime import datetime

def get_custom_logger(name: str):
    """Creates or retrieves a logger with your custom timestamped file handler."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)
        os.makedirs("logs", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        fh = logging.FileHandler(f"logs/{timestamp}.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        
        logger.addHandler(fh)
        
    return logger