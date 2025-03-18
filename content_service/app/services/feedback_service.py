import logging
from datetime import datetime, timezone
from pymongo import UpdateOne
from bson import ObjectId
from threading import Lock
from services.content_serve import content_service
from event.kafka_service import content_kafka_service

class FeedbackProcessor:
    def __init__(self):
        self.content_service = content_service
        self.kafka_service = content_kafka_service
        self.lock = Lock()

    def process_metadata_update(self, event):
        try:
            articles = event.get("articles", [])
            user_id = event.get("user_id")
            print(event)
            if not user_id:
                logging.info("No UserId received for interaction change")
                return
            if not articles:
                logging.info("No articles received for metadata update.")
                return
            
            logging.info(f"Received metadata update for {len(articles)} articles.")

            with self.lock:
                bulk_updates = []
                article_ids = []

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

                if bulk_updates:
                    result = self.content_service.bulkUpdate(bulk_updates)
                    logging.info(f"Matched: {result.matched_count}, Modified: {result.modified_count}")
                print("batched and compute call happend")
                self.kafka_service.batch_compute_and_trigger_updates(article_ids, user_id)

        except Exception as e:
            logging.error(f"Error processing metadata update: {e}", exc_info=True)
            
feedback_log_service = FeedbackProcessor()