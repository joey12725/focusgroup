# VibeTest: AI-Powered Persona Simulation Tool

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**VibeTest** is a command-line tool that allows you to simulate customer interviews with AI-generated personas. It helps founders and product managers validate ideas, test messaging, and gain psychographic insights without the cost and time of traditional market research.

## 🚀 Key Features

*   **Hybrid Persona Generation**: Combines deterministic "blueprints" (for statistical control) with LLM-based creativity to generate realistic, diverse personas.
*   **The Blueprint System**: Define your target audience using validatable logic (e.g., `{{ weighted('Admin': 0.8, 'Manager': 0.2) }}`).
*   **Parallel Simulations**: Conduct dozens of interviews simultaneously using async/await.
*   **The Mom Test Mode**: Automatically rewrites your questions to avoid leading the witness and gather unbiased behavioral data.
*   **Split Testing**: Run A/B tests on your messaging with cohorts of personas.
*   **AI Analysis**: Automatically synthesize interview results into a "Go/No-Go" report with identified consensus and outliers.

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/vibetest.git
    cd vibetest
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up configuration:**
    *   Create a `config.ini` file in the root directory (copy from `config.ini.example` if available).
    *   Add your OpenRouter API key:
        ```ini
        [API]
        OPENROUTER_API_KEY=your_api_key_here
        ```

## ⚡ Quick Start

**1. Initialize a new project:**
Tell the "Architect" about your idea to generate a blueprint of your target audience.
```bash
python main.py init "fintech_app" --desc "A budgeting app for college students who are broke but want to travel."
```

**2. Generate Personas:**
Create 50 personas based on the blueprint.
```bash
python main.py generate "fintech_app" --count 50
```

**3. Run a Simulation:**
Ask your personas a question.
```bash
python main.py ask "What is the biggest frustration you have with saving money?" "fintech_app" --sample 20
```

**4. Analyze Results:**
Get a synthesized report of the feedback.
```bash
python main.py analyze "fintech_app" --save
```

## 📚 Documentation

For more detailed information, check out the full documentation:

*   [**Architecture**](docs/architecture.md): Learn about the system design and core components.
*   [**Usage Guide**](docs/usage.md): Detailed command reference and examples.
*   [**Configuration**](docs/configuration.md): How to configure models and API keys.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to get started.

## 📄 License

This project is licensed under the MIT License.
