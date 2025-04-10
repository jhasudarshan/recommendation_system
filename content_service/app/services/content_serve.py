import threading
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone
from app.db.mongo import mongo_db
from app.config.logger_config import logger
from app.event.kafka_producer import KafkaEventProducer
from app.config.config import CONTENT_CLASSIFY_TOPIC

class ContentService:
    def __init__(self):
        self.content_collection = mongo_db.get_collection("content")
        self.embedding_update_producer = KafkaEventProducer()

    def process_content(self, content_data: dict):
        content_entry = {
            "title": content_data["title"],
            "description": content_data["description"],
            "url": content_data["url"],
            "image_link": content_data["image_link"],
            "interactionMetrics": {"likes": 0, "shares": 0, "clicks": 0},
            "created_at": datetime.now(timezone.utc)
        }
        
        try:
            inserted = self.content_collection.insert_one(content_entry)
            content_id = str(inserted.inserted_id)
        except DuplicateKeyError:
            existing_entry = self.content_collection.find_one({"url": content_entry["url"]}, {"_id": 1})
            content_id = str(existing_entry["_id"])

        logger.info(f"Content processed and stored successfully: {content_id}")
        self.embedding_update_producer.send(CONTENT_CLASSIFY_TOPIC,
         {
            "id": content_id,
            "title": content_data["title"],
            "desc": content_data["description"],
            "body": content_data.get("body", "")
        })
        return {"message": "Content added successfully!", "content_id": content_id}

    def bulkUpdate(self, updatedArticle):
       return self.content_collection.bulk_write(updatedArticle)
    
    def aggregation(self, pipeline):
        return list(self.content_collection.aggregate(pipeline))
    
    def classify_content(self, content_data):
        return self.classifier.classify(content_data["title"], content_data["description"], content_data.get("body", ""))
    
content_service = ContentService()










# def process_batch_content(self, content_list: list):
#         if not content_list:
#             return {"message": "No content to process."}

#         logger.info(f"Processing {len(content_list)} articles in batch")

#         urls = [content["url"] for content in content_list]
#         existing_articles = {doc["url"]: doc for doc in self.content_collection.find({"url": {"$in": urls}})}

#         updates = []
#         new_entries = []
#         tasks = []

#         with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
#             for content_data in content_list:
#                 url = content_data["url"]
#                 existing_entry = existing_articles.get(url)

#                 if existing_entry:
#                     if (
#                         existing_entry["title"] == content_data["title"]
#                         and existing_entry["description"] == content_data["description"]
#                     ):
#                         continue

#                 tasks.append(executor.submit(self.classify_content, content_data))

#             classified_results = [task.result() for task in concurrent.futures.as_completed(tasks)]

#         for content_data, (category, tags) in zip(content_list, classified_results):
#             url = content_data["url"]
#             content_data["category"] = content_data.get("category", category)
#             content_data["tags"] = tags

#             content_entry = {
#                 "title": content_data["title"],
#                 "description": content_data["description"],
#                 "category": content_data["category"],
#                 "tags": content_data["tags"],
#                 "url": content_data["url"],
#                 "image_link": content_data["image_link"],
#                 "interactionMetrics": {"likes": 0, "shares": 0, "clicks": 0},
#                 "created_at": datetime.now(timezone.utc),
#             }

#             if url in existing_articles:
#                 updates.append(UpdateOne({"url": url}, {"$set": content_entry}))
#             else:
#                 new_entries.append(content_entry)

#         with self.lock:
#             if updates:
#                 self.content_collection.bulk_write(updates)
#             if new_entries:
#                 self.content_collection.insert_many(new_entries)

#         logger.info(f"Batch content processing complete. {len(new_entries)} new, {len(updates)} updated.")
#         return {"message": "Batch content processing completed.", "new_entries": len(new_entries), "updated_entries": len(updates)}