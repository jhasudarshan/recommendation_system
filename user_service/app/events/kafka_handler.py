import threading
import uuid
from app.config.logger_config import logger
from app.events.kafka_consumer import KafkaEventConsumer
from app.db.qdrant import qdrant_db
from app.services.generate_embedding import embedding_service
from app.services.user import user_service
from app.services.recommend_service import recommend_service
from app.config.config import KAFKA_EMBEDDING_UPDATE_TOPIC,KAFKA_BALANCE_INTEREST_TOPIC,EMBEDDING_UPDATE,INTEREST_UPDATE_GROUP,KAFKA_INTERACTION_UPDATE,INTERACTION_UPDATE_GROUP

class UserServiceKafkaHandler:
    def __init__(self):
        self.embedding_service = embedding_service 
        self.user_service = user_service
        self.recommend_service = recommend_service
        
        self.embedding_update_consumer = KafkaEventConsumer(
            topic=KAFKA_EMBEDDING_UPDATE_TOPIC,
            group_id=EMBEDDING_UPDATE
        )
        
        self.interest_update_consumer = KafkaEventConsumer(
            topic=KAFKA_BALANCE_INTEREST_TOPIC,
            group_id=INTEREST_UPDATE_GROUP
        )
        
        self.interaction_update_consumer = KafkaEventConsumer(
            topic= KAFKA_INTERACTION_UPDATE,
            group_id = INTERACTION_UPDATE_GROUP
        )

    def start_listeners(self):
        logger.info("Starting Kafka listeners")
        threading.Thread(target=self.embedding_listener, daemon=True).start()
        threading.Thread(target=self.interest_balance_listener, daemon=True).start()
        threading.Thread(target=self.process_interaction_update, daemon=True).start()
        
    def embedding_listener(self):
        self.embedding_update_consumer.listen(self.process_embedding_update)
    
    def interest_balance_listener(self):
        self.interest_update_consumer.listen(self.user_service.process_interest_update)
        
    def process_interaction_update(self):
        self.interaction_update_consumer.listen(self.recommend_service.process_user_interaction_update)
        
    def process_embedding_update(self, event):
        try:
            filtered_articles = event.get("filtered_articles", [])
            if not filtered_articles:
                logger.info("No articles received for embedding update.")
                return

            logger.info(f"Processing embedding update for {len(filtered_articles)} articles.")

            new_articles = []

            for article in filtered_articles:
                article_id = str(article.get("id"))
                if not article_id:
                    logger.warning("Skipping article with missing ID.")
                    continue  

                try:
                    mongo_id = str(article_id)
                    qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, article_id))
                except ValueError:
                    logger.error(f"Invalid article_id format: {article_id}")
                    continue

                category_embedding = self.embedding_service.get_embedding(article.get("category", ""))
                if category_embedding is None:
                    logger.warning(f"No embedding found for category '{article.get('category', '')}', using zero vector.")
                    category_embedding = [0.0] * 14

                tag_embeddings = [
                    self.embedding_service.get_embedding(tag) or [0.0] * 14
                    for tag in article.get("tags", [])
                ]

                category_weight = 0.7
                tag_weight = 0.3 / max(len(tag_embeddings), 1)

                updated_embedding = [
                    category_weight * c + sum(tag_weight * t[i] for t in tag_embeddings)
                    for i, c in enumerate(category_embedding)
                ]

                interaction = article.get("interactionMetrics", {})
                interaction_factor = (
                    interaction.get("likes", 0) * 0.4 +
                    interaction.get("shares", 0) * 0.3 +
                    interaction.get("clicks", 0) * 0.3
                )
                updated_embedding = [e + interaction_factor for e in updated_embedding]
                new_articles.append({"id": qdrant_id, "vector": updated_embedding,"mongo_id": mongo_id})

            if new_articles:
                qdrant_db.upsert_vectors("content_embeddings", new_articles)
                logger.info(f"Upserted {len(new_articles)} new embeddings to Qdrant.")

            logger.info("Qdrant embeddings updated successfully.")

        except Exception as e:
            logger.error(f"Error processing embedding update: {e}", exc_info=True)


user_service_kafka = UserServiceKafkaHandler()
user_service_kafka.start_listeners()