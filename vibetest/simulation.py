import os
import random
import json
import asyncio
import datetime
import configparser
from openai import AsyncOpenAI
from .llm_cost_tracker import CostTracker

class Simulation:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        
        api_key = self.config.get('API', 'OPENROUTER_API_KEY', fallback=os.getenv("OPENROUTER_API_KEY"))
        if api_key:
            api_key = api_key.strip('"').strip("'")
            
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        models_str = self.config.get('API', 'MODELS', fallback="google/gemini-2.5-flash-lite-preview-09-2025")
        self.models = [m.strip().strip('"').strip("'") for m in models_str.split(',')]
        self.model = self.models[0]

    def load_random_personas(self, count: int):
        personas_dir = os.path.join(self.project_path, "personas")
        if not os.path.exists(personas_dir):
            return []
        
        files = [f for f in os.listdir(personas_dir) if f.endswith(".md")]
        if not files:
            return []
            
        selected_files = random.sample(files, min(count, len(files)))
        personas = []
        for filename in selected_files:
            with open(os.path.join(personas_dir, filename), 'r') as f:
                personas.append({"filename": filename, "content": f.read()})
        return personas

    async def generate_followup(self, history: list, model: str = None):
        if not model:
            model = self.model
            
        system_prompt = (
            "You are an inquisitive interviewer. "
            "Based on the conversation history, ask a relevant, short, and probing follow-up question "
            "to dig deeper into the persona's last response. "
            "Do not be repetitive. Be direct."
        )
        
        # Convert history to format for LLM
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            role = "user" if msg['role'] == 'interviewer' else "assistant"
            messages.append({"role": role, "content": msg['content']})
            
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages
            )
            if response.usage:
                CostTracker().add_usage(model, response.usage.prompt_tokens, response.usage.completion_tokens)
            content = response.choices[0].message.content
            if content and content.strip():
                return content.strip()
            return "Could you elaborate on that?"
        except Exception:
            return "Tell me more about that."

    async def generate_assistant_message(self, history: list, prompt: str, model: str = None):
        if not model:
            model = self.model
            
        system_prompt = (
            "You are a helpful AI assistant helping to facilitate a simulated interview. "
            "You have been asked to intervene in the conversation with a specific instruction. "
            "Follow the instruction precisely to generate the next message to the persona. "
            f"Instruction: {prompt}"
        )
        
        # Convert history
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            role = "user" if msg['role'] == 'interviewer' else "assistant"
            messages.append({"role": role, "content": msg['content']})
            
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages
            )
            if response.usage:
                CostTracker().add_usage(model, response.usage.prompt_tokens, response.usage.completion_tokens)
            content = response.choices[0].message.content
            return content.strip() if content else prompt
        except Exception:
            return prompt

    async def conduct_interview(self, persona: dict, initial_question: str | list[str], depth: int, variant: str = None, model: str = None):
        if not model:
            model = self.model
            
        conversation = []
        
        # 1. Prepare Question Queue
        question_queue = []
        if isinstance(initial_question, list):
            question_queue.extend(initial_question)
        else:
            question_queue.append(initial_question)
            
        # Add placeholders for follow-up depth
        # If we have a list, 'depth' applies after the list is exhausted
        for _ in range(depth):
            question_queue.append(None) # None triggers auto-generation
        
        import re
        
        for i, queued_q in enumerate(question_queue):
            current_question = queued_q
            
            # Auto-generate if None
            if current_question is None:
                current_question = await self.generate_followup(conversation, model=model)
                
            # Process ASSISTANT(...) injection
            # Check if it starts with ASSISTANT( and ends with )
            # We use regex to capture content
            match = re.search(r'^(?:ASSISTANT|AGENT)\((.*)\)$', current_question, re.DOTALL)
            if match:
                instruction = match.group(1)
                # Generate the actual question using the assistant
                current_question = await self.generate_assistant_message(conversation, instruction, model=model)

            # Ensure we have a question
            if not current_question or not current_question.strip():
                current_question = "Could you explain further?"

            # Record question
            conversation.append({
                "role": "interviewer",
                "content": current_question
            })
            
            # Ask Persona
            system_prompt = (
                "You are a roleplay actor. I will provide you with a persona profile. "
                "You must adopt this persona completely. "
                "Answer the user's question honestly based on your defined 'Current Mood', 'Financial Situation', and other attributes. "
                "Be brief and conversational. Do not break character."
            )
            
            # Build context for persona including history
            messages = [{"role": "system", "content": system_prompt}]
            messages.append({"role": "system", "content": f"Persona Profile:\n{persona['content']}"})
            
            for msg in conversation:
                role = "user" if msg['role'] == 'interviewer' else "assistant"
                messages.append({"role": role, "content": msg['content']})
            
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages
                )
                if response.usage:
                    CostTracker().add_usage(model, response.usage.prompt_tokens, response.usage.completion_tokens)
                answer = response.choices[0].message.content
            except Exception as e:
                answer = f"[Error: {str(e)}]"
                
            conversation.append({
                "role": "persona",
                "content": answer
            })

        return {
            "persona": persona['filename'],
            "conversation": conversation,
            "status": "success",
            "variant": variant
        }

    async def run_simulation(self, question: str | list[str], sample_size: int, depth: int = 0, options: list[str] = None):
        personas = self.load_random_personas(sample_size)
        if not personas:
            return []

        tasks = []
        if options:
            # Split testing mode
            num_variants = len(options)
            for i, persona in enumerate(personas):
                # Assign variant round-robin
                variant_idx = i % num_variants
                variant = options[variant_idx]
                
                # Inject variant into question(s)
                if isinstance(question, list):
                    variant_question = [q.replace("***", variant) for q in question]
                else:
                    variant_question = question.replace("***", variant)
                
                # Select random model for this thread
                thread_model = random.choice(self.models)
                tasks.append(self.conduct_interview(persona, variant_question, depth, variant, model=thread_model))
        else:
            # Normal mode
            tasks = []
            for p in personas:
                # Select random model for this thread
                thread_model = random.choice(self.models)
                tasks.append(self.conduct_interview(p, question, depth, model=thread_model))

        results = await asyncio.gather(*tasks)
        return results

    def save_session(self, question: str, results: list):
        sessions_dir = os.path.join(self.project_path, "sessions")
        os.makedirs(sessions_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"session_{timestamp}.json"
        
        session_data = {
            "timestamp": timestamp,
            "initial_question": question,
            "results": results,
            "is_split_test": any('variant' in r and r['variant'] is not None for r in results)
        }
        
        filepath = os.path.join(sessions_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=2)
            
        return filepath

    def save_batch_session(self, tests: list):
        sessions_dir = os.path.join(self.project_path, "sessions")
        os.makedirs(sessions_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"session_batch_{timestamp}.json"
        
        session_data = {
            "timestamp": timestamp,
            "type": "batch",
            "tests": tests
        }
        
        filepath = os.path.join(sessions_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=2)
            
        return filepath
