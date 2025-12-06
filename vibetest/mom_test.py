import os
import configparser
from openai import OpenAI

class MomTest:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        
        api_key = self.config.get('API', 'OPENROUTER_API_KEY', fallback=os.getenv("OPENROUTER_API_KEY"))
        if api_key:
            api_key = api_key.strip('"').strip("'")
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        models_str = self.config.get('API', 'MODELS', fallback="google/gemini-2.5-flash-lite-preview-09-2025")
        self.models = [m.strip().strip('"').strip("'") for m in models_str.split(',')]
        self.model = self.models[0]

    def rewrite_question(self, question: str) -> str:
        """
        Rewrites a user question to adhere to The Mom Test principles.
        """
        system_prompt = (
            "You are an expert in 'The Mom Test' by Rob Fitzpatrick. "
            "Your goal is to rewrite bad customer discovery questions (future-tense, hypothetical, seeking validation) "
            "into good questions (past-tense, specific, seeking facts and behaviors).\n\n"
            "Rules:\n"
            "1. No 'Would you...' questions.\n"
            "2. No pitching or selling.\n"
            "3. Ask about specific past behaviors and problems.\n"
            "4. Keep it conversational and brief.\n"
            "5. If the question is already good, return it as is.\n\n"
            "Example:\n"
            "Bad: 'Would you pay for an app that tracks your sleep?'\n"
            "Good: 'How do you currently keep track of your sleep patterns? Have you ever paid for a solution?'"
        )
        
        user_prompt = f"Rewrite this question: \"{question}\""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[Error rewriting question: {str(e)}] {question}"
