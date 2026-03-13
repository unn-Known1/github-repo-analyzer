# Contributing to GitHub Repo Analyzer

Thank you for your interest in contributing!

## How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Development Setup

```bash
git clone https://github.com/unn-Known1/github-repo-analyzer.git
cd github-repo-analyzer
pip install -r requirements.txt
pip install -e .
```

## Running Tests

```bash
# Analyze your own repository
repo-analyzer analyze YOUR_GITHUB/repo-name --token YOUR_TOKEN

# Compare multiple repositories
repo-analyzer compare owner/repo1 owner/repo2 --token YOUR_TOKEN
```

## Code Style

- Follow PEP 8
- Add docstrings to functions and classes
- Keep functions focused and small
- Write clear commit messages

## Reporting Issues

Please use GitHub Issues with:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Sample output/errors

## Feature Requests

Open an issue with:
- Problem statement
- Proposed solution
- Alternative approaches considered

Thank you for contributing!
