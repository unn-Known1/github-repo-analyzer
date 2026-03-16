# Usage Guide

    This guide provides detailed examples on how to use the GitHub Repo Analyzer, including new features.

    ## Installation

    ```bash
    pip install -r requirements.txt
    ```

    ## Basic CLI Usage

    ```bash
    # Single repository analysis
    python -m github_repo_analyzer analyze <owner/repo>

    # Multiple repositories (with parallel workers)
    python -m github_repo_analyzer compare repo1 repo2 repo3 --workers 4

    # Export to different formats
    python -m github_repo_analyzer analyze owner/repo --output report.json
    python -m github_repo_analyzer analyze owner/repo --output report.html
    python -m github_repo_analyzer analyze owner/repo --output report.md
    ```

    ## Using Persistent Cache

    The analyzer now supports SQLite caching to speed up repeated analyses.

    ```bash
    # Cache is enabled by default. Configure cache location and TTL via environment variables or config file.
    export GITHUB_ANALYZER_CACHE_DB=./my_cache.db
    export GITHUB_ANALYZER_CACHE_TTL=1200  # seconds
    python -m github_repo_analyzer analyze owner/repo
    ```

    You can also provide a JSON configuration file:

    ```json
    {
      "cache_db_path": "./cache.db",
      "cache_ttl_seconds": 1200,
      "rate_limit_low_threshold": 100
    }
    ```

    ```bash
    python -m github_repo_analyzer analyze owner/repo --config config.json
    ```

    ## Rate Limiting

    The tool now respects GitHub API rate limits automatically. It will back off and wait when limits are near exhaustion. You can configure the low threshold via the environment variable `GITHUB_ANALYZER_RATE_LIMIT_LOW` (default: 100 requests remaining).

    ## Local Repository Analysis

    You can analyze a local repository directory without GitHub access:

    ```bash
    python -m github_repo_analyzer /path/to/local/repo
    ```

    This runs the local analyzer to compute health, activity, and security metrics based on files and git history.

    ## Docker Deployment

    Use the provided Dockerfile to run the analyzer in a container.

    ```bash
    docker build -t repo-analyzer .
    docker run -e GITHUB_TOKEN=your_token repo-analyzer analyze owner/repo
    ```

    Or with docker-compose (persistent cache):

    ```bash
    docker-compose up analyze args="owner/repo"
    ```

    The `docker-compose.yml` mounts a local volume for the SQLite cache and supports environment variable configuration.

    ## Environment Variable Overrides

    All major settings can be set via environment variables:

    - `GITHUB_TOKEN` – GitHub personal access token (required unless `--config` provides it)
    - `GITHUB_ANALYZER_CACHE_DB` – Path to SQLite cache database
    - `GITHUB_ANALYZER_CACHE_TTL` – Cache TTL in seconds
    - `GITHUB_ANALYZER_RATE_LIMIT_LOW` – Low threshold for rate limiting (requests remaining)
    - `GITHUB_ANALYZER_MAX_INACTIVE_DAYS` – Inactivity threshold for health scoring

    ## Advanced: Dependency Graph and Vulnerability Detection

    The new dependency analyzer can parse manifest files (package.json, requirements.txt, pom.xml, Cargo.toml, go.mod, Gemfile, Pipfile, etc.) to build a dependency graph and identify potential vulnerabilities via the GitHub Advisory Database. This feature is still experimental but can be enabled programmatically:

    ```python
    from github_repo_analyzer import RepoAnalyzer
    from github_repo_analyzer.dependency_analyzer import DependencyAnalyzer

    analyzer = RepoAnalyzer(token)
    result = analyzer.analyze_repo('owner/repo')
    dep_analyzer = DependencyAnalyzer(token)
    graph = dep_analyzer.build_dependency_graph(result)
    vulns = dep_analyzer.check_vulnerabilities(result)
    ```

    This will be integrated into the full report in a future release.

    ## Troubleshooting

    - Ensure your token has `repo` scope for private repositories and `public_repo` for public.
    - If you see rate limiting errors, increase `GITHUB_ANALYZER_RATE_LIMIT_LOW` or reduce `--workers`.
    - For large repositories, consider increasing cache TTL or disabling cache with `--no-cache` (not implemented; remove `--no-cache` flag; the analyzer uses cache by default but you can skip cache check by passing `use_cache=False` via API).

    ## Logging

    The tool uses structured logging. Log level can be set via environment variable `LOG_LEVEL` (DEBUG, INFO, WARNING, ERROR). Logs are written to console and to a file `github_analyzer.log` in the working directory.

    