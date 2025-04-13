from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer
import torch
from typing import List, Tuple,Dict
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
    def __init__(self, model_name: str, classification_type: str, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold

        self.categories = [
            "Gaming", "Finance", "Business", "Healthcare", "Science", "Education", "Psychology",
            "Marketing", "Politics", "Entertainment", "Sports", "Travel", "Sustainability", "Technology"
        ]
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model = torch.quantization.quantize_dynamic(
            self.model, {torch.nn.Linear}, dtype=torch.qint8
        )
        self.model = self.model.to("cpu")
        self.model.eval()
        self.device = "cpu"

    def classify(self, texts: List[str]) -> List[Dict]:
        total_start = time.perf_counter()
        results = []

        for idx, text in enumerate(texts):
            section_times = {}

            # Section 1: Hypothesis & Premise
            t0 = time.perf_counter()
            hypotheses = [f"This text is about {category}." for category in self.categories]
            premises = [text] * len(hypotheses)
            section_times["hypothesis"] = time.perf_counter() - t0

            # Section 2: Tokenization
            t1 = time.perf_counter()
            inputs = self.tokenizer(
                premises,
                hypotheses,
                return_tensors="pt",
                padding=True,
                truncation=True
            ).to(self.device)
            section_times["tokenize"] = time.perf_counter() - t1

            # Section 3: Inference
            t2 = time.perf_counter()
            with torch.no_grad():
                logits = self.model(**inputs).logits
            section_times["inference"] = time.perf_counter() - t2

            # Section 4: Score Computation
            t3 = time.perf_counter()
            entail_contra_logits = logits[:, [0, 2]]
            probs = torch.softmax(entail_contra_logits, dim=1)
            entailment_scores = probs[:, 1]
            section_times["compute_scores"] = time.perf_counter() - t3

            # Section 5: Filtering + Fallback
            t4 = time.perf_counter()
            label_scores = [
                {"label": category, "score": score.item()}
                for category, score in zip(self.categories, entailment_scores)
                if score.item() >= self.confidence_threshold
            ]

            if not label_scores:
                max_score_idx = torch.argmax(entailment_scores).item()
                label_scores = [{
                    "label": self.categories[max_score_idx],
                    "score": entailment_scores[max_score_idx].item()
                }]
            label_scores.sort(key=lambda x: x["score"], reverse=True)
            section_times["filter_fallback"] = time.perf_counter() - t4

            # Section 6: Format Results
            t5 = time.perf_counter()
            results.append({
                "sequence": text,
                "labels": [entry["label"] for entry in label_scores],
                "scores": [entry["score"] for entry in label_scores]
            })
            section_times["format"] = time.perf_counter() - t5

            logger.info(
                f"Text {idx + 1}/{len(texts)} processed. Times: "
                + ", ".join([f"{k}={v:.4f}s" for k, v in section_times.items()])
            )

        total_end = time.perf_counter()
        logger.info(f"classify() completed on {len(texts)} texts in {total_end - total_start:.2f} seconds")

        return results

    
    """Batch inference and classifying"""
    # def classify(self, texts: List[str]) -> List[Dict]:
    #     t0 = time.perf_counter()
    #     all_premises = []
    #     all_hypotheses = []
    #     index_map = []  # track which output goes to which text

    #     # Prepare flattened input for batch processing
    #     for idx, text in enumerate(texts):
    #         for label in self.categories:
    #             all_premises.append(text)
    #             all_hypotheses.append(f"This text is about {label}.")
    #             index_map.append(idx)  # keep track of original text index

    #     t1 = time.perf_counter()
    #     # Tokenize all at once
    #     inputs = self.tokenizer(
    #         all_premises,
    #         all_hypotheses,
    #         return_tensors="pt",
    #         padding=True,
    #         truncation=True,
    #         max_length=	512
    #     ).to(self.device)

    #     t2 = time.perf_counter()
    #     # Run inference in a single pass
    #     with torch.no_grad():
    #         logits = self.model(**inputs).logits

    #     t3 = time.perf_counter()
    #     entail_contra_logits = logits[:, [0, 2]]
    #     probs = torch.softmax(entail_contra_logits, dim=1)
    #     entailment_scores = probs[:, 1]  # score for "entailment"

    #     t4 = time.perf_counter()
    #     # Organize results per input text
    #     results_dict = {i: [] for i in range(len(texts))}

    #     for idx, label_idx in enumerate(index_map):
    #         score = entailment_scores[idx].item()
    #         label = self.categories[idx % len(self.categories)]
    #         if score >= self.confidence_threshold:
    #             results_dict[label_idx].append({"label": label, "score": score})

    #     t5 = time.perf_counter()
    #     # Sort results and format output
    #     final_results = []
    #     for i, text in enumerate(texts):
    #         label_scores = sorted(results_dict[i], key=lambda x: x["score"], reverse=True)
            
    #         if not label_scores:
    #             fallback_scores = [
    #                 (label, entailment_scores[j].item())
    #                 for j, (t_idx, label) in enumerate(zip(index_map, [self.categories[k % len(self.categories)] for k in range(len(entailment_scores))]))
    #                 if t_idx == i
    #             ]
    #             if fallback_scores:
    #                 best_label, best_score = max(fallback_scores, key=lambda x: x[1])
    #                 logger.warning(f"No confident label for: \"{text}\" — fallback to top label: {best_label}")
    #                 label_scores = [{"label": best_label, "score": best_score}]

    #             final_results.append({
    #                 "sequence": text,
    #                 "labels": [entry["label"] for entry in label_scores],
    #                 "scores": [entry["score"] for entry in label_scores]
    #             })
            
    #     t6 = time.perf_counter()
    #     logger.info(f"Preparation Time     : {t1 - t0:.4f} sec")
    #     logger.info(f"Tokenization Time    : {t2 - t1:.4f} sec")
    #     logger.info(f"Inference Time       : {t3 - t2:.4f} sec")
    #     logger.info(f"Softmax + Extraction : {t4 - t3:.4f} sec")
    #     logger.info(f"Filtering Time       : {t5 - t4:.4f} sec")
    #     logger.info(f"Sorting + Formatting : {t6 - t5:.4f} sec")
    #     logger.info(f"Total Classify Time  : {t6 - t0:.4f} sec")

    #     return final_results

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
            futures = [self.executor.submit(self.classifier.classify, batch) for batch in batches]

            for idx, future in enumerate(futures, start=1):
                try:
                    res = future.result()
                    results.extend(res)
                    logger.info(f"Batch {idx}/{len(batches)} processed successfully")
                except Exception as batch_error:
                    logger.warning(f"Batch {idx} failed during classification: {batch_error}", exc_info=True)
                    failed_batch = batches[idx - 1]
                    results.extend([{"sequence": text, "labels": [], "scores": []} for text in failed_batch])

            operations = []
            batch_updates = []

            for item, result in zip(buffer, results):
                try:
                    if not result.get("labels"):
                        logger.warning(f"No labels classified for item ID: {item.get('id')}, skipping update.")
                        continue

                    category = result["labels"][0]
                    tags = result["labels"][1:4]

                    try:
                        object_id = ObjectId(item["id"])
                    except Exception:
                        logger.warning(f"Invalid ObjectId for item: {item.get('id')}, skipping.")
                        continue

                    operations.append(UpdateOne(
                        {"_id": object_id},
                        {"$set": {"category": category, "tags": tags}}
                    ))

                    batch_updates.append({
                        "id": str(item["id"]),
                        "category": category,
                        "tags": tags
                    })

                except Exception as item_error:
                    logger.warning(f"Error processing item ID: {item.get('id')} - {item_error}", exc_info=True)

            if operations:
                logger.info(f"Updating {len(operations)} items in DB")
                write_result = self.collection.bulk_write(operations, ordered=False)
                logger.info(f"Bulk write result: {write_result.bulk_api_result}")

                if batch_updates:
                    self.content_kafka_service.trigger_batch_embedding_update(batch_updates)
                else:
                    logger.warning("No valid batch_updates to send to Kafka.")
            else:
                logger.warning("No DB update operations generated — check input and classification results.")

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