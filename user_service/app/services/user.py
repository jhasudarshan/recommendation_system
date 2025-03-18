from fastapi import APIRouter, HTTPException
from db.mongo import mongo_db
from models.mongo_model import User, Interest
from services.generate_embedding import CategoryEmbeddingService
from typing import List
import numpy as np
import logging

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
    
user_service = UserInterestService()