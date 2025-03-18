import os
import logging
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
if not MONGO_URI:
    raise ValueError("MONGO_URI is not set in environment variables!")

logging.info("Content Service Configuration Loaded: MongoDB, Kafka")