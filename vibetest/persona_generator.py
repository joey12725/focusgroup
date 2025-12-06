import yaml
import json
import os
from openai import OpenAI, AsyncOpenAI
from .blueprint_parser import BlueprintParser
import configparser
from .llm_cost_tracker import CostTracker

class PersonaGenerator:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.parser = BlueprintParser()
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        
        api_key = self.config.get('API', 'OPENROUTER_API_KEY', fallback=os.getenv("OPENROUTER_API_KEY"))
        if api_key:
            api_key = api_key.strip('"').strip("'")
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.async_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        models_str = self.config.get('API', 'MODELS', fallback="google/gemini-2.5-flash-lite-preview-09-2025")
        self.models = [m.strip().strip('"').strip("'") for m in models_str.split(',')]
        self.model = self.models[0]

    def load_blueprint(self):
        blueprint_path = os.path.join(self.project_path, "blueprint.yaml")
        if not os.path.exists(blueprint_path):
            raise FileNotFoundError(f"Blueprint not found at {blueprint_path}")
        
        with open(blueprint_path, 'r') as f:
            return yaml.safe_load(f)

    def generate_skeleton(self, blueprint: dict):
        """
        Generates a raw dictionary of stats based on the blueprint.
        """
        skeleton = {}
        for key, value in blueprint.items():
            if isinstance(value, str):
                skeleton[key] = self.parser.parse(value)
            elif isinstance(value, dict):
                # Handle nested structures if necessary, or just recurse
                skeleton[key] = self.generate_skeleton(value)
            else:
                skeleton[key] = value
        return skeleton

    def flesh_out_persona(self, skeleton: dict):
        """
        Uses the LLM to generate the narrative "flesh" for the persona.
        """
        system_prompt = (
            "You are a creative writer. I will give you a skeleton of a person with raw data points. "
            "You must breathe life into them. Connect the dots. "
            "If they are 'Angry' and 'Broke', invent a scenario explaining why. "
            "Assign a 'skepticism' attribute to the persona on a scale of 0 to 100 based on their personality. "
            "Return the result as a Markdown file with YAML frontmatter containing the skeleton data and the new skepticism attribute."
        )
        
        user_prompt = f"Here is the skeleton:\n{json.dumps(skeleton, indent=2)}\n\nGenerate the full persona profile."

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        if response.usage:
            CostTracker().add_usage(self.model, response.usage.prompt_tokens, response.usage.completion_tokens)
        
        return response.choices[0].message.content

    async def async_flesh_out_persona(self, skeleton: dict):
        """
        Async version: Uses the LLM to generate the narrative "flesh" for the persona.
        """
        system_prompt = (
            "You are a creative writer. I will give you a skeleton of a person with raw data points. "
            "You must breathe life into them. Connect the dots. "
            "If they are 'Angry' and 'Broke', invent a scenario explaining why. "
            "Assign a 'skepticism' attribute to the persona on a scale of 0 to 100 based on their personality. "
            "Return the result as a Markdown file with YAML frontmatter containing the skeleton data and the new skepticism attribute."
        )
        
        user_prompt = f"Here is the skeleton:\n{json.dumps(skeleton, indent=2)}\n\nGenerate the full persona profile."

        response = await self.async_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        if response.usage:
            # CostTracker is thread safe with locks, safe to call from async loop 
            # (as long as it doesn't block significantly, but simple addition is fine)
            CostTracker().add_usage(self.model, response.usage.prompt_tokens, response.usage.completion_tokens)
        
        return response.choices[0].message.content

    def save_persona(self, content: str, filename: str):
        personas_dir = os.path.join(self.project_path, "personas")
        os.makedirs(personas_dir, exist_ok=True)
        
        with open(os.path.join(personas_dir, filename), 'w') as f:
            f.write(content)

if __name__ == "__main__":
    # Test stub
    pass
