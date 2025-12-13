import logging
import os
from logging.handlers import RotatingFileHandler

# extra in-memory recording functionality for logging.Logger objects
import emtest.log_recording  # noqa

LOG_PATH = ".ipfs_tk.log"
print(f"Logging to {os.path.abspath(LOG_PATH)}")

# Formatter
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Console handler (INFO+)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# # File handler (INFO+ with rotation)
# file_handler = RotatingFileHandler(
#     LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5
# )
# file_handler.setLevel(logging.INFO)
# file_handler.setFormatter(formatter)


logger_transm = logging.getLogger("IPFS_TK.Transm")
logger_transm.setLevel(logging.INFO)
# logger_transm.addHandler(file_handler)
logger_transm.addHandler(console_handler)

logger_conv = logging.getLogger("IPFS_TK.Conv")
logger_conv.setLevel(logging.INFO)
# logger_conv.addHandler(file_handler)
logger_conv.addHandler(console_handler)

logger_file = logging.getLogger("IPFS_TK.File")
logger_file.setLevel(logging.INFO)
# logger_file.addHandler(file_handler)
logger_file.addHandler(console_handler)
