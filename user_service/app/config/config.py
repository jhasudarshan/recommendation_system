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

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"))

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

OTP_EXPIRY_SECONDS = int(os.getenv("OTP_EXPIRY_SECONDS"))
OTP_REQUEST_LIMIT = int(os.getenv("OTP_REQUEST_LIMIT"))
OTP_RESEND_COOLDOWN = int(os.getenv("OTP_RESEND_COOLDOWN"))

logger.info("User Service Configuration Loaded: Qdrant, Kafka, Redis")