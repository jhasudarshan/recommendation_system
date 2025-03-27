import os
from app.config.logger_config import logger
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
if not MONGO_URI:
    raise ValueError("MONGO_URI is not set in environment variables!")

QDRANT_TOKEN = os.getenv("QDRANT_TOKEN")
QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION")

KAFKA_BROKER = os.getenv("KAFKA_BROKER")
KAFKA_BALANCE_INTEREST_TOPIC = os.getenv("KAFKA_BALANCE_INTEREST_TOPIC")
KAFKA_EMBEDDING_UPDATE_TOPIC = os.getenv("KAFKA_EMBEDDING_UPDATE_TOPIC")
INTEREST_UPDATE_GROUP = os.getenv("INTEREST_UPDATE_GROUP")
EMBEDDING_UPDATE = os.getenv("EMBEDDING_UPDATE")

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

logger.info("User Service Configuration Loaded: Qdrant, Kafka, Redis")