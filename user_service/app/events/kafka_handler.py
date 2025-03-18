import threading
import logging
from shared_libs.utils.kafka_consumer import KafkaEventConsumer
from db.qdrant import qdrant_db
from services.generate_embedding import embedding_service
import uuid
from services.user import user_service

class UserServiceKafkaHandler:
    def __init__(self):
        self.embedding_service = embedding_service 
        self.user_service = user_service
        self.embedding_update_consumer = KafkaEventConsumer(
            topic="embedding_update_required",
            group_id="user-service-group-1"
        )
        self.interest_update_consumer = KafkaEventConsumer(
            topic="balance_user_interest",
            group_id="user-service-group-2"
        )

    def start_listeners(self):
        logging.info("Starting Kafka listener for embedding_update_required")
        listener_thread1 = threading.Thread(target=self.embedding_listener, daemon=True)
        listener_thread1.start()
        
        listener_thread2 = threading.Thread(target=self.interest_balance_listener,daemon=True)
        listener_thread2.start()

    def embedding_listener(self):
        self.embedding_update_consumer.listen(self.process_embedding_update)
    
    def interest_balance_listener(self):
        self.interest_update_consumer.listen(self.user_service.process_interest_update)
        
    def process_embedding_update(self, event):
        try:
            filtered_articles = event.get("filtered_articles", [])
            print("filtered_article: ",filtered_articles)
            if not filtered_articles:
                logging.info("No articles received for embedding update.")
                return

            logging.info(f"Processing embedding update for {len(filtered_articles)} articles.")

            existing_vector_ids = qdrant_db.get_all_vector_ids("content_embeddings")
            print("existing ",existing_vector_ids)
            existing_set = set(existing_vector_ids)

            new_articles = []
            current_ids = set()

            for article in filtered_articles:
                article_id = str(article.get("id"))
                if not article_id:
                    logging.warning("Skipping article with missing ID.")
                    continue  

                try:
                    qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, article_id))
                except ValueError:
                    logging.error(f"Invalid article_id format: {article_id}")
                    continue  

                current_ids.add(qdrant_id)

                category_embedding = self.embedding_service.get_embedding(article.get("category", ""))
                if category_embedding is None:
                    logging.warning(f"No embedding found for category '{article.get('category', '')}', using zero vector.")
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
                new_articles.append({"id": qdrant_id, "vector": updated_embedding})

            if new_articles:
                qdrant_db.upsert_vectors("content_embeddings", new_articles)
                print(f"Upserted {len(new_articles)} new embeddings to Qdrant.")

            print("Qdrant embeddings updated successfully.")

        except Exception as e:
            logging.error(f"Error processing embedding update: {e}", exc_info=True)


user_service_kafka = UserServiceKafkaHandler()
user_service_kafka.start_listeners()