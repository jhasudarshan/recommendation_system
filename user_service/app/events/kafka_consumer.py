import threading
from kafka import KafkaConsumer
import json
import logging
from app.config.config import KAFKA_BROKER

class KafkaEventConsumer:
    def __init__(self, topic: str, group_id: str, auto_offset_reset="latest"):
        self.topic = topic
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset

    def safe_deserializer(self, x):
        try:
            return json.loads(x.decode("utf-8")) if x else None
        except json.JSONDecodeError:
            logging.error("Received invalid JSON message")
            return None

    def _create_consumer(self):
        try:
            return KafkaConsumer(
                self.topic,
                bootstrap_servers=KAFKA_BROKER,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=False,
                group_id=self.group_id,
                value_deserializer=self.safe_deserializer
            )
        except Exception as e:
            logging.error(f"Error creating Kafka Consumer: {e}")
            return None

    def listen(self, callback):
        def _consume():
            consumer = self._create_consumer()
            if not consumer:
                logging.error("Kafka Consumer failed to initialize. Exiting thread.")
                return
            logging.info(f"Kafka Consumer started listening on topic: {self.topic}")
            try:
                for message in consumer:
                    data = message.value
                    if data is None:
                        logging.warning(f"Skipping empty or invalid message from {message.topic}")
                        continue
                    logging.info(f"Message received from '{message.topic}': {message.value}")
                    callback(data)
                consumer.commit()
            except Exception as e:
                logging.error(f"Kafka Consumer Error: {e}")
                consumer.close()
                self.listen(callback)

        
        threading.Thread(target=_consume, daemon=True).start()