import numpy as np
import json
# from sentence_transformers import SentenceTransformer
# from sklearn.decomposition import PCA
from app.db.mongo import mongo_db
from app.db.redis_cache import redis_cache
from pymongo.collection import Collection
from pymongo.database import Database


class CategoryEmbeddingService:
    def __init__(self, n_components=14):
        self.categories = [
            "Gaming", "Finance", "Business", "Healthcare", "Science", "Education", "Psychology",
            "Marketing", "Politics", "Entertainment", "Sports", "Travel", "Sustainability", "Technology"
        ]
        
        # self.model = SentenceTransformer(model_name)
        self.n_components = n_components
        self.category_embedding_dict = {}

        if isinstance(mongo_db.db, Database):
            self.collection: Collection = mongo_db.get_collection("category_embeddings")
        else:
            raise TypeError("mongo_db.db is not a valid pymongo Database instance!")

        self._load_embeddings()

    # def _generate_embeddings(self):
    #     """Generates and reduces embeddings for predefined categories."""
    #     print(" Generating new category embeddings...")
    #     high_dim_embeddings = np.array([self.model.encode(cat) for cat in self.categories])
    #     pca = PCA(n_components=self.n_components)
    #     reduced_embeddings = pca.fit_transform(high_dim_embeddings)
    #     self.category_embedding_dict = {self.categories[i]: reduced_embeddings[i].tolist() for i in range(len(self.categories))}

    def _load_embeddings(self):
        cached_data = redis_cache.get_cache("category_embeddings")

        if cached_data:
            self.category_embedding_dict = cached_data
        else:
            self._fetch_from_mongo()

    def _fetch_from_mongo(self):
        mongo_embeddings = list(self.collection.find({}, {"_id": 0, "category": 1, "vector": 1}))
        self.category_embedding_dict = {doc["category"]: doc["vector"] for doc in mongo_embeddings}

        redis_cache.set_cache("category_embeddings", self.category_embedding_dict)

    def store_embeddings(self):
        for category, vector in self.category_embedding_dict.items():
            existing_record = self.collection.find_one({"category": category})
            
            category_embedding = {
                "category": category,
                "vector": vector
            }

            if existing_record:
                self.collection.update_one({"category": category}, {"$set": category_embedding})
            else:
                self.collection.insert_one(category_embedding)

        redis_cache.set_cache("category_embeddings", self.category_embedding_dict)

    def get_embedding(self, category):
        return self.category_embedding_dict.get(category, None)
    
    def get_all_embeddings(self):
        return self.category_embedding_dict
        
embedding_service = CategoryEmbeddingService()