import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
if not MONGO_URI:
    raise ValueError("MONGO_URI is not set in environment variables!")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))

KAFKA_BROKER = os.getenv("KAFKA_BROKER")
KAFKA_BALANCE_INTEREST_TOPIC = os.getenv("KAFKA_BALANCE_INTEREST_TOPIC")
KAFKA_EMBEDDING_UPDATE_TOPIC = os.getenv("KAFKA_EMBEDDING_UPDATE_TOPIC")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

logger.info("User Service Configuration Loaded: Qdrant, Kafka, Redis")