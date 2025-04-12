from fastapi import APIRouter, HTTPException
from collections import defaultdict
from bson import ObjectId
from typing import List,Dict
import numpy as np
from app.config.logger_config import logger
from app.db.mongo import mongo_db
from app.db.redis_cache import redis_cache
from app.models.mongo_model import User, Interest
from app.services.generate_embedding import CategoryEmbeddingService

router = APIRouter()

class UserInterestService:
    def __init__(self):
        self.user_collection = mongo_db.get_collection("users")
        self.category_embedding_service = CategoryEmbeddingService()
        self.redis_cache = redis_cache

    def log_interest(self, email: str, interests: List[Interest]):
        user_data = self.user_collection.find_one({"email": email})

        if user_data:
            self.user_collection.update_one(
                {"email": email},
                {"$set": {"interests": [interest.dict() for interest in interests]}}
            )
        else:
            new_user = User(email=email, interests=interests)
            self.user_collection.insert_one(new_user.dict(by_alias=True))

        logger.info(f"Logged interest for user: {email}")

    
    def compute_user_embedding(self, email: str) -> List[float]:
        redis_interest_key = f"user:{email}:interest"
        cached_interest = (self.redis_cache.get_cache(redis_interest_key) or {}).get("data")
    
        if cached_interest:
            user_interests = cached_interest
        else:
            user_data = self.user_collection.find_one({"email": email}, {"interests": 1})
            if not user_data:
                raise HTTPException(status_code=404, detail="User not found")
            user_interests = user_data.get("interests", [])
            self.redis_cache.set_cache(redis_interest_key, user_interests, expiry=3600)
        
        category_embeddings = self.category_embedding_service.get_all_embeddings()
        if not category_embeddings:
            raise HTTPException(status_code=500, detail="Category embeddings not available")

        embedding_dim = len(next(iter(category_embeddings.values())))
        final_embedding = np.zeros(embedding_dim)

        if not user_interests:
            num_categories = len(category_embeddings)
            for emb in category_embeddings.values():
                final_embedding += np.array(emb)
            final_embedding /= num_categories
            return final_embedding.tolist()

        for interest in user_interests:
            category = interest["topic"]
            weight = interest["weight"]
            if category in category_embeddings:
                final_embedding += np.array(category_embeddings[category]) * weight

        return final_embedding.tolist()
    
    def process_interest_update(self, event: Dict):
        try:
            email = event.get("email")
            new_interest = event.get("updatedInterest", [])

            if not email or not new_interest:
                logger.info("Invalid event data: Missing userId or userInterest.")
                raise ValueError("Invalid event data")
                
            redis_interest_key = f"user:{email}:interest"
            
            cached_interest = (redis_cache.get_cache(redis_interest_key)or {}).get("data")

            if cached_interest:
                previous_interest = cached_interest
            else:
                user_data = self.user_collection.find_one({"email": email}, {"interests": 1})
                previous_interest = user_data.get("interests", []) if user_data else []

            if not isinstance(previous_interest, list):
                previous_interest = []
            prev_interest_dict = {
                item["topic"]: item["weight"]
                for item in previous_interest
                if isinstance(item, dict) and "topic" in item and "weight" in item
            }
            
            new_interest_dict = {
                item["topic"]: item["weight"]
                for item in new_interest
                if isinstance(item, dict) and "topic" in item and "weight" in item
            }
            
            final_interest = defaultdict(float)
            weight_previous = 0.7
            weight_new = 0.3
            
            for topic, wt in prev_interest_dict.items():
                final_interest[topic] += wt * weight_previous

            for topic, wt in new_interest_dict.items():
                final_interest[topic] += wt * weight_new

            total_weight = sum(final_interest.values())
            if total_weight > 0:
                for topic in final_interest:
                    final_interest[topic] /= total_weight

            updated_interest = [{"topic": topic, "weight": weight} for topic, weight in final_interest.items()]
            
            redis_cache.set_cache(redis_interest_key, updated_interest, expiry=3600)
            logger.info(f"User {email} interest updated successfully in Redis.")

        except Exception as e:
            logger.error(f"Error processing interest update: {e}", exc_info=True)
    
    def get_user_id(self,email: str):
        redis_key = f"user:{email}"
        cached_user = (self.redis_cache.get_cache(redis_key)or {}).get("data")
        
        if cached_user:
            return cached_user["userId"]
        
        raise HTTPException(status_code=401, detail="User not Authorized")
    
user_service = UserInterestService()