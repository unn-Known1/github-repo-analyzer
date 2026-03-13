# Documentation

Welcome to GitHub Repo Analyzer documentation!

## Quick Links

- [Installation](README.md#installation)
- [Usage Guide](README.md#usage)
- [API Reference](api.md)
- [Examples](examples.md)

## Getting Started

1. Install the tool:
   ```bash
   pip install -r requirements.txt
   ```

2. Get a GitHub Personal Access Token:
   - Go to GitHub → Settings → Developer settings → Personal access tokens
   - Generate new token with `repo` scope
   - Copy the token

3. Run your first analysis:
   ```bash
   export GITHUB_TOKEN="your_token_here"
   python github_repo_analyzer.py analyze owner/repo
   ```

## Features Overview

### Repository Analysis
Comprehensive analysis of:
- Basic stats (stars, forks, issues, etc.)
- Health score (0-100)
- Activity metrics
- Community engagement

### Multi-Repository Comparison
Compare multiple repos side-by-side with summary statistics.

### Export Options
- JSON: Full structured data
- CSV: Tabular format for spreadsheets

### Configuration
Customize health weights and thresholds via config file.

## Version History

- **v1.1.0** (Current): Multi-repo comparison, export, config support, CLI
- **v1.0.0**: Initial release with basic analysis features

---

For more help, open an issue on GitHub!
