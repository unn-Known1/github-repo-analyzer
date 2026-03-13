#!/usr/bin/env python3
from github import Github
from datetime import datetime
from typing import Dict, Any

class RepoAnalyzer:
    def __init__(self, token: str):
        self.g = Github(token)
        
    def analyze_repo(self, repo_name: str) -> Dict[str, Any]:
        try:
            repo = self.g.get_repo(repo_name)
            stats = {
                'name': repo.full_name,
                'description': repo.description,
                'url': repo.html_url,
                'stars': repo.stargazers_count,
                'forks': repo.forks_count,
                'open_issues': repo.open_issues_count,
                'language': repo.language,
                'created_at': repo.created_at.isoformat() if repo.created_at else None,
                'updated_at': repo.updated_at.isoformat() if repo.updated_at else None,
                'size_kb': repo.size,
                'license': repo.license.name if repo.license else None,
                'topics': repo.get_topics(),
            }
            score = 100
            factors = []
            try: repo.get_contents("README.md")
            except: score -= 15; factors.append("Missing README")
            if not repo.license: score -= 10; factors.append("No license")
            if repo.updated_at:
                days = (datetime.now() - repo.updated_at.replace(tzinfo=None)).days
                if days > 90: score -= 20; factors.append(f"Inactive {days}d")
            else: score -= 10; factors.append("No updates")
            if not repo.has_issues: score -= 10; factors.append("Issues off")
            if not repo.description: score -= 5; factors.append("No description")
            if len(repo.get_topics()) == 0: score -= 5; factors.append("No topics")
            
            return {
                'repository': stats,
                'health_score': max(0, score),
                'health_factors': factors,
                'analysis_timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': str(e)}
