from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError
from app.config.logger_config import logger
from app.config.config import MONGO_URI, DB_NAME

class MongoDB:

    def __init__(self):
        self.client = None
        self.db = None
        self._connect()

    def _connect(self):
        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.db = self.client[DB_NAME]
            self.client.admin.command("ping")
            logger.info(f"Connected to MongoDB: {DB_NAME}")
        except ServerSelectionTimeoutError as e:
            logger.error(f"MongoDB Connection Timeout: {e}")
            self.client = None
        except ConfigurationError as e:
            logger.error(f"MongoDB Configuration Error: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"Unexpected MongoDB Error: {e}")
            self.client = None

    def get_collection(self, collection_name):
        if self.client is None:
            logger.error("MongoDB not connected. Attempting to reconnect")
            self._connect()
            if self.client is None:
                return None
        return self.db[collection_name]

    def close_connection(self):
        if self.client:
            self.client.close()
            logger.info(f"MongoDB connection to {DB_NAME} closed.")


mongo_db = MongoDB()