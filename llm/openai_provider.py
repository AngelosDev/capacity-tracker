# llm/openai_provider.py
from openai import OpenAI
import logging
from .base import LLMClassifier
from typing import List, Optional

class OpenAIClassifier(LLMClassifier):
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def classify(self, summary: str, description: str, categories: List[dict], model: Optional[str] = None) -> str:
        prompt = (
            f"Classify the following Jira issue into one of these categories: {categories}.\n"
            f"Only reply with the category name.\n\n"
            f"Summary: {summary}\n"
            f"Description: {description or 'No description'}"
        )
        try:
            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert JIRA analyst. Your job is to classify JIRA issues into exactly one of the provided business categories. Respond with only the category name. Do not explain or elaborate."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=30,
                temperature=0.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Error classifying issue with OpenAI: {e}")
            return "Unclassified"
