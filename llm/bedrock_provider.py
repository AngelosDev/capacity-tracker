# llm/bedrock_provider.py
import boto3
import json
import logging
from botocore.exceptions import BotoCoreError, ClientError
from .base import LLMClassifier
from typing import List, Optional

class BedrockClassifier(LLMClassifier):
    def __init__(self, model: str = "anthropic.claude-instant-v1", region: str = "us-east-1"):
        self.model = model
        self.region = region
        self.client = boto3.client("bedrock-runtime", region_name=self.region)

    def classify(self, summary: str, description: str, categories: List[dict], model: Optional[str] = None) -> str:
        prompt = (
            f"Classify the following Jira issue into one of these categories: {categories}.\n"
            f"Only reply with the category name.\n\n"
            f"Summary: {summary}\n"
            f"Description: {description or 'No description'}"
        )
        body = {
            "prompt": prompt,
            "max_tokens_to_sample": 50,
            "temperature": 0.0,
        }
        try:
            response = self.client.invoke_model(
                modelId=model or self.model,
                body=json.dumps(body),
                accept="application/json",
                contentType="application/json"
            )
            result = json.loads(response["body"].read())
            return result.get("completion", "").strip() or "Unclassified"
        except (BotoCoreError, ClientError, Exception) as e:
            logging.error(f"Error classifying issue with Bedrock: {e}")
            return "Unclassified"
