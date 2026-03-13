# 🚀 GitHub Repo Analyzer

> A powerful Python tool to analyze GitHub repository statistics, health metrics, and generate comprehensive reports.

[![PyPI version](https://badge.fury.io/py/github-repo-analyzer.svg)](https://badge.fury.io/py/github-repo-analyzer)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ Features

### 📊 Comprehensive Analysis
- Repository statistics (stars, forks, issues, size, license, topics)
- Health score calculation (0-100) with detailed factor breakdown
- Activity metrics (commits, pull requests, contributors)
- Community engagement metrics (issue comments, forks/stars ratio)
- CI/CD detection

### 🔄 Multi-Repository Comparison
- Compare health scores across multiple repositories
- Identify best/worst performers
- Summary statistics and rankings

### 📤 Export Capabilities
- Export reports to JSON
- Export to CSV for spreadsheet analysis
- Automatic filename generation with timestamps

### ⚙️ Configuration Support
- Customizable health score weights via config file
- Adjustable inactive threshold
- Caching for faster repeated analysis

### 🖥️ Command-Line Interface
Easy-to-use CLI with subcommands:
```bash
# Analyze a single repository
repo-analyzer analyze owner/repo --token YOUR_TOKEN

# Compare multiple repositories
repo-analyzer compare owner/repo1 owner/repo2 --token YOUR_TOKEN

# Export to CSV
repo-analyzer analyze owner/repo --export csv

# Use configuration file
repo-analyzer analyze owner/repo --config config.json
```

## 📦 Installation

### From PyPI (once published)
```bash
pip install github-repo-analyzer
```

### From source
```bash
git clone https://github.com/unn-Known1/github-repo-analyzer.git
cd github-repo-analyzer
pip install -r requirements.txt
pip install -e .
```

## 🔧 Usage

### Python API

```python
from github_repo_analyzer import RepoAnalyzer

# Initialize with your GitHub token
analyzer = RepoAnalyzer(token="your_github_token_here")

# Analyze a single repository
report = analyzer.analyze_repo("owner/repository")
print(f"Health Score: {report['health_score']}/100")
print(f"Stars: {report['repository']['stars']}")
print(f"Description: {report['repository']['description']}")

# Compare multiple repositories
comparison = analyzer.compare_repos([
    "owner/repo1",
    "owner/repo2",
    "owner/repo3"
])
print(f"Average health: {comparison['summary']['avg_health_score']}")

# Export report to JSON
analyzer.export_report(report, format='json', output_path='report.json')

# Export to CSV
analyzer.export_report(report, format='csv', output_path='report.csv')
```

### Command Line

```bash
# Set token as environment variable
export GITHUB_TOKEN="your_token_here"

# Analyze
repo-analyzer analyze owner/repository

# With verbose output
repo-analyzer analyze owner/repository --verbose

# Compare
repo-analyzer compare owner/repo1 owner/repo2

# Export results
repo-analyzer analyze owner/repository --export csv --output my_report.csv
```

## 📋 Configuration

Create a `config.json` file to customize behavior:

```json
{
  "health_weights": {
    "missing_readme": 20,
    "no_license": 15,
    "inactive": 25,
    "issues_disabled": 10,
    "missing_description": 5,
    "no_topics": 5
  },
  "max_inactive_days": 180,
  "cache_ttl_seconds": 600
}
```

Usage:
```bash
repo-analyzer analyze owner/repository --config config.json
```

## 📖 Health Scoring Algorithm

The health score (0-100) is calculated based on:

| Factor | Penalty |
|--------|---------|
| Missing README | -15 |
| No license | -10 |
| Inactive >90 days | -20 |
| Issues disabled | -10 |
| Missing description | -5 |
| No topics | -5 |
| **Bonus**: Has CI/CD | +5 |

**Customize weights** via config file!

## 📊 Output Example

```json
{
  "repository": {
    "name": "owner/repo",
    "description": "A sample repository",
    "url": "https://github.com/owner/repo",
    "stars": 100,
    "forks": 25,
    "open_issues": 5,
    "language": "Python",
    "license": "MIT"
  },
  "health_score": 85,
  "health_factors": ["Has CI/CD"],
  "activity": {
    "total_commits": 1500,
    "recent_commits_30d": 45,
    "contributor_count": 12
  },
  "community": {
    "open_issues": 5,
    "average_issue_comments": 3.2,
    "forks_to_stars_ratio": 0.23
  },
  "analysis_timestamp": "2026-03-13T12:00:00"
}
```

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- [Issue Tracker](https://github.com/unn-Known1/github-repo-analyzer/issues)
- [Releases](https://github.com/unn-Known1/github-repo-analyzer/releases)
- [Documentation](https://github.com/unn-Known1/github-repo-analyzer/tree/main/docs)

## 🙏 Acknowledgments

- Built with [PyGithub](https://github.com/PyGithub/PyGithub)
- Inspired by the need for quick repository health assessment
