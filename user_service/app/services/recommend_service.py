from app.db.mongo import mongo_db
from app.db.qdrant import qdrant_db
from app.config.logger_config import logger
from app.services.user import user_service
import uuid

class RecommendService:
    def __init__(self):
        self.content_collection = mongo_db.get_collection("content")

    def get_recommendations(self, email: str, top_k: int = 30):
        user_embedding = user_service.compute_user_embedding(email)
        if not user_embedding:
            logger.warning(f"No embedding found for user: {email}")
            return {"message": "No embedding found for user.", "recommendations": []}

        search_results = qdrant_db.search_vector("content_embeddings", user_embedding, top_k)

        recommended_content = []
        content_id_map = {
            str(uuid.uuid5(uuid.NAMESPACE_DNS, str(content["_id"]))): content["_id"]
            for content in self.content_collection.find({}, {"_id": 1})
        }

        for result in search_results:
            content_uuid = result.id
            content_id = content_id_map.get(content_uuid)

            if content_id:
                content_data = self.content_collection.find_one({"_id": content_id})
                if content_data:
                    content_data["_id"] = str(content_data["_id"])
                    content_data["score"] = result.score
                    recommended_content.append(content_data)

        recommended_content.sort(key=lambda x: x["score"], reverse=True)

        logger.info(f"Retrieved {len(recommended_content)} recommendations for user: {email}")
        return {"message": "Recommendations fetched successfully.", "recommendations": recommended_content}

    
recommend_service = RecommendService()