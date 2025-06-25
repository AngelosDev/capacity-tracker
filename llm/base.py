from typing import List, Optional

class LLMClassifier:
    def classify(self, summary: str, description: str, categories: List[dict], model: Optional[str] = None) -> str:
        raise NotImplementedError("Subclasses must implement classify method.")
