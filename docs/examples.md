# Examples

## Basic Repository Analysis

```python
from github_repo_analyzer import RepoAnalyzer

# Initialize
analyzer = RepoAnalyzer(token="your_github_token")

# Analyze a repository
report = analyzer.analyze_repo("torvalds/linux")

print(f"Repository: {report['repository']['name']}")
print(f"Description: {report['repository']['description']}")
print(f"Stars: {report['repository']['stars']:,}")
print(f"Forks: {report['repository']['forks']:,}")
print(f"Health Score: {report['health_score']}/100")
print(f"Open Issues: {report['repository']['open_issues']}")
print(f"Primary Language: {report['repository']['language']}")

if report['health_factors']:
    print("Health Factors:", ", ".join(report['health_factors']))
```

## Comparing Multiple Repositories

```python
repos_to_compare = [
    "django/django",
    "fastapi/fastapi",
    "pallets/flask"
]

comparison = analyzer.compare_repos(repos_to_compare)

print("Comparison Summary:")
print(f"Repositories: {len(comparison['repositories'])}")
print(f"Average Health: {comparison['summary']['avg_health_score']:.1f}/100")
print(f"Most Stars: {comparison['summary']['most_stars']}")
print(f"Most Forked: {comparison['summary']['most_forked']}")

# View individual results
for repo_result in comparison['detailed']:
    name = repo_result['repository']['name']
    score = repo_result['health_score']
    stars = repo_result['repository']['stars']
    print(f"{name}: {score}/100 health, {stars} stars")
```

## Exporting Reports

### Export to JSON

```python
# Export single repository analysis
report = analyzer.analyze_repo("owner/repo")
analyzer.export_report(report, format='json', output_path='report.json')
```

### Export to CSV

```python
# CSV export flattens nested structure
report = analyzer.analyze_repo("owner/repo")
analyzer.export_report(report, format='csv', output_path='report.csv')

# You can now open report.csv in Excel or Google Sheets
```

### Compare and Export

```python
comparison = analyzer.compare_repos(["owner/repo1", "owner/repo2"])
analyzer.export_report(comparison, format='json', output_path='comparison.json')
```

## Using Configuration

### Create `config.json`:

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
  "max_inactive_days": 180
}
```

### Use it:

```python
analyzer = RepoAnalyzer(token="your_token", config_path="config.json")
report = analyzer.analyze_repo("owner/repo")
```

## Command Line Examples

```bash
# Simple analysis
export GITHUB_TOKEN="your_token"
repo-analyzer analyze owner/repository

#Verbose with JSON export
repo-analyzer analyze owner/repository --verbose --export json --output analysis.json

# Compare three repositories
repo-analyzer compare owner/repo1 owner/repo2 owner/repo3

# Use custom config
repo-analyzer analyze owner/repository --config config.json

# Disable caching for fresh results
repo-analyzer analyze owner/repository --no-cache
```

## Batch Analysis Script

```python
import json
from github_repo_analyzer import RepoAnalyzer

analyzer = RepoAnalyzer(token="your_token")

# List of repositories to analyze
repos = [
    "requests/requests",
    "pallets/flask",
    "django/django",
    "fastapi/fastapi"
]

all_reports = []
for repo in repos:
    print(f"Analyzing {repo}...")
    report = analyzer.analyze_repo(repo)
    if 'error' not in report:
        all_reports.append(report)

# Save batch results
with open('batch_analysis.json', 'w') as f:
    json.dump(all_reports, f, indent=2)

print(f"Analyzed {len(all_reports)} repositories")
```

## Advanced: Custom Health Weights

```python
# Custom configuration for enterprise use
config = {
    "health_weights": {
        "missing_readme": 25,    # Heavily penalize no README
        "no_license": 20,        # License is very important
        "inactive": 15,          # Moderate penalty for inactive
        "issues_disabled": 10,
        "missing_description": 5,
        "no_topics": 5
    },
    "max_inactive_days": 120    # Consider 120 days as inactive threshold
}

# Save config
import json
with open('enterprise_config.json', 'w') as f:
    json.dump(config, f, indent=2)

# Use it
analyzer = RepoAnalyzer(token="token", config_path="enterprise_config.json")
```
