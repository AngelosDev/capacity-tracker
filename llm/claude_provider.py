# llm/claude_provider.py
import anthropic
import logging
from .base import LLMClassifier
from typing import List, Optional

class ClaudeClassifier(LLMClassifier):
    def __init__(self, api_key: str, model: str = "claude-v1"):
        self.client = anthropic.Client(api_key)
        self.model = model

    def classify(self, summary: str, description: str, categories: List[dict], model: Optional[str] = None) -> str:
        prompt = (
            f"Classify the following issue based on its summary and description: \n"
            f"Only reply with the category name.\n\n"
            f"Summary: {summary}\n"
            f"Description: {description}\n"
            f"Categories: {categories}"
        )
        try:
            response = self.client.completion(
                prompt=prompt,
                model=model or self.model,
                max_tokens_to_sample=50
            )
            return response.get('completion', '').strip()
        except Exception as e:
            logging.error(f"Error classifying issue with Claude: {e}")
            return "Unclassified"
