import os
import yaml
import configparser
from openai import OpenAI

class Architect:
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

    def create_blueprint(self, project_name: str, description: str) -> str:
        """
        Generates a blueprint.yaml content based on the project description.
        """
        system_prompt = (
            "You are The Architect. Your goal is to translate a high-level product description "
            "into a strict mathematical configuration (The Blueprint) for generating user personas.\n\n"
            "You must output a valid YAML file.\n"
            "The YAML must define variables using the following custom DSL functions. "
            "IMPORTANT: You MUST wrap every function call in double curly braces {{ }} AND double quotes like this: \"{{ function(...) }}\".\n"
            "- \"{{ range(min, max) }}\": Uniform integer selection\n"
            "- \"{{ choice(A, B, C) }}\": Simple random selection\n"
            "- \"{{ weighted(Key:Val, Key2:Val2) }}\": Weighted probability\n"
            "- \"{{ normal(mean, std) }}\": Bell curve distribution\n"
            "- \"{{ bool(chance) }}\": Boolean with probability (e.g., 0.3 for 30%)\n\n"
            "Structure the YAML as a simple key-value map where keys are variable names and values are the quoted DSL strings.\n"
            "Example:\n"
            "Age: \"{{ range(25, 55) }}\"\n"
            "Role: \"{{ choice(Admin, User) }}\"\n\n"
            "Do NOT use nested structures like 'type' or 'distribution'. Just 'Variable_Name: \"{{ function(...) }}\"'.\n"
            "Determine 3-5 crucial psychographic variables that would impact a buying decision "
            "(e.g., 'Risk Tolerance', 'Tech Stack', 'Aesthetic Taste') and include them in the YAML.\n"
            "Also include standard demographic variables like age, income, role, location.\n"
            "Do NOT include markdown formatting (like ```yaml). Just return the raw YAML content."
        )

        user_prompt = f"Project Name: {project_name}\nDescription: {description}\n\nCreate the blueprint.yaml."

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        return response.choices[0].message.content

    def save_blueprint(self, project_name: str, content: str):
        project_dir = os.path.join("projects", project_name)
        os.makedirs(project_dir, exist_ok=True)
        
        filepath = os.path.join(project_dir, "blueprint.yaml")
        
        # Clean up potential markdown code blocks if the LLM ignores instructions
        clean_content = content.strip()
        if clean_content.startswith("```yaml"):
            clean_content = clean_content[7:]
        if clean_content.startswith("```"):
            clean_content = clean_content[3:]
        if clean_content.endswith("```"):
            clean_content = clean_content[:-3]
            
        with open(filepath, 'w') as f:
            f.write(clean_content.strip())
        
        return filepath
