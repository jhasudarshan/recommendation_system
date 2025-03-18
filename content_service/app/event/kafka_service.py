import threading
import time
# import sys
# import os
# # ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
# # sys.path.insert(0, ROOT_DIR)
from shared_libs.utils.kafka_producer import KafkaEventProducer
from shared_libs.utils.kafka_consumer import KafkaEventConsumer
import logging
from datetime import datetime, timezone
from pymongo import UpdateOne
from services.content_serve import content_service
from bson import ObjectId

class ContentServiceKafkaHandler:
    def __init__(self):
        self.content_service = content_service

        self.interaction_consumer = KafkaEventConsumer(topic="metadata_update", group_id="content-service-group")

        self.embedding_update_producer = KafkaEventProducer()

        self.article_engagement_scores = {}
        self.lock = threading.Lock()

        
    def start_listeners(self):
        logging.info("Starting Kafka listener for embedding_update_required")
        listener_thread = threading.Thread(target=self.listen, daemon=True)
        listener_thread.start()

    def listen(self):
        self.interaction_consumer.listen(self.process_metadata_update)

    def process_metadata_update(self, event):
        try:
            articles = event.get("articles", [])
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
                self.batch_compute_and_trigger_updates(article_ids)

        except Exception as e:
            logging.error(f"Error processing metadata update: {e}", exc_info=True)

    def batch_compute_and_trigger_updates(self, article_ids):
        if not article_ids:
            return
        logging.info("batch computing checking: ")
        pipeline = [
            {"$match": {"_id": {"$in": article_ids}}},
            {"$project": {
                "_id": 1,
                "interactionMetrics": 1,
                "category": 1,
                "tags": 1,
                "engagement_score": {
                    "$sum": [
                        {"$multiply": ["$interactionMetrics.likes", 0.4]},
                        {"$multiply": ["$interactionMetrics.shares", 0.3]},
                        {"$multiply": ["$interactionMetrics.clicks", 0.3]}
                    ]
                }
            }}
        ]
        articles_scores = self.content_service.aggregation(pipeline)
        print("article_scores",articles_scores)
        batch_updates = []
        now = time.time()

        for score_data in articles_scores:
            article_id = str(score_data["_id"])
            new_score = score_data["engagement_score"]

            last_score, last_update_time = self.article_engagement_scores.get(article_id, (0, 0))
            score_change = (new_score - last_score) / max(1, last_score)

            if score_change > 0.3:
                batch_updates.append({
                    "id": article_id,
                    "category": score_data.get("category", ""),
                    "tags": score_data.get("tags", [])
                })
                self.article_engagement_scores[article_id] = (new_score, now)

        if batch_updates:
            self.trigger_batch_embedding_update(batch_updates)

    def trigger_batch_embedding_update(self, batch_updates):
        event_data = {"filtered_articles": batch_updates}
        self.embedding_update_producer.send("embedding_update_required",event_data)
        logging.info(f"Triggered embedding update for {len(batch_updates)} articles.")


content_kafka_service = ContentServiceKafkaHandler()
content_kafka_service.start_listeners()