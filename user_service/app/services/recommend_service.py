from app.db.mongo import mongo_db
from app.db.qdrant import qdrant_db
from app.config.logger_config import logger
from app.services.user import user_service
from bson import ObjectId
from datetime import datetime, timedelta,timezone
from pymongo import UpdateOne

class RecommendService:
    def __init__(self):
        self.content_collection = mongo_db.get_collection("content")
        self.interaction_collection = mongo_db.get_collection("interaction")

    def get_recommendations(self, email: str, top_k: int = 30):
        user_embedding = user_service.compute_user_embedding(email)
        if not user_embedding:
            logger.warning(f"No embedding found for user: {email}")
            return {"message": "No embedding found for user.", "recommendations": []}

        search_results = qdrant_db.search_vector("content_embeddings", user_embedding, top_k)

        matched_ids = []
        article_ids = []
        qdrant_score_map = {}

        for result in search_results:
            try:
                mongo_id  = result.payload.get("mongo_id")
                if mongo_id:
                    article_ids.append(mongo_id)
                    matched_ids.append(ObjectId(mongo_id))
                    qdrant_score_map[mongo_id] = result.score
            except Exception as e:
                logger.warning(f"Invalid ObjectId from Qdrant result: {result.id} — {e}")

        if not matched_ids:
            return {"message": "No matched content found.", "recommendations": []}

        articles = list(self.content_collection.find(
            {"_id": {"$in": matched_ids}},
            {"interactionMetrics": 0}
        ))

        user_id = user_service.get_user_id(email)
        recently_viewed_ids,liked_map = self.batch_interaction_filter(user_id, article_ids)

        recommended_content = []

        for article in articles:
            mongo_id = str(article["_id"])
            if mongo_id in recently_viewed_ids:
                continue 
            article.update({
                "_id": mongo_id,
                "score": qdrant_score_map.get(mongo_id, 0.0),
                "liked": liked_map.get(mongo_id, False)
            })

            recommended_content.append(article)

        recommended_content.sort(key=lambda x: x["score"], reverse=True)

        logger.info(f"Retrieved {len(recommended_content)} recommendations for user: {email}")
        return {
            "message": "Recommendations fetched successfully.",
            "recommendations": recommended_content
        }
        
    def batch_interaction_filter(self,user_id: str, article_ids: list):
        recently_viewed_ids = set()
        liked_map = {}
        recent_view_threshold = datetime.now(timezone.utc) - timedelta(days=2)
        
        interactions = self.interaction_collection.find({
            "userId": user_id,
            "articleId": {"$in": article_ids},
            "$or": [
                {"action.like": True},
                {"action.view": {"$gte": recent_view_threshold}}
            ]
        })

        for interaction in interactions:
            article_id = str(interaction["articleId"])
            action = interaction.get("action", {})

            if action.get("like", False):
                liked_map[article_id] = True

            view_time = action.get("view")
            if view_time:
                if view_time.tzinfo is None:
                    view_time = view_time.replace(tzinfo=timezone.utc)
                if view_time >= recent_view_threshold:
                    recently_viewed_ids.add(article_id)
        
        return recently_viewed_ids, liked_map
    
    def process_user_interaction_update(self, event):
        try:
            interactions = event.get("interactions", [])
            email = event.get("email")

            if not email or not interactions:
                logger.warning("Invalid interaction update event: missing email or interactions")
                return

            logger.info(f"Processing {len(interactions)} user interaction updates for {email}")
            user_id = user_service.get_user_id(email)

            bulk_updates = []
            article_ids = []

            for interaction in interactions:
                article_id = ObjectId(interaction.get("articleId"))

                article_ids.append(article_id)

                update_fields = {}
                inc_fields = {}

                if interaction.get("like") is not None:
                    update_fields["action.like"] = interaction["like"]

                if interaction.get("share"):
                    inc_fields["action.share"] = interaction["share"]

                if interaction.get("viewedAt"):
                    try:
                        update_fields["action.view"] = datetime.fromisoformat(interaction["viewedAt"])
                    except ValueError as ve:
                        logger.warning(f"Invalid date format for viewedAt: {interaction['viewedAt']}. Error: {ve}")
                        update_fields["action.view"] = datetime.now(timezone.utc)

                elif interaction.get("view", False):
                    update_fields["action.view"] = datetime.now(timezone.utc)


                update_query = {
                    "$setOnInsert": {"userId": user_id, "articleId": str(article_id)},
                    "$set": update_fields,
                    "$inc": inc_fields
                }

                bulk_updates.append(UpdateOne(
                    {"userId": user_id, "articleId": str(article_id)},
                    update_query,
                    upsert=True
                ))

            if bulk_updates:
                result = self.interaction_collection.bulk_write(bulk_updates)
                logger.info(f"User interaction bulk updated: Matched={result.matched_count}, Upserts={result.upserted_count}")

        except Exception as e:
            logger.error(f"Error processing user interaction update: {e}", exc_info=True)
    
recommend_service = RecommendService()