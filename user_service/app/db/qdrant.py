from typing import List, Dict
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams
from app.config.logger_config import logger
from app.config.config import QDRANT_TOKEN,QDRANT_HOST,QDRANT_COLLECTION

class QdrantDB:
    def __init__(self,collection_name: str = QDRANT_COLLECTION):
        try:
            self.client = QdrantClient(
                url=QDRANT_HOST, 
                api_key=QDRANT_TOKEN,
            )
            
            self.collection_name = collection_name
            self._initialize_collection()
            logger.info("Qdrant Connected Successfully")
        except Exception as e:
            logger.error(f"Qdrant Connection Failed: {e}")
            self.client = None
        
    def _initialize_collection(self):
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            logger.info(f" Creating collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=14, distance=Distance.COSINE)
            )

    def upsert_vectors(self, collection_name: str, vectors: List[Dict]):
        if self.client is None:
            logger.error("Qdrant client is not connected.")
            return
        
        points = [
            models.PointStruct(id=vec["id"], vector=vec["vector"], payload={"mongo_id": vec["mongo_id"]})
            for vec in vectors
        ]

        self.client.upsert(collection_name=collection_name, points=points)
        logger.info(f"Upserted {len(vectors)} vectors into '{collection_name}'.")
        return

    def get_all_vector_ids(self, collection_name: str) -> List[str]:
        try:
            points, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=None,
            )
            return [str(point.id) for point in points]
        except Exception as e:
            logger.error(f"Error fetching vector IDs from Qdrant: {e}")
            return []

    def delete_vectors(self, collection_name, vector_ids):
        self.client.delete(
            collection_name=collection_name, 
            points_selector=models.PointIdsList(points=vector_ids)
        )

    def search_vector(self, collection_name: str, query_vector: List[float], top_k: int = 5):
        if self.client is None:
            logger.error("Qdrant client is not connected.")
            return []

        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k
            )
            logger.info(f"Search in '{collection_name}' returned {len(results)} results.")
            return results
        except Exception as e:
            logger.error(f"Qdrant Search Error: {e}")
            return []

    def search_similar_users(self, query_embedding: List[float], top_k: int = 30) -> List[Dict]:
        if self.client is None:
            logger.error("Qdrant client is not connected.")
            return []

        try:
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k
            )
            return [{"user_id": res.payload["user_id"], "score": res.score} for res in search_results]
        except Exception as e:
            logger.error(f"Error searching similar users: {e}")
            return []

qdrant_db = QdrantDB()