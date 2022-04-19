import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler


def log(message):
    logging.info(message)


log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

os.makedirs("logs", exist_ok=True)
# log_file_name = f"logs/{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
log_file_name = f"logs/teletekst_nieuws.log"

# timed rotated log files
file_handler = TimedRotatingFileHandler(log_file_name, when="midnight", interval=1)
file_handler.suffix = "%Y%m%d"
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)
root_logger.addHandler(console_handler)

logger = logging.getLogger("teletekst_nieuws")
logger.info("Logger initialized")
