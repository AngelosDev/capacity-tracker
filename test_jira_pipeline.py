import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from jira_pipeline import extract_data, process_data, classify_issues, store_output

class TestJiraPipeline(unittest.TestCase):

    @patch('jira_pipeline.requests.get')
    def test_extract_data(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = [{"key": "TEST-1", "summary": "Test issue"}]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        config = {
            'jira': {
                'api_url': 'https://example.com',
                'auth_token': 'token'
            },
            'filters': {}
        }

        data = extract_data(config)
        self.assertEqual(len(data), 1)

    def test_process_data(self):
        data = [{"Updated": "2025-06-18T12:00:00", "Created": "2025-06-17T12:00:00"}]
        df = process_data(data)
        self.assertEqual(df['Updated'][0], "2025-06-18T12:00:00")

    def test_classify_issues(self):
        data = pd.DataFrame([{"Summary": "Test issue", "Description": "Tooling improvements"}])
        config = {
            'classification': {
                'categories': [
                    {"Name": "Internal Productivity", "Description": "Tooling improvements"}
                ]
            }
        }
        classified_data = classify_issues(data, config)
        self.assertEqual(classified_data['Category'][0], "Internal Productivity")

if __name__ == '__main__':
    unittest.main()
