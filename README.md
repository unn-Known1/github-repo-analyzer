# GitHub Repo Analyzer

A Python tool to analyze GitHub repository statistics and health metrics.

## Features

- Repository statistics (stars, forks, issues)
- Health score calculation
- Activity metrics

## Usage

```python
from github_repo_analyzer import RepoAnalyzer
analyzer = RepoAnalyzer(token="your_token")
report = analyzer.analyze_repo("owner/repo")
print(report)
```

## License

MIT
## Documentation

See [docs](docs/index.md).
