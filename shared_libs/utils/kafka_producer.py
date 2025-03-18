from kafka import KafkaProducer
import json
import logging
from utils.kafka_config import KAFKA_BROKER

class KafkaEventProducer:
    def __init__(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers="localhost:9092",
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                retries=5
            )
            logging.info("Kafka Producer connected successfully.")
        except Exception as e:
            logging.error(f"Kafka Producer Connection Error: {e}")
            self.producer = None

    def send(self, topic, message):
        if not self.producer:
            logging.error("Kafka Producer is not connected. Message not sent.")
            return

        try:
            future = self.producer.send(topic, message)
            future.get(timeout=10)
            logging.info(f"Message sent to '{topic}': {message}")
        except Exception as e:
            logging.error(f"Error sending message to '{topic}': {e}")