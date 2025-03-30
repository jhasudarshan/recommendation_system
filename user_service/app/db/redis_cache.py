import redis
import json
from app.config.logger_config import logger
from app.config.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

class RedisCache:
    def __init__(self):
        try:
            self.client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                ssl=True
            )
            logger.info("Redis Connected Successfully.")
        except redis.ConnectionError as e:
            logger.error(f"Redis Connection Failed: {e}")
            self.client = None

    def set_cache(self, key: str, value: dict, expiry: int = 3600):
        if not self.client:
            logger.error("Redis Not Initialized! Cannot set cache.")
            return False

        try:
            self.client.setex(key, expiry, json.dumps(value))
            logger.info(f"Cached data for key: '{key}' (Expires in {expiry} sec)")
            return True
        except redis.RedisError as e:
            logger.error(f"Redis Set Cache Error: {e}")
        return False

    def get_cache(self, key: str):
        if not self.client:
            logger.error("Redis Not Initialized! Cannot get cache.")
            return None

        try:
            data = self.client.get(key)
            return json.loads(data) if data else None
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Redis Get Cache Error: {e}")
        return None
    
    def set_value(self, key: str, value: str, expiry: int):
        if not self.client:
            logger.error("Redis Not Initialized! Cannot set value.")
            return False

        try:
            self.client.setex(key, expiry, value)
            logger.info(f"Stored value for key: '{key}' (Expires in {expiry} sec)")
            return True
        except redis.RedisError as e:
            logger.error(f"Redis Set Value Error: {e}")
        return False

    def get_value(self, key: str):
        if not self.client:
            logger.error("Redis Not Initialized! Cannot get value.")
            return None

        try:
            return self.client.get(key).decode() if self.client.get(key) else None
        except redis.RedisError as e:
            logger.error(f"Redis Get Value Error: {e}")
        return None

    def increment_key(self, key: str, expiry: int = 3600):
        if not self.client:
            logger.error("Redis Not Initialized! Cannot increment key.")
            return None

        try:
            count = self.client.incr(key)
            if count == 1:
                self.client.expire(key, expiry)
            return count
        except redis.RedisError as e:
            logger.error(f"Redis Increment Key Error: {e}")
        return None

    def delete_key(self, key: str):
        if not self.client:
            logger.error("Redis Not Initialized! Cannot delete key.")
            return False

        try:
            self.client.delete(key)
            logger.info(f"Deleted key: '{key}' from Redis.")
            return True
        except redis.RedisError as e:
            logger.error(f"Redis Delete Key Error: {e}")
        return False

    def close(self):
        if self.client:
            self.client.close()
            logger.info("Redis Connection Closed.")

redis_cache = RedisCache()