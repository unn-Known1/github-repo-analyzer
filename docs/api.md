# API Reference

## `RepoAnalyzer` Class

Main class for analyzing GitHub repositories.

### `__init__(token: str, config_path: Optional[str] = None)`

Initialize the analyzer with a GitHub token.

**Parameters:**
- `token` (str): GitHub Personal Access Token
- `config_path` (Optional[str]): Path to configuration JSON file

**Example:**
```python
analyzer = RepoAnalyzer(token="your_token")
```

### `analyze_repo(repo_name: str, use_cache: bool = True) -> Dict[str, Any]`

Analyze a single repository.

**Parameters:**
- `repo_name` (str): Repository name in format `owner/repo`
- `use_cache` (bool): Use cached results if available (default: True)

**Returns:** Dictionary containing:
- `repository`: Basic repository information
- `health_score`: Integer 0-100
- `health_factors`: List of factors affecting health
- `activity`: Activity metrics
- `community`: Community engagement metrics
- `analysis_timestamp`: When analysis was performed

**Example:**
```python
result = analyzer.analyze_repo("octocat/hello-world")
print(f"Health: {result['health_score']}")
```

### `compare_repos(repo_names: List[str]) -> Dict[str, Any]`

Compare multiple repositories.

**Parameters:**
- `repo_names` (List[str]): List of repository names

**Returns:** Dictionary with comparison summary and detailed results.

**Example:**
```python
comparison = analyzer.compare_repos(["owner/repo1", "owner/repo2"])
print(f"Average health: {comparison['summary']['avg_health_score']}")
```

### `export_report(analysis: Dict, output_format: str = 'json', output_path: Optional[str] = None) -> str`

Export analysis report to file.

**Parameters:**
- `analysis` (Dict): Analysis result from `analyze_repo` or `compare_repos`
- `output_format` (str): 'json' or 'csv'
- `output_path` (Optional[str]): Output file path (auto-generated if None)

**Returns:** Confirmation message with file path.

---

## Command-Line Interface

### `repo-analyzer analyze REPO [OPTIONS]`

Analyze a repository.

**Options:**
- `--token`, `-t`: GitHub token
- `--config`, `-c`: Config file path
- `--export`, `-e`: Export format (json/csv)
- `--output`, `-o`: Output file path
- `--no-cache`: Disable caching
- `--verbose`, `-v`: Verbose output

### `repo-analyzer compare REPO1 REPO2 [OPTIONS]`

Compare multiple repositories.

**Options:** Same as analyze, plus:
- Requires at least 2 repositories

### `repo-analyzer version`

Show version information.
