import threading
from kafka import KafkaConsumer
import json
import logging

class KafkaEventConsumer:
    def __init__(self, topic: str, group_id: str, auto_offset_reset="earliest"):
        self.topic = topic
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset

    def _create_consumer(self):
        return KafkaConsumer(
            self.topic,
            bootstrap_servers="localhost:9092",
            auto_offset_reset=self.auto_offset_reset,
            enable_auto_commit=True,
            group_id=self.group_id,
            value_deserializer=lambda x: json.loads(x.decode("utf-8"))
        )

    def listen(self, callback):
        def _consume():
            consumer = self._create_consumer()
            logging.info(f"Kafka Consumer started listening on topic: {self.topic}")
            try:
                for message in consumer:
                    logging.info(f"Message received from '{message.topic}': {message.value}")
                    callback(message.value)
            except Exception as e:
                logging.error(f"Kafka Consumer Error: {e}")


        threading.Thread(target=_consume, daemon=True).start()