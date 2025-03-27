from kafka import KafkaProducer
import json
from app.config.logger_config import logger
from  app.config.config import KAFKA_BROKER

class KafkaEventProducer:
    def __init__(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                retries=5
            )
            logger.info("Kafka Producer connected successfully.")
        except Exception as e:
            logger.error(f"Kafka Producer Connection Error: {e}")
            self.producer = None

    def send(self, topic, message):
        if not self.producer:
            logger.error("Kafka Producer is not connected. Message not sent.")
            return

        try:
            future = self.producer.send(topic, message)
            future.get(timeout=10)
            logger.info(f"Message sent to '{topic}': {message}")
            self.producer.flush()
        except Exception as e:
            logger.error(f"Error sending message to '{topic}': {e}")
            
kafka_event_producer = KafkaEventProducer()