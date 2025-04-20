import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import os

def setup_logging(logger):
	load_dotenv()

	log_file = os.getenv("LOG_FILE", "kiparla_tools.log")
	error_file = os.getenv("ERROR_FILE", "kiparla_tools.log")
	log_level = os.getenv("LOG_LEVEL", "INFO").upper()

	logger.setLevel(getattr(logging, log_level, logging.INFO))

	file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
	error_handler = logging.FileHandler(error_file, "w", encoding="utf-8")
	error_handler.setLevel(logging.ERROR)

	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	file_handler.setFormatter(formatter)
	error_handler.setFormatter(formatter)

	logger.addHandler(file_handler)
	logger.addHandler(error_handler)