# Contributing to eTax

Thank you for your interest in contributing to eTax!

## Development Setup

### Prerequisites
- Python 3.10+
- Frappe Bench v15
- ERPNext v15

### Installation

```bash
# Clone the repository
bench get-app https://github.com/mn-frappe/etax

# Install on your site
bench --site your-site.local install-app etax

# Install development dependencies
cd apps/etax
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
cd /path/to/frappe-bench
bench --site your-site.local run-tests --app etax
```

## Code Style

- We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
- Pre-commit hooks are configured to run automatically
- Follow PEP 8 guidelines

### Before Committing

```bash
# Run linter
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `chore:` - Maintenance tasks
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests

## Reporting Issues

- Use the GitHub issue templates
- Provide detailed reproduction steps
- Include environment information

## Questions?

Feel free to open an issue for any questions!
