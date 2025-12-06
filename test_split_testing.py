import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
import os
from simulation import Simulation
from analyst import Analyst

class TestSplitTesting(unittest.TestCase):
    def setUp(self):
        self.project_path = "/tmp/test_project"
        self.sim = Simulation(self.project_path)
        self.analyst = Analyst(self.project_path)

    @patch('simulation.Simulation.load_random_personas')
    @patch('simulation.Simulation.conduct_interview')
    def test_run_simulation_split_testing(self, mock_conduct, mock_load):
        # Setup mocks
        mock_load.return_value = [
            {"filename": "p1.md", "content": "Persona 1"},
            {"filename": "p2.md", "content": "Persona 2"},
            {"filename": "p3.md", "content": "Persona 3"},
            {"filename": "p4.md", "content": "Persona 4"}
        ]
        
        mock_conduct.side_effect = lambda p, q, d, v: asyncio.sleep(0) # Mock coroutine
        
        # Run simulation with options
        options = ["$10", "$20"]
        question = "How much for ***?"
        
        asyncio.run(self.sim.run_simulation(question, 4, 0, options))
        
        # Verify calls
        self.assertEqual(mock_conduct.call_count, 4)
        
        # Check arguments for each call
        calls = mock_conduct.call_args_list
        
        # Persona 1 -> Variant $10
        args1 = calls[0][0]
        self.assertEqual(args1[1], "How much for $10?")
        self.assertEqual(args1[3], "$10")
        
        # Persona 2 -> Variant $20
        args2 = calls[1][0]
        self.assertEqual(args2[1], "How much for $20?")
        self.assertEqual(args2[3], "$20")
        
        # Persona 3 -> Variant $10
        args3 = calls[2][0]
        self.assertEqual(args3[1], "How much for $10?")
        self.assertEqual(args3[3], "$10")
        
        # Persona 4 -> Variant $20
        args4 = calls[3][0]
        self.assertEqual(args4[1], "How much for $20?")
        self.assertEqual(args4[3], "$20")

    def test_analyze_results_split_testing(self):
        # Mock session data
        session_data = {
            "initial_question": "How much for ***?",
            "is_split_test": True,
            "results": [
                {"status": "success", "variant": "$10", "persona": "p1.md", "response": "I'd buy it."},
                {"status": "success", "variant": "$20", "persona": "p2.md", "response": "Too expensive."},
                {"status": "success", "variant": "$10", "persona": "p3.md", "response": "Great deal."},
                {"status": "success", "variant": "$20", "persona": "p4.md", "response": "Maybe."}
            ]
        }
        
        # Mock OpenAI client
        self.analyst.client = MagicMock()
        self.analyst.client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="Analysis Report"))
        ]
        
        self.analyst.analyze_results(session_data)
        
        # Verify prompt construction
        call_args = self.analyst.client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        user_prompt = messages[1]['content']
        
        self.assertIn("## Variant: $10", user_prompt)
        self.assertIn("## Variant: $20", user_prompt)
        self.assertIn("I'd buy it.", user_prompt)
        self.assertIn("Too expensive.", user_prompt)

if __name__ == '__main__':
    unittest.main()
