# tests/test_llm.py
# Unit tests for LLMClassifier and its subclasses.
import unittest
from llm.openai_provider import OpenAIClassifier
from llm.claude_provider import ClaudeClassifier
from llm.bedrock_provider import BedrockClassifier

class TestLLMClassifier(unittest.TestCase):
    def test_openai_classifier(self):
        # This is a placeholder; in real tests, mock OpenAI API
        classifier = OpenAIClassifier(api_key="test")
        self.assertTrue(hasattr(classifier, 'classify'))

    def test_claude_classifier(self):
        # This is a placeholder; in real tests, mock Anthropic API
        classifier = ClaudeClassifier(api_key="test")
        self.assertTrue(hasattr(classifier, 'classify'))

    def test_bedrock_classifier(self):
        # This is a placeholder; in real tests, mock boto3
        classifier = BedrockClassifier()
        self.assertTrue(hasattr(classifier, 'classify'))

if __name__ == '__main__':
    unittest.main()
