import unittest
from unittest.mock import MagicMock, patch
import json
from vibetest.analyst import Analyst

class TestAnalyst(unittest.TestCase):
    @patch('vibetest.analyst.OpenAI')
    def test_analyze_results(self, mock_openai):
        # Setup mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Analysis Report"
        mock_client.chat.completions.create.return_value = mock_response
        
        analyst = Analyst("dummy_path")
        session_data = {
            "question": "Q",
            "results": [{"response": "A", "status": "success", "persona": "p1.md"}]
        }
        
        report = analyst.analyze_results(session_data)
        self.assertEqual(report, "Analysis Report")

    @patch('vibetest.analyst.os.listdir')
    @patch('vibetest.analyst.open')
    @patch('vibetest.analyst.os.path.exists')
    def test_load_session(self, mock_exists, mock_open, mock_listdir):
        mock_exists.return_value = True
        mock_listdir.return_value = ["session_1.json"]
        mock_open.return_value.__enter__.return_value = MagicMock()
        # Mock json.load
        with patch('json.load') as mock_json_load:
            mock_json_load.return_value = {"key": "value"}
            
            analyst = Analyst("dummy_path")
            data = analyst.load_session("latest")
            
            self.assertEqual(data, {"key": "value"})

if __name__ == "__main__":
    unittest.main()
