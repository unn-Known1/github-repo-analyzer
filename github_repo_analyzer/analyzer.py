#!/usr/bin/env python3
"""
GitHub Repository Analyzer - Advanced repository health and statistics tool
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


class RepoAnalyzer:
    """Analyze GitHub repositories for health, activity, and metrics"""
    
    def __init__(self, token: str, config_path: Optional[str] = None):
        self.g = Github(token)
        self.config = self._load_config(config_path) if config_path else {}
        self.cache = {}
        
    def _load_config(self, path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def analyze_repo(self, repo_name: str, use_cache: bool = True) -> Dict[str, Any]:
        """Analyze a single repository comprehensively"""
        cache_key = f"analyze:{repo_name}"
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]
            
        try:
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
            community = self._get_community_metrics(repo)
            
            result = {
                'repository': stats,
                'health_score': health['score'],
                'health_factors': health['factors'],
                'activity': activity,
                'community': community,
                'analysis_timestamp': datetime.now().isoformat(),
                'analyzed_by': self.g.get_user().login
            }
            
            self.cache[cache_key] = result
            return result
            
        except Exception as e:
            return {'error': str(e), 'repo': repo_name}
    
    def _calculate_health(self, repo) -> Dict[str, Any]:
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
        
        # CI/CD detection
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
    
    def _get_activity_metrics(self, repo) -> Dict[str, Any]:
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
        }
        
        return {
            'comparison_timestamp': datetime.now().isoformat(),
            'repositories': [r['repository']['name'] for r in results],
            'summary': summary,
            'detailed': results
        }
    
    def export_report(self, analysis: Dict[str, Any], output_format: str = 'json', output_path: Optional[str] = None) -> str:
        """Export analysis report to file"""
        if output_path is None:
            repo_name = analysis['repository']['name'].replace('/', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"report_{repo_name}_{timestamp}.{output_format}"
        
        try:
            if output_format == 'json':
                with open(output_path, 'w') as f:
                    json.dump(analysis, f, indent=2, default=str)
            elif output_format == 'csv':
                flat = self._flatten_dict(analysis)
                with open(output_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(flat.keys())
                    writer.writerow(flat.values())
            else:
                return f"Unsupported format: {output_format}"
            return f"Report exported to {output_path}"
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
        description="GitHub Repository Analyzer - Analyze repository health and metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze owner/repo --token YOUR_TOKEN
  %(prog)s compare owner/repo1 owner/repo2 --token YOUR_TOKEN --output comparison.json
  %(prog)s analyze owner/repo --export csv
        """
    )
    
    parser.add_argument('action', choices=['analyze', 'compare', 'version'],
                        help='Action to perform')
    parser.add_argument('repos', nargs='*', help='Repository name(s) (owner/repo)')
    parser.add_argument('--token', '-t', help='GitHub personal access token')
    parser.add_argument('--config', '-c', help='Path to config JSON file')
    parser.add_argument('--export', '-e', choices=['json', 'csv'], 
                        help='Export report format')
    parser.add_argument('--output', '-o', help='Output file path (default: auto-generated)')
    parser.add_argument('--no-cache', action='store_true', help='Disable caching')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    import os
    token = args.token or os.environ.get('GITHUB_TOKEN')
    if not token:
        parser.error("GitHub token required. Use --token or set GITHUB_TOKEN environment variable")
    
    analyzer = RepoAnalyzer(token, config_path=args.config)
    
    if args.action == 'version':
        import github_repo_analyzer
        print(f"GitHub Repo Analyzer v{github_repo_analyzer.__version__}")
        print("Enhanced Features: Multi-repo comparison, Export (JSON/CSV), Config support")
        sys.exit(0)
    
    if args.action == 'analyze':
        if not args.repos:
            parser.error("analyze requires at least one repository")
        
        for repo in args.repos:
            print(f"\nAnalyzing: {repo}")
            result = analyzer.analyze_repo(repo, use_cache=not args.no_cache)
            
            if 'error' in result:
                print(f"  ERROR: {result['error']}")
                continue
            
            print(f"  Health Score: {result['health_score']}/100")
            print(f"  Stars: {result['repository']['stars']}, Forks: {result['repository']['forks']}")
            print(f"  Issues: {result['repository']['open_issues']} open, {result['repository']['closed_issues']} closed")
            print(f"  Activity: {result['activity']['recent_commits_30d']} commits (30d), {result['activity']['contributor_count']} contributors")
            if result['health_factors']:
                print(f"  Health Factors: {', '.join(result['health_factors'])}")
            
            if args.export:
                export_msg = analyzer.export_report(result, args.export, args.output)
                print(f"  {export_msg}")
    
    elif args.action == 'compare':
        if len(args.repos) < 2:
            parser.error("compare requires at least 2 repositories")
        
        print(f"Comparing {len(args.repos)} repositories...")
        comparison = analyzer.compare_repos(args.repos)
        
        if 'error' in comparison:
            print(f"ERROR: {comparison['error']}")
            sys.exit(1)
        
        print("\n" + "="*60)
        print("COMPARISON SUMMARY")
        print("="*60)
        print(f"Repositories: {', '.join(comparison['repositories'])}")
        print(f"Average Health Score: {comparison['summary']['avg_health_score']:.1f}/100")
        print(f"Highest Health: {comparison['summary']['highest_health']}")
        print(f"Lowest Health: {comparison['summary']['lowest_health']}")
        print(f"Most Stars: {comparison['summary']['most_stars']}")
        print(f"Most Forked: {comparison['summary']['most_forked']}")
        print("="*60)
        
        if args.export:
            export_msg = analyzer.export_report(comparison, args.export, args.output)
            print(f"\n{export_msg}")


if __name__ == "__main__":
    main()
