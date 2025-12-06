import os
import json
import configparser
from llm_cost_tracker import CostTracker
from openai import OpenAI
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown

class Analyst:
    def __init__(self, project_path: str):
        self.project_path = project_path
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
        self.console = Console()

    def load_session(self, session_id: str):
        sessions_dir = os.path.join(self.project_path, "sessions")
        if session_id == "latest":
            files = [f for f in os.listdir(sessions_dir) if f.endswith(".json")]
            if not files:
                return None
            files.sort(reverse=True)
            filename = files[0]
        else:
            filename = session_id if session_id.endswith(".json") else f"{session_id}.json"
            
        filepath = os.path.join(sessions_dir, filename)
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, 'r') as f:
            return json.load(f)

    def analyze_results(self, session_data: dict):
        # Check for batch session
        if session_data.get('type') == 'batch' or 'tests' in session_data:
            return self.analyze_batch_results(session_data['tests'])

        question = session_data.get('initial_question', session_data.get('question'))
        results = session_data['results']
        is_split_test = session_data.get('is_split_test', False)
        
        return self._analyze_single_test(question, results, is_split_test)

    def analyze_batch_results(self, tests: list):
        full_report = "# Batch Analysis Report\n\n"
        
        for i, test in enumerate(tests):
            question = test['question']
            results = test['results']
            is_split_test = test['is_split_test']
            
            full_report += f"## Test {i+1}: {question}\n\n"
            
            # Add a status update to the console if possible, but we are inside a method.
            # We'll just run it.
            report = self._analyze_single_test(question, results, is_split_test)
            full_report += report + "\n\n---\n\n"
            
        return full_report

    def _analyze_single_test(self, question: str, results: list, is_split_test: bool):
        if is_split_test:
            # Group by variant
            variants = {}
            for r in results:
                if r['status'] == 'success':
                    variant = r.get('variant', 'Unknown')
                    if variant not in variants:
                        variants[variant] = []
                    
                    if 'conversation' in r:
                        conv_text = f"Persona: {r['persona']}\n"
                        for msg in r['conversation']:
                            role = "Interviewer" if msg['role'] == 'interviewer' else "Persona"
                            conv_text += f"{role}: {msg['content']}\n"
                        variants[variant].append(conv_text)
                    else:
                        variants[variant].append(f"Persona: {r['persona']}\nResponse: {r['response']}")
            
            if not variants:
                return "No successful responses to analyze."

            system_prompt = (
                "You are a Data Analyst specializing in A/B testing. "
                "I will provide you with interview transcripts from a split test with multiple variants. "
                "Your task is to compare the performance of each variant side-by-side. "
                "Analyze the sentiment, enthusiasm, and conversion intent for each group. "
                "Identify which variant performed better and why. "
                "Format the output as a Markdown report with a clear 'Winner' recommendation."
            )
            
            user_prompt = f"Initial Question: {question}\n\n"
            for variant, transcripts in variants.items():
                user_prompt += f"## Variant: {variant}\n"
                user_prompt += "\n---\n".join(transcripts)
                user_prompt += "\n\n"

        else:
            # Normal analysis
            formatted_responses = []
            for r in results:
                if r['status'] == 'success':
                    if 'conversation' in r:
                        conv_text = f"Persona: {r['persona']}\n"
                        for msg in r['conversation']:
                            role = "Interviewer" if msg['role'] == 'interviewer' else "Persona"
                            conv_text += f"{role}: {msg['content']}\n"
                        formatted_responses.append(conv_text)
                    else:
                        formatted_responses.append(f"Persona: {r['persona']}\nResponse: {r['response']}")
            
            if not formatted_responses:
                return "No successful responses to analyze."

            system_prompt = (
                "You are a Data Analyst. I will provide you with a set of interview transcripts from different personas. "
                "Your task is to synthesize these findings into a clear report. "
                "Identify the Consensus (60%+ agreement), the Variance (major points of contention), and any Outliers. "
                "Pay attention to how the personas responded to follow-up questions to gain deeper insights. "
                "Finally, provide a 'Go/No-Go' recommendation based on the sentiment. "
                "Format the output as a Markdown report."
            )
            
            user_prompt = f"Initial Question: {question}\n\nTranscripts:\n" + "\n---\n".join(formatted_responses)

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

    def render_report(self, report_content: str):
        from rich.panel import Panel
        self.console.print(Panel(Markdown(report_content), title="Analysis Report", border_style="magenta", expand=False))

    def save_report(self, report_content: str, session_data: dict):
        reports_dir = os.path.join(self.project_path, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = session_data.get('timestamp', 'unknown')
        filename = f"report_{timestamp}.md"
        filepath = os.path.join(reports_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(report_content)
            
        return filepath
