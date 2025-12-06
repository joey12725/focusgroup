import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import os
from vibetest.simulation import Simulation

class TestSimulation(unittest.TestCase):
    @patch('vibetest.simulation.AsyncOpenAI')
    def test_conduct_interview(self, mock_openai):
        # Setup mock
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "I am fine."
        mock_client.chat.completions.create.return_value = mock_response
        
        sim = Simulation("dummy_path")
        persona = {"filename": "p_001.md", "content": "Name: John"}
        
        # Run async test
        result = asyncio.run(sim.conduct_interview(persona, "How are you?", depth=0))
        
        self.assertEqual(result['status'], 'success')
        # The response is in the conversation list now
        self.assertEqual(result['conversation'][1]['content'], "I am fine.")
        self.assertEqual(result['persona'], "p_001.md")

    @patch('vibetest.simulation.os.listdir')
    @patch('vibetest.simulation.open')
    @patch('vibetest.simulation.os.path.exists')
    def test_load_random_personas(self, mock_exists, mock_open, mock_listdir):
        mock_exists.return_value = True
        mock_listdir.return_value = ["p_001.md", "p_002.md"]
        mock_open.return_value.__enter__.return_value.read.return_value = "content"
        
        sim = Simulation("dummy_path")
        personas = sim.load_random_personas(1)
        
        self.assertEqual(len(personas), 1)
        self.assertEqual(personas[0]['content'], "content")

if __name__ == '__main__':
    unittest.main()
