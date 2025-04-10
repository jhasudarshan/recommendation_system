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
import os

class ContentClassifier:
    def __init__(self, model_name: str, classification_type: str, confidence_threshold: float = 0.7):
        hf_cache_dir = os.getenv("HF_HOME", "/content_service/hf_cache")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name,cache_dir=hf_cache_dir)
        model = AutoModelForSequenceClassification.from_pretrained(model_name,cache_dir=hf_cache_dir)

        # Dynamic Quantization for CPU optimization
        self.model = torch.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )
    
        self.model.eval()  # VERY IMPORTANT
        self.model.to("cpu")
        self.confidence_threshold = confidence_threshold

        self.categories = [
            "Gaming", "Finance", "Business", "Healthcare", "Science", "Education", "Psychology",
            "Marketing", "Politics", "Entertainment", "Sports", "Travel", "Sustainability", "Technology"
        ]

    def classify(self, texts: List[str]) -> List[dict]:
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="pt"
        )

        with torch.no_grad():
            outputs = self.model(**inputs)

        logits = outputs.logits
        probs = torch.sigmoid(logits).cpu().numpy()  # multi-label scenario

        results = []
        for prob in probs:
            scores = prob.tolist()
            label_score_pairs = sorted(
                zip(self.categories, scores), 
                key=lambda x: x[1], 
                reverse=True
            )

            labels = [label for label, score in label_score_pairs if score >= self.confidence_threshold]


            if not labels:
                labels.append(label_score_pairs[0][0])

            result = {
                "labels": [label for label, _ in label_score_pairs],
                "scores": [score for _, score in label_score_pairs]
            }

            results.append(result)

        return results

class ClassifyWorker:
    def __init__(self, content_collection, classifier: ContentClassifier):
        self.buffer = []
        self.buffer_lock = threading.Lock()
        self.flush_interval = 10
        self.batch_size = 50
        self.collection = content_collection
        self.classifier = classifier
        self.content_kafka_service = content_kafka_service
        self.executor = ThreadPoolExecutor(max_workers=2)

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
        if not buffer:
            logger.info("Empty buffer received, skipping classify_and_update.")
            return

        try:
            start_time = time.perf_counter()
            logger.info(f"Starting classify_and_update for {len(buffer)} items")
            
            texts = [f"{item['title']}. {item['desc']}" for item in buffer]
            batch_size = 4
            batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
            
            results = []
            """memory-load increases this thing can be used to speedup the process"""
            futures = [self.executor.submit(self.classifier.classify, batch) for batch in batches]
            for idx, future in enumerate(futures, start=1):
                res = future.result()
                logger.info(f"Batch {idx} processed")
                results.extend(res)
            
            # for idx, batch in enumerate(batches, start=1):
            #     result = self.classifier.classify(batch)  # Sequential processing
            #     results.extend(result)
            #     logger.info(f"Batch {idx}/{len(batches)} processed")
            
            operations = []
            batch_updates = []

            for item, result in zip(buffer, results):
                category = result["labels"][0]
                tags = result["labels"][1:]

                operations.append(UpdateOne(
                    {"_id": ObjectId(item["id"])},
                    {"$set": {"category": category, "tags": tags}}
                ))

                batch_updates.append({
                    "id": str(item["id"]),
                    "category": category,
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