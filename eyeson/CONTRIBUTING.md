# Contributing to EYESON

First off, thank you for considering contributing to EYESON! It's people like you that make this project a great tool for the bespoke clothing industry.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to see if the problem has already been reported. When you are creating a bug report, please include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples to demonstrate the steps**
- **Describe the behavior you observed and what behavior you expected**
- **Include code samples and screenshots if relevant**

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title**
- **Provide a step-by-step description of the suggested enhancement**
- **Provide specific examples to demonstrate the enhancement**
- **Explain why this enhancement would be useful**

### Pull Requests

1. Fork the repository
2. Create a new branch from `main` for your feature or bug fix
3. Make your changes
4. Add or update tests as needed
5. Update documentation as needed
6. Ensure all tests pass
7. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Git
- Docker (optional, for infrastructure)

### Backend Setup

```bash
# Clone your fork
git clone https://github.com/your-username/EYESON.git
cd EYESON/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your settings

# Run the API
uvicorn src.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=src --cov-report=html

# Frontend tests
cd frontend
npm test
```

## Style Guides

### Git Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, semicolons, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Build process or auxiliary tool changes

Example:
```
feat(voice): add support for Spanish voice prompts

- Add Spanish translations for all 15 prompts
- Update voice router to handle 'es' language code
- Add tests for Spanish TTS synthesis

Refs: #123
```

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use Black for formatting: `black src/`
- Use isort for import sorting: `isort src/`

### TypeScript/JavaScript Style Guide

- Use TypeScript for all new code
- Follow the [Airbnb Style Guide](https://github.com/airbnb/javascript)
- Use Prettier for formatting
- Use ESLint for linting

## Project Structure

```
eyeson-production/
├── backend/
│   ├── src/
│   │   ├── api/          # API route handlers
│   │   ├── core/         # Core configuration
│   │   ├── models/       # Database models
│   │   ├── services/     # Business logic
│   │   └── utils/        # Utility functions
│   └── tests/            # Test suite
├── frontend/
│   └── src/
│       ├── components/   # React components
│       ├── hooks/        # Custom hooks
│       ├── services/     # API clients
│       └── utils/        # Utilities
├── ml-service/           # ML inference service
└── infrastructure/       # Terraform, K8s configs
```

## Testing

### Writing Tests

- All new code should have tests
- Aim for >80% code coverage
- Use pytest for backend tests
- Use Jest and React Testing Library for frontend

### Test Naming

```python
# Backend
def test_create_session_success():
    """Test successful session creation."""
    pass

def test_create_session_invalid_language():
    """Test session creation with invalid language code."""
    pass
```

```typescript
// Frontend
describe('VoicePlayer', () => {
  it('should play audio when prompted', () => {
    // test code
  });
});
```

## Documentation

- Update the README.md if you change functionality
- Add docstrings to all public functions
- Update API documentation (OpenAPI spec is auto-generated)
- Add comments for complex logic

## Open Source Components

When contributing code that uses or modifies open source components:

1. Ensure license compatibility (MIT, Apache 2.0 preferred)
2. Attribute the original authors
3. Document any modifications made

## Questions?

Feel free to open an issue with your question or reach out to the maintainers.

Thank you for contributing! 🎉
