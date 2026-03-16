# 🚀 GitHub Repo Analyzer

> A powerful Python tool to analyze GitHub repository statistics, health metrics, and generate comprehensive reports.

[![PyPI version](https://badge.fury.io/py/github-repo-analyzer.svg)](https://badge.fury.io/py/github-repo-analyzer)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ Features

### 📊 Comprehensive Analysis
 - **Offline local repository analysis** (no GitHub API required for local repos)
- Repository statistics (stars, forks, issues, size, license, topics)
- Health score calculation (0-100) with detailed factor breakdown
- Activity metrics (commits, pull requests, contributors)
- Community engagement metrics (issue comments, forks/stars ratio)
- CI/CD detection

### 🔒 Security Insights
- Dependabot alerts and vulnerable dependencies count
- Code scanning alerts
- Security policy detection (SECURITY.md)
- Dependency graph analysis with manifest parsing (Python, JavaScript, Ruby, Java, Go, Rust, PHP, .NET, C++)
- Identify outdated or vulnerable dependencies

### 🔄 Multi-Repository Comparison
- Compare health scores across multiple repositories
- Identify best/worst performers
- Summary statistics and rankings
- Parallel analysis for faster results (configurable workers)

 - Works with both GitHub and local repository analyses
### 📤 Export Capabilities
- Export reports to JSON, CSV, HTML, or **Markdown**
- Interactive HTML reports with charts (health gauge, metrics, security, CI/CD)
- Automatic filename generation with timestamps

### ⚙️ Configuration & Performance
- Customizable health score weights via config file
- Adjustable inactive threshold
- Persistent caching with SQLite (survives restarts)
- Configurable cache TTL and database path
- Rate limit monitoring with automatic backoff
- Verbose logging to file or console

### 🖥️ Command-Line Interface
Easy-to-use CLI with subcommands:
```bash
# Analyze a single repository
repo-analyzer analyze owner/repo --token YOUR_TOKEN

# Compare multiple repositories in parallel
repo-analyzer compare owner/repo1 owner/repo2 --workers 5

# Export to Markdown
repo-analyzer analyze owner/repo --export markdown

# Use configuration file
repo-analyzer analyze owner/repo --config config.json

# Enable verbose logging
repo-analyzer analyze owner/repo --verbose

# Disable cache
repo-analyzer analyze owner/repo --no-cache
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
### 📁 Local Repository Analysis

You can analyze a local git repository by providing a filesystem path instead of `owner/repo`. A GitHub token is still required for some metadata but can be a dummy value since no GitHub API calls are made for the core analysis.

```bash
repo-analyzer analyze /path/to/local/repo --export markdown --output local_report.md
```


```python
from github_repo_analyzer import RepoAnalyzer

# Initialize with your GitHub token
analyzer = RepoAnalyzer(token="your_github_token_here")

# Analyze a single repository
report = analyzer.analyze_repo("owner/repository")
print(f"Health Score: {report['health_score']}/100")
print(f"Stars: {report['repository']['stars']}")
print(f"Description: {report['repository']['description']}")

# Compare multiple repositories (parallel)
comparison = analyzer.compare_repos([
    "owner/repo1",
    "owner/repo2",
    "owner/repo3"
], max_workers=5)
print(f"Average health: {comparison['summary']['avg_health_score']}")

# Export report to different formats
analyzer.export_report(report, format='json', output_path='report.json')
analyzer.export_report(report, format='csv', output_path='report.csv')
analyzer.export_report(report, format='html', output_path='report.html')
analyzer.export_report(report, format='markdown', output_path='report.md')
```

### Command Line

```bash
# Set token as environment variable
export GITHUB_TOKEN="your_token_here"

# Analyze with verbose output
repo-analyzer analyze owner/repository --verbose

# Compare with parallel workers
repo-analyzer compare owner/repo1 owner/repo2 owner/repo3 --workers 5

# Export to different formats
repo-analyzer analyze owner/repository --export html
repo-analyzer analyze owner/repository --export markdown

# Compare and export
repo-analyzer compare owner/repo1 owner/repo2 --export json --output comparison.json

# Analyze organization
repo-analyzer org your-org --token YOUR_TOKEN --include-forks --export csv
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
  "cache_ttl_seconds": 600,
  "cache_db_path": ".github_repo_analyzer_cache.db",
  "rate_limit_low_threshold": 100
}
```

Usage:
```bash
repo-analyzer analyze owner/repository --config config.json
```

### Environment Variable Overrides

You can override config options using environment variables:

- `GITHUB_ANALYZER_CACHE_TTL` – cache TTL in seconds
- `GITHUB_ANALYZER_CACHE_DB` – path to SQLite cache database
- `GITHUB_ANALYZER_RATE_LIMIT_LOW` – low threshold for rate limit warnings
- `GITHUB_ANALYZER_MAX_INACTIVE_DAYS` – inactive threshold for health scoring

Example:
```bash
export GITHUB_ANALYZER_CACHE_TTL=300
export GITHUB_ANALYZER_LOG_LEVEL=DEBUG
```

## 📖 Health Scoring Algorithm

The health score (0-100) is calculated based on:

| Factor | Penalty |
|--------|---------|
| Missing README | -15 |
| No license | -10 |
| Inactive > configurable days | -20 |
| Issues disabled | -10 |
| Missing description | -5 |
| No topics | -5 |
| **Bonus**: Has CI/CD | +5 |

**Customize weights** via config file!

## 📊 Output Example (JSON)

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
  "security": {
    "dependabot_alerts_count": 2,
    "code_scanning_alerts_count": 0,
    "has_security_policy": true
  },
  "cicd": {
    "has_github_actions": true,
    "ci_systems": ["GitHub Actions"],
    "has_tests_command": true
  },
  "dependencies": {
    "manifests_found": ["requirements.txt", "Pipfile"],
    "total_dependencies": 42,
    "ecosystem_counts": {"python": 42}
  },
  "analysis_timestamp": "2026-03-13T12:00:00"
}
```

## 🚀 Recent Enhancements (v1.2.0+)

- **Persistent caching** – SQLite backend for cross-run caching
- **Rate limit handling** – Monitors GitHub API limits and auto-backoff
- **Dependency analysis** – Parses manifest files across ecosystems
- **Traffic insights** – GitHub traffic data (views, clones, referrers)
- **Parallel comparison** – Faster multi-repo analysis with ThreadPoolExecutor
- **Markdown export** – Native Markdown report generation
- **Structured logging** – Configurable log levels and file output
- **Docker support** – Containerized deployment (Dockerfile & docker-compose)
- **Environment overrides** – Configure via env vars without config files

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
