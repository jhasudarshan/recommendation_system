from datetime import datetime, timezone
from pymongo import UpdateOne
from bson import ObjectId
from threading import Lock
from app.config.logger_config import logger
from app.config.config import KAFKA_INTERACTION_UPDATE
from app.services.content_serve import content_service
from app.event.kafka_service import content_kafka_service
from app.event.kafka_producer import kafka_event_producer

class FeedbackProcessor:
    def __init__(self):
        self.content_service = content_service
        self.kafka_service = content_kafka_service
        self.feedback_producer = kafka_event_producer
        self.lock = Lock()

    def process_metadata_update(self, event):
        try:
            articles = event.get("articles", [])
            email = event.get("email")
            print(event)
            if not email or not articles:
                logger.warning("Invalid interaction update event: missing email or articles")
                return
            
            logger.info(f"Received metadata update for {len(articles)} articles.")

            with self.lock:
                bulk_updates = []
                article_ids = []
                kafka_interaction_payload = []
                
                for article in articles:
                    article_id = article["id"]
                    interaction = article["interaction"]
                    
                    
                    try:
                        article_id = ObjectId(article_id)
                    except Exception:
                        pass
                    
                    article_ids.append(article_id)
                    update_query = {
                        "$inc": {
                            "interactionMetrics.likes": interaction.get("likes", 0),
                            "interactionMetrics.shares": interaction.get("shares", 0),
                            "interactionMetrics.clicks": interaction.get("clicks", 0)
                        },
                        "$set": {"updated_at": datetime.now(timezone.utc)}
                    }
                    
                    bulk_updates.append(UpdateOne({"_id": article_id}, update_query))
                    
                    kafka_entry = {
                        "articleId" : str(article_id),
                        "like": interaction.get("likes", 0) > 0,
                        "share": interaction.get("shares",0),
                        "viewedAt": datetime.now(timezone.utc).isoformat()
                    }
                    
                    kafka_interaction_payload.append(kafka_entry)
                    
                if bulk_updates:
                    result = self.content_service.bulkUpdate(bulk_updates)
                    logger.info(f"Matched: {result.matched_count}, Modified: {result.modified_count}")
                    
                logger.info("Sending interaction update to user-service via Kafka.")
                self.feedback_producer.send(KAFKA_INTERACTION_UPDATE, {
                    "email": email,
                    "interactions": kafka_interaction_payload
                })
                
                logger.info("Calling post-processing compute pipeline.")
                self.kafka_service.batch_compute_and_trigger_updates(article_ids, email)

        except Exception as e:
            logger.error(f"Error processing metadata update: {e}", exc_info=True)
            
feedback_log_service = FeedbackProcessor()