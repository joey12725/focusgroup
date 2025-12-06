
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from simulation import Simulation

class TestAssistantInjection(unittest.TestCase):
    def setUp(self):
        self.sim = Simulation("dummy_path")
        # Mock the client
        self.sim.client = AsyncMock()

    def test_list_processing(self):
        """Test that a list of questions is processed sequentially."""
        async def run_test():
            # Setup mocks
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Persona Answer"
            self.sim.client.chat.completions.create.return_value = mock_response

            persona = {"filename": "p_001.md", "content": "Persona Profile"}
            questions = ["Q1", "Q2"]
            
            result = await self.sim.conduct_interview(persona, questions, depth=0)
            
            conversation = result['conversation']
            # Expected: Q1, A1, Q2, A2 (4 messages)
            self.assertEqual(len(conversation), 4)
            self.assertEqual(conversation[0]['role'], 'interviewer')
            self.assertEqual(conversation[0]['content'], 'Q1')
            self.assertEqual(conversation[2]['role'], 'interviewer')
            self.assertEqual(conversation[2]['content'], 'Q2')

        asyncio.run(run_test())

    def test_assistant_injection(self):
        """Test that ASSISTANT(...) tags validly inject generated questions."""
        async def run_test():
            # Setup mocks
            # We need to simulate different responses for different calls
            # 1. Assistant generation
            # 2. Persona answer to Q1
            # 3. Persona answer to injected Q
            
            mock_response_assistant = MagicMock()
            mock_response_assistant.choices[0].message.content = "Generated Question"
            
            mock_response_persona = MagicMock()
            mock_response_persona.choices[0].message.content = "Persona Answer"
            
            # Side effect to return different responses based on input messages
            async def side_effect(*args, **kwargs):
                messages = kwargs.get('messages', [])
                last_msg = messages[-1]['content']
                
                # If checking for assistant instruction
                if "You are a helpful AI assistant" in messages[0]['content']:
                    return mock_response_assistant
                else:
                    return mock_response_persona

            self.sim.client.chat.completions.create.side_effect = side_effect

            persona = {"filename": "p_001.md", "content": "Persona Profile"}
            questions = ["Q1", "ASSISTANT(Ask something cool)"]
            
            result = await self.sim.conduct_interview(persona, questions, depth=0)
            
            conversation = result['conversation']
            # Expected: Q1, A1, Generated Question, A2
            self.assertEqual(len(conversation), 4)
            self.assertEqual(conversation[0]['content'], 'Q1')
            self.assertEqual(conversation[2]['content'], 'Generated Question')
            
            # Verify the assistant context included history
            # The assistant call happens before the second persona call
            # We can check call args if needed or rely on the fact that result is correct
            
        asyncio.run(run_test())

    def test_depth_after_list(self):
        """Test that depth parameter triggers auto-followups after list exhaustion."""
        async def run_test():
             # Setup mocks
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Generic Response"
            self.sim.client.chat.completions.create.return_value = mock_response
            
            # Mock generate_followup to return "Auto Followup"
            self.sim.generate_followup = AsyncMock(return_value="Auto Followup")

            persona = {"filename": "p_001.md", "content": "Persona Profile"}
            questions = ["Q1"]
            
            # Depth 1 -> Q1, A1, Auto1, A2
            result = await self.sim.conduct_interview(persona, questions, depth=1)
            
            conversation = result['conversation']
            self.assertEqual(len(conversation), 4)
            self.assertEqual(conversation[2]['content'], 'Auto Followup')

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
