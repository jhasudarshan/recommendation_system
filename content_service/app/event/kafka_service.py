import threading
import time
from shared_libs.utils.kafka_producer import KafkaEventProducer
import logging
from services.content_serve import content_service
from collections import defaultdict

class ContentServiceKafkaHandler:
    def __init__(self):
        self.content_service = content_service
        self.embedding_update_producer = KafkaEventProducer()
        self.article_engagement_scores = {}
        self.lock = threading.Lock()

    def batch_compute_and_trigger_updates(self, article_ids,userId):
        if not article_ids:
            logging.info("No article IDs provided. Skipping batch processing.")
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
        if not articles_scores:
            logging.info("No articles found for the given IDs.")
            return
        
        logging.info("Computing user interest from engagement data...")
        self.compute_user_interest(userId, articles_scores)
        
        print("article_scores",articles_scores)
        batch_updates = []
        now = time.time()

        for score_data in articles_scores:
            article_id = str(score_data["_id"])
            new_score = score_data["engagement_score"]

            last_score,last_update_time = self.article_engagement_scores.get(article_id, (0, 0))
            score_change = (new_score - last_score) / max(1, last_score)  if last_score > 0 else new_score

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
        print("trigeered embedding update happen")
        self.embedding_update_producer.send("embedding_update_required",event_data)
        logging.info(f"Triggered embedding update for {len(batch_updates)} articles.")
        
    def compute_user_interest(self,user_id, articles):
        category_weights = defaultdict(float)
        category_counts = defaultdict(int)
        
        # Accumulate weights and counts
        for article in articles:
            category = article.get("category", "Unknown")
            tags = article.get("tags", [])
            
            # Assign weights (category gets a higher weight, tags get lower weight)
            category_weights[category] += 0.6
            category_counts[category] += 1
            
            for tag in tags:
                category_weights[tag] += 0.4
                category_counts[tag] += 1
        
        # Normalize weights based on category counts
        for topic in category_weights:
            if category_counts[topic] > 0:
                category_weights[topic] /= category_counts[topic]
        
        user_interest = [{"topic": topic, "weight": weight} for topic, weight in category_weights.items()]
        
        interest_payload = {
            "userId": user_id,
            "updatedInterest": user_interest
        }
        print("Producer user_interest produced happend")
        self.embedding_update_producer.send("balance_user_interest",interest_payload)

content_kafka_service = ContentServiceKafkaHandler()