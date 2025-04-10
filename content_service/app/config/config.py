import os
from  app.config.logger_config import logger
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
KAFKA_BALANCE_INTEREST_TOPIC = os.getenv("KAFKA_BALANCE_INTEREST_TOPIC")
KAFKA_EMBEDDING_UPDATE_TOPIC = os.getenv("KAFKA_EMBEDDING_UPDATE_TOPIC")
KAFKA_BROKER = os.getenv("KAFKA_BROKER")
CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL")
CLASSIFICATION = os.getenv("CLASSIFICATION")
API_KEY = os.getenv("API_KEY")
FETCH_API_URL = os.getenv("FETCH_API_URL")
PROCESS_API_URL = os.getenv("PROCESS_API_URL")
CONTENT_CLASSIFY_TOPIC = os.getenv("CONTENT_CLASSIFY_TOPIC")
CONTENT_CLASSIFY_GROUP = os.getenv("CONTENT_CLASSIFY_GROUP")
if not MONGO_URI:
    raise ValueError("MONGO_URI is not set in environment variables!")

logger.info("Content Service Configuration Loaded: MongoDB, Kafka")