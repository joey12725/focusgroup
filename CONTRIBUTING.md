# Contributing to VibeTest

Thank you for your interest in contributing to VibeTest! We welcome contributions from the community to help make this tool better for everyone.

## 🛠️ Development Setup

1.  **Fork the repository** on GitHub.
2.  **Clone your fork** locally:
    ```bash
    git clone https://github.com/yourusername/vibetest.git
    cd vibetest
    ```
3.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
4.  **Install dependencies** including dev requirements:
    ```bash
    pip install -r requirements.txt
    ```

## 🧪 Testing

We use `pytest` for testing. Please ensure all tests pass before submitting a Pull Request.

**Run all tests:**
```bash
pytest
```

**Run specific test file:**
```bash
pytest test_simulation.py
```

## 📝 Coding Guidelines

*   **Style**: We follow PEP 8. Please use a linter like `flake8` or a formatter like `black` to ensure your code is consistently formatted.
*   **Documentation**: Add docstrings to all new modules, classes, and functions. If you add a new feature, please update the [Usage Guide](docs/usage.md) and [README](README.md) if applicable.
*   **Type Hinting**: Use Python type hints for function arguments and return values.

## 🚀 Submitting a Pull Request

1.  Create a new branch for your feature or fix: `git checkout -b feature/my-new-feature`.
2.  Commit your changes with clear, descriptive messages.
3.  Push to your fork: `git push origin feature/my-new-feature`.
4.  Open a Pull Request on the main repository description of your changes.

## 🐛 Reporting Bugs

If you find a bug, please open an issue on GitHub with:
*   Steps to reproduce.
*   Expected vs. actual behavior.
*   Your environment details (OS, Python version).

Thank you for helping improve VibeTest!
