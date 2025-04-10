from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
import torch
from typing import List, Tuple
from pymongo import UpdateOne
from bson import ObjectId
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from app.db.mongo import mongo_db
from app.config.config import CLASSIFIER_MODEL,CLASSIFICATION,CONTENT_CLASSIFY_TOPIC,CONTENT_CLASSIFY_GROUP
from app.event.kafka_consumer import KafkaEventConsumer
from app.config.logger_config import logger
from app.event.kafka_service import content_kafka_service

class ContentClassifier:
    def __init__(self, model_name: str, classification_type: str, confidence_threshold: float = 0.7):
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)

        # Dynamic Quantization for CPU optimization
        quantized_model = torch.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )

        self.classifier = pipeline(
            classification_type,
            model=quantized_model,
            tokenizer=tokenizer,
            device=-1
        )

        self.confidence_threshold = confidence_threshold
        self.categories = [
            "Gaming", "Finance", "Business", "Healthcare", "Science", "Education", "Psychology",
            "Marketing", "Politics", "Entertainment", "Sports", "Travel", "Sustainability", "Technology"
        ]

    def classify(self, texts: List[str]) -> List[dict]:
        return self.classifier(texts,self.categories, multi_label=True)

class ClassifyWorker:
    def __init__(self, content_collection, classifier: ContentClassifier):
        self.buffer = []
        self.buffer_lock = threading.Lock()
        self.flush_interval = 10
        self.batch_size = 50
        self.collection = content_collection
        self.classifier = classifier
        self.content_kafka_service = content_kafka_service
        self.executor = ThreadPoolExecutor(max_workers=4)

    def add_to_buffer(self, item):
        with self.buffer_lock:
            self.buffer.append(item)
            if len(self.buffer) >= self.batch_size:
                self.flush()

    def flush(self):
        with self.buffer_lock:
            if not self.buffer:
                return
            buffer_copy = self.buffer.copy()
            self.buffer.clear()

        threading.Thread(target=self.classify_and_update, args=(buffer_copy,), daemon=True).start()

    def classify_and_update(self, buffer):
        try:
            start_time = time.perf_counter()

            logger.info(f"Starting classify_and_update for {len(buffer)} items")
            texts = [f"{item['title']}. {item['desc']}" for item in buffer]
            batch_size = 8
            
            batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
            logger.info(f"Submitting {len(batches)} batches to thread pool")
            
            results = []
            futures = [self.executor.submit(self.classifier.classify, batch) for batch in batches]
            for idx, future in enumerate(futures, start=1):
                res = future.result()
                logger.info(f"Batch {idx} processed")
                results.extend(res)
            
            operations = []
            batch_updates = []

            for item, result in zip(buffer, results):
                top_label = result["labels"][0]

                tags = [
                    label for label, score in zip(result["labels"][1:], result["scores"][1:])
                    if score >= self.classifier.confidence_threshold
                ]

                operations.append(UpdateOne(
                    {"_id": ObjectId(item["id"])},
                    {"$set": {"category": top_label, "tags": tags}}
                ))

                batch_updates.append({
                    "id": str(item["id"]),
                    "category": top_label,
                    "tags": tags
                })

            if operations:
                logger.info(f"Updating {len(operations)} items in DB")
                self.collection.bulk_write(operations)
                self.content_kafka_service.trigger_batch_embedding_update(batch_updates)


            end_time = time.perf_counter()
            logger.info(f"classify_and_update completed for {len(buffer)} items in {end_time - start_time:.2f} seconds")

        except Exception as e:
            logger.error(f"Error during classify_and_update: {str(e)}", exc_info=True)

class ContentKafkaListener:
    def __init__(self):
        self.content_collection = mongo_db.get_collection("content")

        self.classifier = ContentClassifier(CLASSIFIER_MODEL, CLASSIFICATION)
        self.classify_worker = ClassifyWorker(self.content_collection, self.classifier)

        self.content_consumer = KafkaEventConsumer(
            topic=CONTENT_CLASSIFY_TOPIC,
            group_id=CONTENT_CLASSIFY_GROUP
        )

    def start_listeners(self):
        logger.info("Starting Kafka listener for content classification")
        
        listener_thread = threading.Thread(target=self.content_listener, daemon=True)
        listener_thread.start()

        flush_thread = threading.Thread(target=self.periodic_flush, daemon=True)
        flush_thread.start()

    def content_listener(self):
        self.content_consumer.listen(self.process_content)

    def process_content(self, data):
        self.classify_worker.add_to_buffer(data)

    def periodic_flush(self):
        while True:
            time.sleep(self.classify_worker.flush_interval)
            self.classify_worker.flush()