from transformers import pipeline
from typing import List, Tuple
import functools

class ContentClassifier:
    def __init__(self, model_name: str = "facebook/bart-large-mnli", confidence_threshold: float = 0.5):
        self.classifier = pipeline("zero-shot-classification", model=model_name)
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

classifier = ContentClassifier(confidence_threshold=0.6) 