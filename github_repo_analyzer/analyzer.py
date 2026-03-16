#!/usr/bin/env python3
"""
GitHub Repository Analyzer - Advanced repository health, security, CI/CD, and trends
"""

import json
import csv
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import argparse
import sys

try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    print("ERROR: PyGithub not installed. Run: pip install PyGithub")
    sys.exit(1)

import matplotlib.pyplot as plt
import matplotlib
from .logger import get_logger
from .cache import SQLiteCache
from .rate_limiter import RateLimiter
import subprocess
import re
import os
from .local_analyzer import LocalRepo, LocalDependencyAnalyzer
from concurrent.futures import ThreadPoolExecutor, as_completed

matplotlib.use('Agg')  # Non-interactive backend


class RepoAnalyzer:
    """Analyze GitHub repositories for health, security, CI/CD, and comprehensive metrics"""
    
    def __init__(self, token: str, config_path: Optional[str] = None):
        self.g = Github(token)
        self.logger = get_logger(__name__)
        self.config = self._load_config(config_path) if config_path else {}
        self._apply_env_overrides()
        cache_db = self.config.get('cache_db_path', '.github_repo_analyzer_cache.db')
        cache_ttl = self.config.get('cache_ttl_seconds', 600)
        self.cache = SQLiteCache(db_path=cache_db, default_ttl=cache_ttl)
        low_thresh = self.config.get('rate_limit_low_threshold', 100)
        self.rate_limiter = RateLimiter(self.g, low_threshold=low_thresh)

    def _load_config(self, path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _apply_env_overrides(self):
            """Apply environment variable overrides to config."""
            env_overrides = {
                'GITHUB_ANALYZER_CACHE_TTL': ('cache_ttl_seconds', int),
                'GITHUB_ANALYZER_CACHE_DB': ('cache_db_path', str),
                'GITHUB_ANALYZER_RATE_LIMIT_LOW': ('rate_limit_low_threshold', int),
                'GITHUB_ANALYZER_MAX_INACTIVE_DAYS': ('max_inactive_days', int),
            }
            for env_var, (config_key, cast_func) in env_overrides.items():
                value = os.environ.get(env_var)
                if value:
                    try:
                        self.config[config_key] = cast_func(value)
                    except Exception as e:
                        self.logger.debug(f"Failed to parse environment override {env_var}={value}: {e}")
    
    def analyze_repo(self, repo_name: str, use_cache: bool = True) -> Dict[str, Any]:
            """Analyze a single repository comprehensively"""
            cache_key = f"analyze:{repo_name}"
            if use_cache:
                cached = self.cache.get(cache_key)
                if cached is not None:
                    self.logger.debug(f"Cache hit for {repo_name}")
                    return cached

            # If the provided path is a local directory, analyze it directly
            if os.path.isdir(repo_name):
                return self._analyze_local(repo_name, use_cache)
            try:
                self.rate_limiter.check()
                repo = self.g.get_repo(repo_name)

                stats = {
                    'name': repo.full_name,
                    'description': repo.description or '',
                    'url': repo.html_url,
                    'stars': repo.stargazers_count,
                    'forks': repo.forks_count,
                    'open_issues': repo.open_issues_count,
                    'closed_issues': repo.get_issues(state='closed').totalCount,
                    'language': repo.language,
                    'created_at': repo.created_at.isoformat() if repo.created_at else None,
                    'updated_at': repo.updated_at.isoformat() if repo.updated_at else None,
                    'pushed_at': repo.pushed_at.isoformat() if repo.pushed_at else None,
                    'default_branch': repo.default_branch,
                    'size_kb': repo.size,
                    'license': repo.license.name if repo.license else None,
                    'topics': repo.get_topics(),
                    'subscribers_count': repo.subscribers_count,
                    'watchers_count': repo.watchers_count,
                    'network_count': repo.network_count,
                    'archived': repo.archived,
                    'disabled': repo.disabled,
                }

                health = self._calculate_health(repo)
                activity = self._get_activity_metrics(repo)
                security = self._get_security_metrics(repo)
                cicd = self._get_cicd_metrics(repo)
                test_coverage = self._detect_test_coverage(repo)
                community = self._get_community_metrics(repo)

                self.rate_limiter.check()
                traffic = self._get_traffic_metrics(repo)

                result = {
                    'repository': stats,
                    'health_score': health['score'],
                    'health_factors': health['factors'],
                    'activity': activity,
                    'community': community,
                    'traffic': traffic,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'security': security,
                    'cicd': cicd,
                    'test_coverage': test_coverage,
                    'analyzed_by': self.g.get_user().login
                }

                if use_cache:
                    self.cache.set(cache_key, result)
                return result

            except Exception as e:
                self.logger.error(f"Error analyzing {repo_name}: {e}")
                return {'error': str(e), 'repo': repo_name}
        def _calculate_health(self, repo) -> Dict[str, Any]:
        self.rate_limiter.check()
        """Calculate repository health score (0-100)"""
        score = 100
        factors = []
        penalties = self.config.get('health_weights', {})
        
        try:
            repo.get_contents("README.md")
        except:
            score -= penalties.get('missing_readme', 15)
            factors.append("Missing README")
        
        if not repo.license:
            score -= penalties.get('no_license', 10)
            factors.append("No license")
        
        max_inactive_days = self.config.get('max_inactive_days', 90)
        if repo.updated_at:
            days_since_update = (datetime.now() - repo.updated_at.replace(tzinfo=None)).days
            if days_since_update > max_inactive_days:
                score -= penalties.get('inactive', 20)
                factors.append(f"Inactive for {days_since_update} days")
        else:
            score -= penalties.get('no_updates', 10)
            factors.append("No update history")
        
        if not repo.has_issues:
            score -= penalties.get('issues_disabled', 10)
            factors.append("Issues disabled")
        
        if not repo.description:
            score -= penalties.get('missing_description', 5)
            factors.append("Missing description")
        
        topics = repo.get_topics()
        if len(topics) == 0:
            score -= penalties.get('no_topics', 5)
            factors.append("No topics")
        
        # CI/CD detection bonus
        ci_files = ['.travis.yml', '.github/workflows', 'Jenkinsfile', '.circleci', 'azure-pipelines.yml']
        has_ci = any(self._file_exists(repo, f) for f in ci_files)
        if has_ci:
            score += 5
            factors.append("Has CI/CD")
        
        return {
            'score': max(0, min(100, score)),
            'factors': factors
        }
    
    def _file_exists(self, repo, path: str) -> bool:
        try:
            repo.get_contents(path)
            return True
        except:
            return False
    
    def _get_security_metrics(self, repo) -> Dict[str, Any]:
        self.rate_limiter.check()
        """Extract security-related metrics from GitHub"""
        try:
            security_metrics = {
                'dependabot_alerts_count': 0,
                'code_scanning_alerts_count': 0,
                'has_security_policy': False,
                'security_policy_file': None,
                'has_dependency_graph': False,
                'vulnerable_dependencies': 0,
            }
            
            # Check for security policy (SECURITY.md)
            try:
                security_policy = repo.get_contents("SECURITY.md")
                security_metrics['has_security_policy'] = True
                security_metrics['security_policy_file'] = "SECURITY.md"
            except:
                try:
                    repo.get_contents(".security/SECURITY.md")
                    security_metrics['has_security_policy'] = True
                    security_metrics['security_policy_file'] = ".security/SECURITY.md"
                except:
                    pass
            
            # Dependabot alerts (requires repo permissions)
            try:
                if hasattr(repo, 'get_dependabot_alerts'):
                    alerts = repo.get_dependabot_alerts()
                    security_metrics['dependabot_alerts_count'] = alerts.totalCount if hasattr(alerts, 'totalCount') else len(list(alerts))
                    security_metrics['vulnerable_dependencies'] = security_metrics['dependabot_alerts_count']
                    security_metrics['has_dependency_graph'] = True
            except:
                pass
            
            # Code scanning alerts
            try:
                if hasattr(repo, 'get_code_scanning_alerts'):
                    code_alerts = repo.get_code_scanning_alerts()
                    security_metrics['code_scanning_alerts_count'] = code_alerts.totalCount if hasattr(code_alerts, 'totalCount') else len(list(code_alerts))
            except:
                pass
            
            return security_metrics
        except Exception as e:
            return {'error': str(e), 'dependabot_alerts_count': 0, 'code_scanning_alerts_count': 0, 'has_security_policy': False}
    
    def _get_activity_metrics(self, repo) -> Dict[str, Any]:
        self.rate_limiter.check()
        """Extract activity-related metrics"""
        try:
            commits = repo.get_commits()
            total_commits = commits.totalCount
            
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_commits = 0
            try:
                for commit in commits:
                    if commit.commit.author.date < thirty_days_ago:
                        break
                    recent_commits += 1
            except:
                pass
            
            open_prs = repo.get_pulls(state='open').totalCount
            closed_prs = repo.get_pulls(state='closed').totalCount
            
            contributors = repo.get_contributors()
            contributor_count = contributors.totalCount if hasattr(contributors, 'totalCount') else len(list(contributors))
            
            return {
                'total_commits': total_commits,
                'recent_commits_30d': recent_commits,
                'open_pull_requests': open_prs,
                'closed_pull_requests': closed_prs,
                'contributor_count': contributor_count,
                'last_commit': commits[0].commit.author.date.isoformat() if total_commits > 0 else None,
                'last_push': repo.pushed_at.isoformat() if repo.pushed_at else None,
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_community_metrics(self, repo) -> Dict[str, Any]:
        self.rate_limiter.check()
            """Extract community engagement metrics"""
            try:
                contributors = repo.get_contributors()
                contributor_logins = []
                total_commits = 0
                for c in contributors:
                    contributor_logins.append(c.login)
                    total_commits += c.contributions

                # Pull request statistics
                pulls = repo.get_pulls(state='all')
                prs_open = 0
                prs_closed = 0
                prs_merged = 0
                for pr in pulls:
                    if pr.state == 'open':
                        prs_open += 1
                    else:
                        if pr.merged_at:
                            prs_merged += 1
                        else:
                            prs_closed += 1

                # Issue statistics
                issues = repo.get_issues(state='all')
                issues_open = 0
                issues_closed = 0
                for issue in issues:
                    if issue.state == 'open':
                        issues_open += 1
                    else:
                        issues_closed += 1

                return {
                    'contributors_count': len(contributor_logins),
                    'top_contributors': contributor_logins[:5],
                    'total_commits': total_commits,
                    'prs_open': prs_open,
                    'prs_closed': prs_closed,
                    'prs_merged': prs_merged,
                    'pr_merge_rate': round(prs_merged / (prs_merged + prs_closed) * 100, 1) if (prs_merged + prs_closed) > 0 else 0.0,
                    'issues_open': issues_open,
                    'issues_closed': issues_closed,
                    'issue_response_days': None,  # Could be implemented with comment timestamps
                }
            except Exception as e:
                self.logger.error(f"Error fetching community metrics: {e}")
                return {'error': str(e)}
    
    def _get_community_metrics(self, repo) -> Dict[str, Any]:
        """Extract community engagement metrics"""
        try:
            open_issues = repo.open_issues_count
            issues = repo.get_issues(state='all')
            issue_avg_comments = 0
            if open_issues > 0:
                comments = sum(issue.comments for issue in issues[:100])
                sampled = min(100, issues.totalCount)
                issue_avg_comments = comments / sampled if sampled > 0 else 0
            
            forks_ratio = repo.forks_count / max(repo.stargazers_count, 1)
            
            return {
                'open_issues': open_issues,
                'average_issue_comments': round(issue_avg_comments, 2),
                'forks_to_stars_ratio': round(forks_ratio, 3),
                'has_wiki': repo.has_wiki,
                'has_downloads': repo.has_downloads,
                'has_pages': repo.has_pages,
                'has_projects': repo.has_projects,
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_cicd_metrics(self, repo) -> Dict[str, Any]:
        self.rate_limiter.check()
        """Analyze CI/CD pipeline usage and health"""
        try:
            cicd_metrics = {
                'has_github_actions': False,
                'workflows_count': 0,
                'workflow_file': None,
                'ci_systems': [],
                'has_tests_command': False,
                'test_command_detected': None,
            }
            
            # GitHub Actions
            try:
                workflows = repo.get_contents(".github/workflows")
                cicd_metrics['has_github_actions'] = True
                cicd_metrics['workflows_count'] = len(workflows)
                if workflows:
                    cicd_metrics['workflow_file'] = workflows[0].name
                cicd_metrics['ci_systems'].append('GitHub Actions')
            except:
                pass
            
            # Other CI systems
            ci_files = {
                'Travis CI': '.travis.yml',
                'CircleCI': '.circleci/config.yml',
                'GitLab CI': '.gitlab-ci.yml',
                'Jenkins': 'Jenkinsfile',
                'Azure Pipelines': 'azure-pipelines.yml',
                'AppVeyor': 'appveyor.yml',
                'Bitrise': 'bitrise.yml',
            }
            for ci_name, ci_file in ci_files.items():
                try:
                    repo.get_contents(ci_file)
                    cicd_metrics['ci_systems'].append(ci_name)
                except:
                    pass
            
            # Detect test command
            test_patterns = ['pytest', 'tox', 'npm test', 'make test', 'dotnet test', 'go test', 'mvn test', 'gradle test']
            if cicd_metrics['has_github_actions'] and workflows:
                try:
                    wf_content = workflows[0].decoded_content.decode()
                    for pattern in test_patterns:
                        if pattern.lower() in wf_content.lower():
                            cicd_metrics['has_tests_command'] = True
                            cicd_metrics['test_command_detected'] = pattern
                            break
                except:
                    pass
            
            if not cicd_metrics['has_tests_command']:
                test_indicators = ['tests/', 'test/', 'spec/', 'pytest.ini', 'tox.ini', 'Makefile', 'Rakefile']
                for indicator in test_indicators:
                    try:
                        if '/' in indicator:
                            repo.get_contents(indicator)
                            cicd_metrics['has_tests_command'] = True
                            cicd_metrics['test_command_detected'] = 'tests directory'
                            break
                        else:
                            repo.get_contents(indicator)
                            cicd_metrics['has_tests_command'] = True
                            cicd_metrics['test_command_detected'] = indicator
                            break
                    except:
                        pass
            
            return cicd_metrics
        except Exception as e:
            return {'error': str(e), 'has_github_actions': False, 'ci_systems': []}
    
    def _get_traffic_metrics(self, repo) -> Dict[str, Any]:
            """Get repository traffic metrics (views, clones, referrers)"""
            self.rate_limiter.check()
            try:
                traffic = {
                    'views': 0,
                    'unique_views': 0,
                    'clones': 0,
                    'unique_clones': 0,
                    'top_referrers': [],
                    'top_paths': [],
                }

                # Get views
                try:
                    views = repo.get_views_traffic()
                    traffic['views'] = views.count
                    traffic['unique_views'] = views.uniques
                except Exception as e:
                    self.logger.debug(f"Traffic views not available: {e}")

                # Get clones
                try:
                    clones = repo.get_clones_traffic()
                    traffic['clones'] = clones.count
                    traffic['unique_clones'] = clones.uniques
                except Exception as e:
                    self.logger.debug(f"Traffic clones not available: {e}")

                # Get top referrers (last 14 days)
                try:
                    referrers = repo.get_top_referrers()
                    for ref in referrers[:5]:
                        traffic['top_referrers'].append({
                            'referrer': ref.referrer,
                            'count': ref.count,
                            'uniques': ref.uniques,
                        })
                except Exception as e:
                    self.logger.debug(f"Traffic referrers not available: {e}")

                # Get top paths
                try:
                    paths = repo.get_top_paths()
                    for p in paths[:5]:
                        traffic['top_paths'].append({
                            'path': p.path,
                            'title': p.title,
                            'count': p.count,
                            'uniques': p.uniques,
                        })
                except Exception as e:
                    self.logger.debug(f"Traffic paths not available: {e}")

                return traffic
            except Exception as e:
                return {'error': str(e)}
    
    def _detect_test_coverage(self, repo) -> Dict[str, Any]:
        """Detect test coverage reporting"""
        try:
            coverage_metrics = {
                'has_coverage_report': False,
                'coverage_file': None,
                'coverage_service': None,
                'coverage_percentage': None,
            }
            
            coverage_files = [
                'coverage.xml',
                '.coverage',
                'htmlcov/',
                'coverage/',
                'lcov.info',
                'jacoco.xml',
            ]
            for cov_file in coverage_files:
                try:
                    repo.get_contents(cov_file)
                    coverage_metrics['has_coverage_report'] = True
                    coverage_metrics['coverage_file'] = cov_file
                    break
                except:
                    pass
            
            service_files = [
                ('.codecov.yml', 'Codecov'),
                ('codecov.yml', 'Codecov'),
                ('.coveralls.yml', 'Coveralls'),
                ('coveralls.yml', 'Coveralls'),
            ]
            for file_name, service_name in service_files:
                try:
                    repo.get_contents(file_name)
                    coverage_metrics['coverage_service'] = service_name
                    break
                except:
                    pass
            
            try:
                package_json = repo.get_contents("package.json")
                content = package_json.decoded_content.decode()
                if 'nyc' in content or '"coverage"' in content:
                    coverage_metrics['coverage_service'] = 'NYC (Istanbul)'
            except:
                pass
            
            return coverage_metrics
        except Exception as e:
            return {'error': str(e), 'has_coverage_report': False}
    
    def compare_repos(self, repo_names: List[str]) -> Dict[str, Any]:
        """Compare multiple repositories"""
        results = []
        for repo_name in repo_names:
            analysis = self.analyze_repo(repo_name)
            if 'error' not in analysis:
                results.append(analysis)
        
        if not results:
            return {'error': 'No valid repositories analyzed'}
        
        summary = {
            'repositories_compared': len(results),
            'avg_health_score': sum(r['health_score'] for r in results) / len(results),
            'highest_health': max(results, key=lambda x: x['health_score'])['repository']['name'],
            'lowest_health': min(results, key=lambda x: x['health_score'])['repository']['name'],
            'most_stars': max(results, key=lambda x: x['repository']['stars'])['repository']['name'],
            'most_forked': max(results, key=lambda x: x['repository']['forks'])['repository']['name'],
            'avg_security_alerts': sum(r.get('security', {}).get('dependabot_alerts_count', 0) for r in results) / len(results),
            'repos_with_ci': sum(1 for r in results if r.get('cicd', {}).get('has_github_actions', False)) / len(results) * 100,
            'repos_with_coverage': sum(1 for r in results if r.get('test_coverage', {}).get('has_coverage_report', False)) / len(results) * 100,
        }
        
        return {
            'comparison_timestamp': datetime.now().isoformat(),
            'repositories': [r['repository']['name'] for r in results],
            'summary': summary,
            'detailed': results
        }
    
    def generate_html_report(self, analysis: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Generate an interactive HTML report with charts"""
        if output_path is None:
            repo_name = analysis['repository']['name'].replace('/', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"report_{repo_name}_{timestamp}.html"
        
        try:
            # Create charts
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            
            # Health Score Gauge
            ax1 = axes[0, 0]
            health = analysis['health_score']
            colors = ['#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff']
            if health >= 75:
                color = colors[3]
            elif health >= 50:
                color = colors[2]
            elif health >= 25:
                color = colors[1]
            else:
                color = colors[0]
            ax1.barh([0], [health], color=color, height=0.6)
            ax1.set_xlim(0, 100)
            ax1.set_title(f'Health Score: {health}/100', fontsize=14, fontweight='bold')
            ax1.set_xlabel('Score')
            ax1.set_yticks([])
            ax1.text(health + 2, 0, f'{health}', va='center', fontweight='bold', fontsize=12)
            
            # Metrics Overview
            ax2 = axes[0, 1]
            metrics = ['Stars', 'Forks', 'Issues', 'Contributors']
            values = [
                analysis['repository']['stars'],
                analysis['repository']['forks'],
                analysis['repository']['open_issues'],
                analysis['activity'].get('contributor_count', 0)
            ]
            bars = ax2.bar(metrics, values, color=['#4d96ff', '#6bcb77', '#ffd93d', '#ff6b6b'])
            ax2.set_title('Key Metrics')
            ax2.set_ylabel('Count')
            for bar, val in zip(bars, values):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.01,
                        str(val), ha='center', va='bottom', fontsize=9)
            
            # CI/CD & Security
            ax3 = axes[1, 0]
            security_data = [
                analysis.get('security', {}).get('dependabot_alerts_count', 0),
                analysis.get('security', {}).get('code_scanning_alerts_count', 0),
                1 if analysis.get('security', {}).get('has_security_policy', False) else 0,
            ]
            sec_labels = ['Dependabot Alerts', 'Code Scanning', 'Security Policy']
            colors_sec = ['#ff6b6b' if x > 0 else '#cccccc' for x in security_data]
            ax3.bar(sec_labels, security_data, color=colors_sec)
            ax3.set_title('Security Status')
            ax3.set_ylabel('Count / Present')
            
            # CI/CD & Coverage
            ax4 = axes[1, 1]
            cicd_cov_data = [
                1 if analysis.get('cicd', {}).get('has_github_actions', False) else 0,
                1 if analysis.get('cicd', {}).get('has_tests_command', False) else 0,
                1 if analysis.get('test_coverage', {}).get('has_coverage_report', False) else 0,
            ]
            cc_labels = ['GitHub Actions', 'Tests Detected', 'Coverage Report']
            colors_cc = ['#4d96ff' if x else '#cccccc' for x in cicd_cov_data]
            ax4.bar(cc_labels, cicd_cov_data, color=colors_cc)
            ax4.set_title('CI/CD & Coverage')
            ax4.set_ylabel('Available')
            ax4.set_ylim(0, 1.2)
            
            plt.tight_layout()
            chart_path = output_path.replace('.html', '_charts.png')
            plt.savefig(chart_path, dpi=100, bbox_inches='tight')
            plt.close()
            
            # Generate HTML content
            html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Repository Analysis – {analysis['repository']['name']}</title>
    <style>
        :root {{ --primary: #2563eb; --success: #22c55e; --warning: #f59e0b; --danger: #ef4444; --gray: #6b7280; --bg: #f8fafc; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: #1e293b; line-height: 1.6; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); overflow: hidden; }}
        header {{ background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 30px; }}
        .repo-info {{ display: flex; align-items: center; gap: 20px; }}
        .repo-info img {{ width: 100px; height: 100px; border-radius: 12px; border: 3px solid white; }}
        .repo-details h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .repo-details p {{ opacity: 0.9; font-size: 16px; }}
        .repo-details a {{ color: white; text-decoration: underline; }}
        .content {{ padding: 30px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 25px 0; }}
        .metric {{ background: var(--bg); padding: 20px; border-radius: 10px; text-align: center; border-left: 4px solid var(--primary); }}
        .metric h4 {{ margin: 0 0 8px 0; font-size: 12px; text-transform: uppercase; color: var(--gray); letter-spacing: 0.5px; }}
        .metric .value {{ font-size: 28px; font-weight: 700; color: #1e293b; }}
        .score-card {{ background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 25px; border-radius: 12px; text-align: center; margin: 25px 0; }}
        .score-card h2 {{ margin: 0 0 10px 0; font-size: 18px; font-weight: 500; }}
        .score-card .score {{ font-size: 56px; font-weight: 700; line-height: 1; }}
        .factors {{ background: #fef3c7; border: 1px solid #fbbf24; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        .factors h3 {{ color: #92400e; margin-bottom: 10px; }}
        .factors ul {{ margin-left: 20px; color: #78350f; }}
        .charts img {{ width: 100%; border: 1px solid #e2e8f0; border-radius: 10px; margin: 10px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: var(--bg); font-weight: 600; color: var(--gray); text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; }}
        .positive {{ color: var(--success); font-weight: 600; }}
        .negative {{ color: var(--danger); font-weight: 600; }}
        .neutral {{ color: var(--gray); }}
        .section-title {{ font-size: 20px; font-weight: 600; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin: 30px 0 15px; }}
        .rec-item {{ background: white; border: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; margin: 10px 0; }}
        .rec-item h5 {{ margin: 0 0 5px 0; color: #1e293b; }}
        .rec-item p {{ margin: 0; color: #64748b; font-size: 14px; }}
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; margin-left: 8px; }}
        .badge.critical {{ background: #fecaca; color: #991b1b; }}
        .badge.high {{ background: #fed7aa; color: #9a3412; }}
        .badge.medium {{ background: #fef3c7; color: #92400e; }}
        .badge.low {{ background: #dcfce7; color: #166534; }}
        footer {{ background: var(--bg); padding: 20px; text-align: center; color: var(--gray); font-size: 13px; border-top: 1px solid #e2e8f0; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="repo-info">
                <img src="https://github.com/{analysis['repository']['name'].split('/')[0]}.png?size=100" alt="Owner Avatar">
                <div class="repo-details">
                    <h1>{analysis['repository']['name']}</h1>
                    <p>{analysis['repository']['description'] or 'No description provided'}</p>
                    <p><a href="{analysis['repository']['url']}" target="_blank">{analysis['repository']['url']}</a></p>
                </div>
            </div>
        </header>
        
        <div class="content">
            <!-- Metrics Grid -->
            <div class="metrics-grid">
                <div class="metric"><h4>Stars</h4><div class="value">{analysis['repository']['stars']}</div></div>
                <div class="metric"><h4>Forks</h4><div class="value">{analysis['repository']['forks']}</div></div>
                <div class="metric"><h4>Open Issues</h4><div class="value">{analysis['repository']['open_issues']}</div></div>
                <div class="metric"><h4>Size (KB)</h4><div class="value">{analysis['repository']['size_kb']}</div></div>
                <div class="metric"><h4>Language</h4><div class="value">{analysis['repository']['language'] or 'N/A'}</div></div>
                <div class="metric"><h4>License</h4><div class="value">{analysis['repository']['license'] or 'N/A'}</div></div>
                <div class="metric"><h4>Contributors</h4><div class="value">{analysis['activity'].get('contributor_count', 0)}</div></div>
                <div class="metric"><h4>Commits (30d)</h4><div class="value">{analysis['activity'].get('recent_commits_30d', 0)}</div></div>
            </div>
            
            <!-- Health Score -->
            <div class="score-card">
                <h2>Overall Health Score</h2>
                <div class="score">{analysis['health_score']}/100</div>
                <p>Analyzed on {analysis['analysis_timestamp'][:10]} by {analysis['analyzed_by']}</p>
            </div>
            
            <!-- Health Factors -->
            <h2 class="section-title">Health Factors</h2>
            <div class="factors">
                <ul>
                    {''.join(f'<li>{factor}</li>' for factor in analysis['health_factors']) if analysis['health_factors'] else '<li>No issues detected</li>'}
                </ul>
            </div>
            
            <!-- Charts -->
            <h2 class="section-title">Visual Analytics</h2>
            <div class="charts">
                <img src="{chart_path}" alt="Analysis Charts">
            </div>
            
            <!-- Security & CI/CD -->
            <h2 class="section-title">Security & CI/CD Status</h2>
            <table>
                <tr><th>Metric</th><th>Value</th><th>Status</th></tr>
                <tr><td>Dependabot Alerts</td><td>{analysis.get('security', {}).get('dependabot_alerts_count', 0)}</td><td class="{'negative' if analysis.get('security', {}).get('dependabot_alerts_count', 0) > 0 else 'positive'}">{'Needs Attention' if analysis.get('security', {}).get('dependabot_alerts_count', 0) > 0 else 'Clean'}</td></tr>
                <tr><td>Code Scanning Alerts</td><td>{analysis.get('security', {}).get('code_scanning_alerts_count', 0)}</td><td class="{'negative' if analysis.get('security', {}).get('code_scanning_alerts_count', 0) > 0 else 'positive'}">{'Needs Attention' if analysis.get('security', {}).get('code_scanning_alerts_count', 0) > 0 else 'Clean'}</td></tr>
                <tr><td>Security Policy</td><td>Present</td><td class="{'positive' if analysis.get('security', {}).get('has_security_policy', False) else 'negative'}">{'Yes' if analysis.get('security', {}).get('has_security_policy', False) else 'No'}</td></tr>
                <tr><td>GitHub Actions</td><td>Enabled</td><td class="{'positive' if analysis.get('cicd', {}).get('has_github_actions', False) else 'negative'}">{'Yes' if analysis.get('cicd', {}).get('has_github_actions', False) else 'No'}</td></tr>
                <tr><td>CI Systems</td><td colspan="2">{', '.join(analysis.get('cicd', {}).get('ci_systems', ['None']))}</td></tr>
                <tr><td>Test Command Detected</td><td>{analysis.get('cicd', {}).get('test_command_detected', 'Not detected')}</td><td class="{'positive' if analysis.get('cicd', {}).get('has_tests_command', False) else 'neutral'}">{'Found' if analysis.get('cicd', {}).get('has_tests_command', False) else 'Not Found'}</td></tr>
                <tr><td>Coverage Report</td><td>{analysis.get('test_coverage', {}).get('coverage_file', 'None')}</td><td class="{'positive' if analysis.get('test_coverage', {}).get('has_coverage_report', False) else 'neutral'}">{'Yes' if analysis.get('test_coverage', {}).get('has_coverage_report', False) else 'No'}</td></tr>
                <tr><td>Coverage Service</td><td colspan="2">{analysis.get('test_coverage', {}).get('coverage_service', 'Not configured')}</td></tr>
            </table>
            
            <!-- Activity Metrics -->
            <h2 class="section-title">Activity & Community</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Commits</td><td>{analysis['activity'].get('total_commits', 0)}</td></tr>
                <tr><td>Recent Commits (30d)</td><td>{analysis['activity'].get('recent_commits_30d', 0)}</td></tr>
                <tr><td>Open Pull Requests</td><td>{analysis['activity'].get('open_pull_requests', 0)}</td></tr>
                <tr><td>Closed Pull Requests</td><td>{analysis['activity'].get('closed_pull_requests', 0)}</td></tr>
                <tr><td>Last Commit</td><td>{analysis['activity'].get('last_commit', 'N/A')[:19] if analysis['activity'].get('last_commit') else 'N/A'}</td></tr>
                <tr><td>Last Push</td><td>{analysis['activity'].get('last_push', 'N/A')[:19] if analysis['activity'].get('last_push') else 'N/A'}</td></tr>
                <tr><td>Average Issue Comments</td><td>{analysis['community'].get('average_issue_comments', 0)}</td></tr>
                <tr><td>Forks to Stars Ratio</td><td>{analysis['community'].get('forks_to_stars_ratio', 0)}</td></tr>
                <tr><td>Has Wiki</td><td class="{'positive' if analysis['community'].get('has_wiki', False) else 'neutral'}">{'Yes' if analysis['community'].get('has_wiki', False) else 'No'}</td></tr>
                <tr><td>Has Pages</td><td class="{'positive' if analysis['community'].get('has_pages', False) else 'neutral'}">{'Yes' if analysis['community'].get('has_pages', False) else 'No'}</td></tr>
            </table>
            
            <!-- Recommendations -->
            <h2 class="section-title">Recommendations</h2>
            <div class="recommendations">
            '''.strip()
            
            # Add recommendations
            recommendations = self.generate_recommendations(analysis)
            for rec in recommendations:
                priority_class = rec['priority'].lower()
                html += f'''<div class="rec-item">
                    <h5>{rec['category']} <span class="badge {priority_class}">{rec['priority']}</span></h5>
                    <p>{rec['suggestion']}</p>
                </div>'''
            
            if not recommendations:
                html += '''<div class="rec-item">
                    <h5>All Good! 🎉</h5>
                    <p>No immediate recommendations. Keep up the great work!</p>
                </div>'''
            
            html += f'''</div>
            
            <footer>
                <p>Generated by GitHub Repo Analyzer on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Analysis version: Enhanced with Security, CI/CD, Coverage, and Trends</p>
            </footer>
        </div>
    </div>
</body>
</html>'''
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            return f"HTML report generated: {output_path}"
        except Exception as e:
            return f"HTML report generation failed: {str(e)}"
    
    def generate_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        health = analysis['health_score']
        if health < 80:
            recommendations.append({
                'category': 'Health',
                'priority': 'High' if health < 50 else 'Medium',
                'suggestion': f'Improve repository health score (current: {health}/100). Review factors below.'
            })
        
        if 'Missing README' in analysis.get('health_factors', []):
            recommendations.append({
                'category': 'Documentation',
                'priority': 'High',
                'suggestion': 'Add a comprehensive README.md file with project description, installation instructions, and usage examples.'
            })
        
        if not analysis['repository'].get('license'):
            recommendations.append({
                'category': 'Legal',
                'priority': 'High',
                'suggestion': 'Add an open source license (e.g., MIT, Apache 2.0, GPL) to clarify usage rights.'
            })
        
        sec = analysis.get('security', {})
        if sec.get('dependabot_alerts_count', 0) > 0:
            recommendations.append({
                'category': 'Security',
                'priority': 'Critical',
                'suggestion': f'Fix {sec["dependabot_alerts_count"]} vulnerable dependencies. Review and update dependencies via Dependabot.'
            })
        
        if not sec.get('has_security_policy'):
            recommendations.append({
                'category': 'Security',
                'priority': 'Medium',
                'suggestion': 'Add a SECURITY.md file describing how to report security vulnerabilities responsibly.'
            })
        
        cicd = analysis.get('cicd', {})
        if not cicd.get('has_github_actions') and not cicd.get('ci_systems'):
            recommendations.append({
                'category': 'CI/CD',
                'priority': 'Medium',
                'suggestion': 'Set up continuous integration (e.g., GitHub Actions) to run tests automatically on push.'
            })
        
        if not cicd.get('has_tests_command'):
            recommendations.append({
                'category': 'Testing',
                'priority': 'High',
                'suggestion': 'Add automated tests and configure CI to run them (e.g., pytest, tox, npm test).'
            })
        
        cov = analysis.get('test_coverage', {})
        if cicd.get('has_tests_command') and not cov.get('has_coverage_report'):
            recommendations.append({
                'category': 'Testing',
                'priority': 'Low',
                'suggestion': 'Consider adding code coverage reporting (e.g., Codecov, Coveralls) to track test completeness.'
            })
        
        if analysis['activity'].get('recent_commits_30d', 0) == 0:
            recommendations.append({
                'category': 'Maintenance',
                'priority': 'High',
                'suggestion': 'Repository appears inactive (no commits in 30 days). Consider updating, archiving, or deprecating.'
            })
        
        if analysis['repository']['archived']:
            recommendations.append({
                'category': 'Maintenance',
                'priority': 'Info',
                'suggestion': 'Repository is archived. Unarchive if you plan to continue development.'
            })
        
        return recommendations
    
    def analyze_organization(self, org_name: str, include_forks: bool = False) -> Dict[str, Any]:
        """Analyze all repositories in an organization"""
        try:
            org = self.g.get_organization(org_name)
            repos = org.get_repos(type='all' if include_forks else 'public')
            
            analyses = []
            for repo in repos:
                if not include_forks and repo.fork:
                    continue
                analysis = self.analyze_repo(f"{org_name}/{repo.name}")
                if 'error' not in analysis:
                    analyses.append(analysis)
            
            if analyses:
                summary = {
                    'organization': org_name,
                    'total_repos': len(analyses),
                    'avg_health_score': sum(a['health_score'] for a in analyses) / len(analyses),
                    'total_stars': sum(a['repository']['stars'] for a in analyses),
                    'repos_with_ci': sum(1 for a in analyses if a.get('cicd', {}).get('has_github_actions', False)),
                    'repos_with_coverage': sum(1 for a in analyses if a.get('test_coverage', {}).get('has_coverage_report', False)),
                    'repos_with_security_alerts': sum(1 for a in analyses if a.get('security', {}).get('dependabot_alerts_count', 0) > 0),
                    'repos_with_security_policy': sum(1 for a in analyses if a.get('security', {}).get('has_security_policy', False)),
                }
                top_repos = sorted(analyses, key=lambda x: x['health_score'], reverse=True)[:5]
                summary['healthiest_repos'] = [r['repository']['name'] for r in top_repos]
            else:
                summary = {'error': 'No repositories found'}
            
            return {
                'org_analysis_timestamp': datetime.now().isoformat(),
                'summary': summary,
                'repositories': analyses,
            }
        except Exception as e:
            return {'error': str(e), 'organization': org_name}
    
    def load_historical_data(self, history_file: str) -> List[Dict]:
        """Load previous analysis results for trend comparison"""
        try:
            with open(history_file, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def compare_with_history(self, current_analysis: Dict[str, Any], history: List[Dict]) -> Dict[str, Any]:
        """Compare current analysis with historical data to show trends"""
        if not history:
            return {'trend_available': False, 'message': 'No historical data available'}
        
        repo_name = current_analysis['repository']['name']
        matching_history = [h for h in history if h.get('repository', {}).get('name') == repo_name]
        
        if not matching_history:
            return {'trend_available': False, 'message': f'No historical data for {repo_name}'}
        
        prev_analysis = sorted(matching_history, key=lambda x: x.get('analysis_timestamp', ''), reverse=True)[0]
        
        trends = {
            'health_score_change': current_analysis['health_score'] - prev_analysis['health_score'],
            'stars_change': current_analysis['repository']['stars'] - prev_analysis['repository']['stars'],
            'forks_change': current_analysis['repository']['forks'] - prev_analysis['repository']['forks'],
            'open_issues_change': current_analysis['repository']['open_issues'] - prev_analysis['repository']['open_issues'],
            'contributor_change': current_analysis['activity'].get('contributor_count', 0) - prev_analysis['activity'].get('contributor_count', 0),
        }
        
        trends['health_trend'] = 'improving' if trends['health_score_change'] > 0 else 'declining' if trends['health_score_change'] < 0 else 'stable'
        
        return {
            'trend_available': True,
            'previous_analysis_date': prev_analysis['analysis_timestamp'],
            'trends': trends
        }
    
    def export_report(self, analysis: Dict[str, Any], output_format: str = 'json', output_path: Optional[str] = None) -> str:
        """Export analysis report to file (json, csv, html)"""
        if output_path is None:
            repo_name = analysis['repository']['name'].replace('/', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if output_format == 'html':
                output_path = f"report_{repo_name}_{timestamp}.html"
            else:
                output_path = f"report_{repo_name}_{timestamp}.{output_format}"
        
        try:
            if output_format == 'json':
                with open(output_path, 'w') as f:
                    json.dump(analysis, f, indent=2, default=str)
                return f"Report exported to {output_path}"
            elif output_format == 'csv':
                flat = self._flatten_dict(analysis)
                with open(output_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(flat.keys())
                    writer.writerow(flat.values())
                return f"Report exported to {output_path}"
            elif output_format == 'html':
                msg = self.generate_html_report(analysis, output_path)
                if 'failed' in msg.lower():
                    return msg
                return msg
            else:
                return f"Unsupported format: {output_format}"
        except Exception as e:
            return f"Export failed: {str(e)}"
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """Flatten nested dictionary for CSV export"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, str(v)))
            else:
                items.append((new_key, v))
        return dict(items)


def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(
        description="GitHub Repository Analyzer - Comprehensive analysis with security, CI/CD, and trends",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze owner/repo --token YOUR_TOKEN
  %(prog)s compare owner/repo1 owner/repo2 --token YOUR_TOKEN --export html
  %(prog)s analyze owner/repo --recommendations --history previous.json
  %(prog)s org your-org --token YOUR_TOKEN --include-forks
        """
    )
    
    parser.add_argument('action', choices=['analyze', 'compare', 'org', 'version'],
                        help='Action to perform')
    parser.add_argument('targets', nargs='*', help='Repository name(s) or organization (e.g., owner/repo or org-name)')
    parser.add_argument('--token', '-t', help='GitHub personal access token')
    parser.add_argument('--config', '-c', help='Path to config JSON file')
    parser.add_argument('--export', '-e', choices=['json', 'csv', 'html'],
                        help='Export report format')
    parser.add_argument('--output', '-o', help='Output file path (default: auto-generated)')
    parser.add_argument('--no-cache', action='store_true', help='Disable caching')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--recommendations', '-r', action='store_true', help='Show improvement recommendations')
    parser.add_argument('--history', '-H', help='JSON file with previous analyses for trend comparison')
    parser.add_argument('--include-forks', '-f', action='store_true', help='Include forks in organization analysis')
    
    args = parser.parse_args()
    
    import os
    token = args.token or os.environ.get('GITHUB_TOKEN')
    if not token:
        parser.error("GitHub token required. Use --token or set GITHUB_TOKEN environment variable")
    
    analyzer = RepoAnalyzer(token, config_path=args.config)
    
    if args.action == 'version':
        import github_repo_analyzer
        print(f"GitHub Repo Analyzer v{github_repo_analyzer.__version__}")
        print("Enhanced Edition – Security, CI/CD, Coverage, Trends, HTML Reports")
        sys.exit(0)
    
    if args.action == 'analyze':
        if not args.targets:
            parser.error("analyze requires at least one repository")
        
        for repo in args.targets:
            print(f"\n🔍 Analyzing: {repo}")
            result = analyzer.analyze_repo(repo, use_cache=not args.no_cache)
            
            if 'error' in result:
                print(f"  ❌ ERROR: {result['error']}")
                continue
            
            print(f"  💯 Health Score: {result['health_score']}/100")
            print(f"  ⭐ Stars: {result['repository']['stars']}, 🍴 Forks: {result['repository']['forks']}")
            print(f"  🐛 Issues: {result['repository']['open_issues']} open, {result['repository']['closed_issues']} closed")
            print(f"  📊 Activity: {result['activity'].get('recent_commits_30d', 0)} commits (30d), {result['activity'].get('contributor_count', 0)} contributors")
            
            # Security & CI/CD quick stats
            sec = result.get('security', {})
            cicd = result.get('cicd', {})
            cov = result.get('test_coverage', {})
            print(f"  🔒 Security: {sec.get('dependabot_alerts_count', 0)} dependabot alerts, {sec.get('code_scanning_alerts_count', 0)} code scanning")
            print(f"  🤖 CI/CD: {'GitHub Actions' if cicd.get('has_github_actions') else 'None'}, Tests: {'Yes' if cicd.get('has_tests_command') else 'No'}")
            print(f"  📈 Coverage: {'Yes' if cov.get('has_coverage_report') else 'No'} ({cov.get('coverage_service', 'None')})")
            
            if result['health_factors']:
                print(f"  ⚠️  Factors: {', '.join(result['health_factors'])}")
            
            if args.export:
                export_msg = analyzer.export_report(result, args.export, args.output)
                print(f"  📤 {export_msg}")
            
            if args.recommendations:
                print("\n  💡 RECOMMENDATIONS:")
                recs = analyzer.generate_recommendations(result)
                for rec in recs:
                    icon = {'Critical': '🔴', 'High': '🟠', 'Medium': '🟡', 'Low': '🟢', 'Info': '🔵'}.get(rec['priority'], '⚪')
                    print(f"    [{icon}] {rec['category']}: {rec['suggestion']}")
            
            if args.history:
                history = analyzer.load_historical_data(args.history)
                trends = analyzer.compare_with_history(result, history)
                if trends.get('trend_available'):
                    t = trends['trends']
                    print(f"\n  📈 TRENDS (since {trends['previous_analysis_date'][:10]})")
                    print(f"    Health: {t['health_score_change']:+d} ({t['health_trend']}), Stars: {t['stars_change']:+d}, Forks: {t['forks_change']:+d}")
                    print(f"    Issues: {t['open_issues_change']:+d}, Contributors: {t['contributor_change']:+d}")
    
    elif args.action == 'compare':
        if len(args.targets) < 2:
            parser.error("compare requires at least 2 repositories")
        
        print(f"🔬 Comparing {len(args.targets)} repositories...")
        comparison = analyzer.compare_repos(args.targets)
        
        if 'error' in comparison:
            print(f"❌ ERROR: {comparison['error']}")
            sys.exit(1)
        
        print("\n" + "="*70)
        print("COMPARISON SUMMARY")
        print("="*70)
        print(f"Repositories: {', '.join(comparison['repositories'])}")
        print(f"Average Health: {comparison['summary']['avg_health_score']:.1f}/100")
        print(f"Healthiest: {comparison['summary']['highest_health']}")
        print(f"Lowest Health: {comparison['summary']['lowest_health']}")
        print(f"Most Starred: {comparison['summary']['most_stars']}")
        print(f"Most Forked: {comparison['summary']['most_forked']}")
        print(f"Avg Security Alerts: {comparison['summary']['avg_security_alerts']:.1f}")
        print(f"Repos with CI: {comparison['summary']['repos_with_ci']:.1f}%")
        print(f"Repos with Coverage: {comparison['summary']['repos_with_coverage']:.1f}%")
        print("="*70)
        
        if args.export:
            export_msg = analyzer.export_report(comparison, args.export, args.output)
            print(f"\n📤 {export_msg}")
    
    elif args.action == 'org':
        if not args.targets:
            parser.error("org requires organization name")
        org_name = args.targets[0]
        
        print(f"🏢 Analyzing organization: {org_name}")
        org_analysis = analyzer.analyze_organization(org_name, include_forks=args.include_forks)
        
        if 'error' in org_analysis:
            print(f"❌ ERROR: {org_analysis['error']}")
            sys.exit(1)
        
        summary = org_analysis['summary']
        print("\n" + "="*70)
        print("ORGANIZATION SUMMARY")
        print("="*70)
        print(f"Organization: {summary['organization']}")
        print(f"Total Repositories: {summary['total_repos']}")
        print(f"Average Health Score: {summary['avg_health_score']:.1f}/100")
        print(f"Total Stars Earned: {summary['total_stars']:,}")
        print(f"Repos with CI/CD: {summary['repos_with_ci']}/{summary['total_repos']}")
        print(f"Repos with Coverage: {summary['repos_with_coverage']}/{summary['total_repos']}")
        print(f"Repos with Security Alerts: {summary['repos_with_security_alerts']}/{summary['total_repos']}")
        print(f"Repos with Security Policy: {summary['repos_with_security_policy']}/{summary['total_repos']}")
        print(f"Top 5 Healthiest: {', '.join(summary['healthiest_repos'])}")
        print("="*70)
        
        if args.export:
            export_msg = analyzer.export_report(org_analysis, args.export, args.output)
            print(f"\n📤 {export_msg}")
    
    else:
        parser.error(f"Unknown action: {args.action}")


if __name__ == "__main__":
    main()
