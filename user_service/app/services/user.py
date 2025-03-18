from fastapi import APIRouter, HTTPException
from db.mongo import mongo_db
from models.mongo_model import User, Interest
from services.generate_embedding import CategoryEmbeddingService
from typing import List,Dict
import numpy as np
import logging
from collections import defaultdict
from bson import ObjectId

router = APIRouter()

class UserInterestService:
    def __init__(self):
        self.user_collection = mongo_db.get_collection("users")
        self.category_embedding_service = CategoryEmbeddingService()

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

        logging.info(f"Logged interest for user: {email}")

    
    def compute_user_embedding(self, email: str) -> List[float]:
        user_data = self.user_collection.find_one({"email": email})

        if not user_data or "interests" not in user_data:
            raise HTTPException(status_code=404, detail="User not found or has no interests")

        user_interests = user_data["interests"]
        category_embeddings = self.category_embedding_service.get_all_embeddings()

        if not category_embeddings:
            raise HTTPException(status_code=500, detail="Category embeddings not available")

        embedding_dim = len(next(iter(category_embeddings.values())))
        final_embedding = np.zeros(embedding_dim)

        for interest in user_interests:
            category = interest["topic"]
            weight = interest["weight"]
            if category in category_embeddings:
                final_embedding += np.array(category_embeddings[category]) * weight

        return final_embedding.tolist()
    
    def process_interest_update(self, event: Dict):
        try:
            user_id = event.get("userId")
            user_id = ObjectId(user_id) 
            new_interest = event.get("updatedInterest", [])

            if not user_id or not new_interest:
                logging.info("Invalid event data: Missing userId or userInterest.")
                return
            
            # Fetch previous interest from MongoDB
            user_data = self.user_collection.find_one({"_id": user_id}, {"interests": 1})
            print(user_data)
            previous_interest = user_data.get("interests", []) if user_data else []

            # Convert interests into a dict for easier merging
            prev_interest_dict = {item["topic"]: item["weight"] for item in previous_interest}
            new_interest_dict = {item["topic"]: item["weight"] for item in new_interest}

            # Merge interests (normalize and balance short-term vs long-term)
            final_interest = defaultdict(float)
            weight_previous = 0.7  # Long-term weight
            weight_new = 0.3  # Short-term weight
            
            for topic, wt in prev_interest_dict.items():
                final_interest[topic] += wt * weight_previous

            for topic, wt in new_interest_dict.items():
                final_interest[topic] += wt * weight_new

            # Normalize final interest
            total_weight = sum(final_interest.values())
            if total_weight > 0:
                for topic in final_interest:
                    final_interest[topic] /= total_weight

            # Convert final interest back to list format
            updated_interest = [{"topic": topic, "weight": weight} for topic, weight in final_interest.items()]
            
            # Update user interests in MongoDB
            self.user_collection.update_one({"_id": user_id}, {"$set": {"interests": updated_interest}})
            user_data = self.user_collection.find_one({"_id": user_id})
            logging.info(f"User {user_id} interest updated successfully.")

        except Exception as e:
            logging.error(f"Error processing interest update: {e}", exc_info=True)
    
user_service = UserInterestService()