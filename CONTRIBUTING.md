# Contributing to Kafka-Spark-Hudi Data Pipeline

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful, inclusive, and professional in all interactions.

## How to Contribute

### 1. Fork and Clone
```bash
git clone https://github.com/your-username/Data-Pipeline-with-Kafka-Spark-Hudi-Polaris.git
cd Data-Pipeline-with-Kafka-Spark-Hudi-Polaris
```

### 2. Create a Branch
```bash
git checkout -b feature/your-feature-name
```

### 3. Make Changes

#### Code Style
- Follow **PEP 8** for Python code
- Use **Black** for formatting: `black src/ tests/ --line-length=100`
- Run **flake8** for linting: `flake8 src/ tests/ --max-line-length=100`
- Add **type hints** to all functions
- Write **comprehensive docstrings**

#### Testing
- Add tests for new features in `tests/unit/` or `tests/integration/`
- Run tests: `pytest tests/ -v`
- Ensure test coverage: `pytest tests/ --cov=src`

#### Documentation
- Update `README.md` for user-facing changes
- Update `LOCAL_SETUP.md` for setup changes
- Add docstrings to all new functions/classes

### 4. Commit Changes
Use **conventional commits**:
```bash
git commit -m "feat: add new feature"
git commit -m "fix: resolve bug in streaming processor"
git commit -m "docs: update setup guide"
git commit -m "test: add unit tests for validation"
```

**Commit Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions/changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

### 5. Push and Create PR
```bash
git push origin feature/your-feature-name
```
Then create a Pull Request on GitHub.

## Development Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install black flake8 pytest pytest-cov

# Install pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install

# Start infrastructure
docker-compose up -d

# Run tests
pytest tests/ -v
```

### Pre-commit Hooks (Recommended)

Pre-commit hooks automatically check your code before each commit:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

**What pre-commit checks:**
- ✅ Trailing whitespace removal
- ✅ End-of-file fixing
- ✅ YAML/JSON validation
- ✅ Large file detection
- ✅ Merge conflict detection
- ✅ Debug statement detection
- ✅ Black formatting
- ✅ isort import sorting
- ✅ flake8 linting
- ✅ Bandit security scanning
- ✅ Secrets detection

## Pull Request Guidelines

### PR Checklist
- [ ] Code follows PEP 8 style guide
- [ ] Code is formatted with Black
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages follow conventional commits
- [ ] No merge conflicts

### PR Description
Include:
- **What**: Brief description of changes
- **Why**: Reason for changes
- **How**: Implementation approach
- **Testing**: How you tested the changes

## Areas for Contribution

### High Impact
- Add more data validation rules
- Improve error handling and recovery
- Add performance optimizations
- Enhance monitoring and alerting

### Medium Impact
- Add more unit and integration tests
- Improve documentation with examples
- Add support for more data sources
- Implement data quality checks

### Good First Issues
- Fix typos in documentation
- Add code comments
- Improve error messages
- Add example scripts

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
