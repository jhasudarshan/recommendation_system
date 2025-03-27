from transformers import pipeline
from typing import List, Tuple
import functools
from app.config.config import CLASSIFIER_MODEL,CLASSIFICATION

class ContentClassifier:
    def __init__(self, model_name: str,classification_type: str, confidence_threshold: float = 0.5):
        self.classifier = pipeline(classification_type, model=model_name)
        self.confidence_threshold = confidence_threshold
        self.categories = [
            "Gaming", "Finance", "Business", "Healthcare", "Science", "Education", "Psychology",
            "Marketing", "Politics", "Entertainment", "Sports", "Travel", "Sustainability", "Technology"
        ]

    @functools.lru_cache(maxsize=100)
    def classify(self, title: str, description: str, body: str = "") -> Tuple[str, List[str]]:
        text = f"{title}. {description}."
        
        if body:
            text += f" {body}."

        result = self.classifier(text, self.categories, multi_label=True)

        primary_category = result["labels"][0]

        tags = [
            label for label, score in zip(result["labels"], result["scores"])
            if score >= self.confidence_threshold
        ]

        return primary_category, tags

classifier = ContentClassifier(CLASSIFIER_MODEL,CLASSIFICATION,confidence_threshold=0.6) 