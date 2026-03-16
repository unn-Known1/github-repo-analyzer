# Changelog

## [1.2.0] - 2026-03-16

### Added
- Persistent SQLite caching with TTL and cross-run cache persistence
- Rate limit monitoring with automatic backoff to avoid GitHub API limits
- Dependency graph analysis: parses manifest files across ecosystems (Python, JavaScript, Ruby, Java, Go, Rust, PHP, .NET, C++) to list dependencies
- Security vulnerability context via Dependabot and Code Scanning alerts integration
- GitHub traffic insights: views, clones, and top referrers (when authorized)
- Parallel multi-repository comparison using ThreadPoolExecutor for speed
- Markdown export format for reports (--export markdown)
- Structured logging module with configurable levels and file output
- Environment variable overrides for configuration (e.g., GITHUB_ANALYZER_CACHE_TTL)
- Dockerfile and docker-compose support for containerized deployment
- `--workers` CLI option to control parallelism for compare command
- `--verbose` flag to enable debug logging
- New CLI options: `--no-cache` now uses persistent SQLite instead of in-memory

### Enhanced
- Health scoring algorithm refined with better CI/CD detection
- Improved error logging and reporting via logger module
- Cache uses SQLite for persistence across runs (previous in-memory only)
- Rate limiter prevents hitting GitHub API limits intelligently
- Recommendations engine extended to cover security and traffic insights
- Export system now supports HTML, JSON, CSV, and Markdown uniformly
- Code modularization: separated logger, cache, rate limiter, dependency analyzer
- Comparison summary includes ecosystem breakdown and dependency counts

### Changed
- `RepoAnalyzer.__init__` now sets up persistent cache and rate limiter automatically
- `compare_repos` signature now accepts `max_workers` parameter (default 5)
- `export_report` gained 'markdown' format support
- Analyzer now always includes 'dependencies' field in analysis results
- Default cache TTL increased to 600 seconds (10 minutes)
- `__version__` bumped to "1.2.0"

## [1.1.0] - 2026-03-13

### Added
- Multi-repository comparison feature
- Export to JSON and CSV formats
- Configuration file support (config.json)
- CLI argument parsing with argparse
- Caching support for faster repeated analysis
- Comprehensive activity metrics (commits, PRs, contributors)
- Community engagement metrics (issue comments, forks/stars ratio)
- CI/CD detection heuristic
- Setup.py for pip installable package
- Command-line interface with subcommands

### Enhanced
- Improved health scoring algorithm with configurable weights
- Better error handling and reporting
- Flattened dictionary output for CSV export
- Detailed comparison summary between repositories

### Changed
- Updated main analyzer class structure
- Improved documentation in code

## [1.0.0] - 2026-03-13

### Added
- Initial release
- Basic repository statistics (stars, forks, issues, etc.)
- Health score calculation (0-100)
- Simple activity metrics
- README and license
