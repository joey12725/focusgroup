import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import os
from simulation import Simulation

class TestSimulation(unittest.TestCase):
    @patch('simulation.AsyncOpenAI')
    def test_ask_persona(self, mock_openai):
        # Setup mock
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "I am fine."
        mock_client.chat.completions.create.return_value = mock_response
        
        sim = Simulation("dummy_path")
        persona = {"filename": "p_001.md", "content": "Name: John"}
        
        # Run async test
        result = asyncio.run(sim.ask_persona(persona, "How are you?"))
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['response'], "I am fine.")
        self.assertEqual(result['persona'], "p_001.md")

    @patch('simulation.os.listdir')
    @patch('simulation.open')
    @patch('simulation.os.path.exists')
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
