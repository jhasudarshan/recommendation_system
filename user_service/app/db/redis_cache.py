import redis
import json
import time
import threading
from datetime import datetime,timezone
from app.config.logger_config import logger
from app.config.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD
from app.db.mongo import mongo_db

class RedisCache:
    def __init__(self):
        try:
            self.client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                ssl=True
            )
            self.user_collection = mongo_db.get_collection("users")
            self.start_expiry_monitor()
            logger.info("Redis Connected Successfully.")
        except redis.ConnectionError as e:
            logger.error(f"Redis Connection Failed: {e}")
            self.client = None

    def set_cache(self, key: str, value: dict, expiry: int = 3600):
        if not self.client:
            logger.error("Redis Not Initialized! Cannot set cache.")
            return False
        try:
            expiry_time = datetime.now(timezone.utc).timestamp() + expiry
            soft_expiry_time = expiry_time - 2
            value = {"data": value}
            
            value["_expiry"] = expiry_time

            self.client.setex(key, expiry, json.dumps(value))
            self.client.zadd("expiring_keys", {key: soft_expiry_time})
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
    
    def remove_user_from_cache(self, email):
        try:
            redis_user_key = f"user:{email}"
            redis_interest_key = f"user:{email}:interest"
            cached_interest  = (self.get_cache(redis_interest_key) or {}).get("data")
            
            if cached_interest:
                interest_data = (cached_interest)
                self.user_collection.update_one(
                    {"email": email}, {"$set": {"interests": interest_data}}, upsert=True
                )
                self.delete_key(redis_user_key)
                self.delete_key(redis_interest_key)
                logger.info(f"User {email} interest saved to MongoDB & removed from Redis.")

        except Exception as e:
            logger.error(f"Error removing user from cache: {e}", exc_info=True)
    
    def poll_expired_keys(self):
        while True:
            try:
                current_time = datetime.now(timezone.utc).timestamp()
                expired_keys = self.client.zrangebyscore("expiring_keys", 0, current_time)
                
                
                for key in expired_keys:
                    key = key.decode()
                    if key.startswith("user:") and key.endswith(":interest"):
                        email = key.split(":")[1]
                        logger.info(f"Key expired: {key}, removing user {email} from cache.")
                        self.remove_user_from_cache(email)

                    self.client.zrem("expiring_keys", key)

                time.sleep(1)

            except redis.RedisError as e:
                logger.error(f"Error during expiry polling: {e}")

    def start_expiry_monitor(self):
        thread = threading.Thread(target=self.poll_expired_keys, daemon=True)
        thread.start()
        logger.info("Redis key expiry polling started.")

    def close(self):
        if self.client:
            self.client.close()
            logger.info("Redis Connection Closed.")

redis_cache = RedisCache()