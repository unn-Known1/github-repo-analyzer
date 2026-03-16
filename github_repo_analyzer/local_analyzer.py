"""
Local repository analysis utilities.
Provides classes to analyze a repository on the local filesystem without using GitHub API.
"""

import os
import subprocess
import re
import json
from datetime import datetime
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional


class LocalRepo:
    """Adapter for a local git repository providing a subset of PyGithub's Repo interface."""
    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        # Ensure it's a git repository
        try:
            subprocess.run(['git', '-C', self.path, 'rev-parse', '--is-inside-work-tree'],
                           capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            raise ValueError(f"Not a git repository: {self.path}")
        self.default_branch = self._detect_default_branch()
        self.size_kb = self._calculate_size_kb()
        self.license = self._detect_license()
        self.updated_at = self._git_latest_commit_date()
        self.created_at = self._git_earliest_commit_date()
        self.description = self._read_description()
        self.language = self._detect_language()
        self.topics = []
        # Flags typically used in health calculation
        self.has_issues = False
        self.has_wiki = False
        self.has_downloads = False
        self.has_pages = False
        self.has_projects = False
        self.archived = False
        self.disabled = False
        self.name = os.path.basename(self.path)
        self.url = f"file://{self.path}"

    def _git_output(self, *args) -> str:
        try:
            result = subprocess.run(['git', '-C', self.path] + list(args),
                                    capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except Exception:
            return ''

    def _detect_default_branch(self) -> str:
        branch = self._git_output('symbolic-ref', '--short', 'HEAD')
        if branch:
            return branch
        # fallback
        branch = self._git_output('rev-parse', '--abbrev-ref', 'HEAD')
        return branch or 'main'

    def _git_latest_commit_date(self) -> Optional[datetime]:
        iso = self._git_output('log', '-1', '--format=%cI')
        if iso:
            try:
                return datetime.fromisoformat(iso)
            except Exception:
                pass
        return None

    def _git_earliest_commit_date(self) -> Optional[datetime]:
        iso = self._git_output('log', '--reverse', '--format=%cI', '-1')
        if iso:
            try:
                return datetime.fromisoformat(iso)
            except Exception:
                pass
        return None

    def _calculate_size_kb(self) -> int:
        total_bytes = 0
        for root, dirs, files in os.walk(self.path):
            if '.git' in dirs:
                dirs.remove('.git')
            for file in files:
                try:
                    total_bytes += os.path.getsize(os.path.join(root, file))
                except OSError:
                    pass
        return total_bytes // 1024

    def _detect_license(self) -> Optional[Any]:
        common_licenses = ['LICENSE', 'LICENSE.md', 'COPYING', 'COPYRIGHT', 'license.txt']
        for fname in common_licenses:
            path = os.path.join(self.path, fname)
            if os.path.isfile(path):
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(2048)
                    content_lower = content.lower()
                    if 'mit' in content_lower:
                        name = 'MIT'
                    elif 'apache' in content_lower:
                        if '2.0' in content_lower or 'v2.0' in content_lower:
                            name = 'Apache-2.0'
                        else:
                            name = 'Apache'
                    elif 'gpl' in content_lower:
                        if 'v3' in content_lower or 'gplv3' in content_lower:
                            name = 'GPLv3'
                        elif 'v2' in content_lower:
                            name = 'GPLv2'
                        else:
                            name = 'GPL'
                    elif 'bsd' in content_lower:
                        name = 'BSD'
                    elif 'mpl' in content_lower:
                        name = 'MPL'
                    else:
                        name = 'Custom'
                except Exception:
                    name = 'Unknown'
                # Simple object with .name attribute
                class Lic:
                    pass
                lic = Lic()
                lic.name = name
                return lic
        return None

    def _read_description(self) -> str:
        readme_names = ['README.md', 'README.rst', 'README.txt', 'README']
        for rname in readme_names:
            rpath = os.path.join(self.path, rname)
            if os.path.isfile(rpath):
                try:
                    with open(rpath, 'r', encoding='utf-8', errors='ignore') as f:
                        first_line = f.readline().strip()
                        if first_line.startswith('#'):
                            first_line = first_line.lstrip('#').strip()
                        return first_line
                except Exception:
                    pass
        return ''

    def _detect_language(self) -> Optional[str]:
        ext_map = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript', '.jsx': 'JavaScript', '.tsx': 'TypeScript',
            '.java': 'Java', '.go': 'Go', '.rs': 'Rust', '.c': 'C', '.h': 'C/C++', '.cpp': 'C++', '.cc': 'C++',
            '.cxx': 'C++', '.hpp': 'C++', '.cs': 'C#', '.php': 'PHP', '.rb': 'Ruby', '.swift': 'Swift',
            '.kt': 'Kotlin', '.scala': 'Scala', '.m': 'Objective-C', '.sh': 'Shell', '.bash': 'Shell',
            '.html': 'HTML', '.htm': 'HTML', '.css': 'CSS', '.scss': 'SCSS', '.less': 'Less',
            '.json': 'JSON', '.xml': 'XML', '.yml': 'YAML', '.yaml': 'YAML', '.toml': 'TOML',
            '.md': 'Markdown', '.rst': 'reStructuredText', '.gradle': 'Gradle', '.groovy': 'Groovy',
            '.ps1': 'PowerShell', '.sql': 'SQL', '.lua': 'Lua', '.pl': 'Perl', '.pm': 'Perl',
            '.r': 'R', '.dart': 'Dart', '.d': 'D', '.jl': 'Julia', '.clj': 'Clojure',
            '.ex': 'Elixir', '.exs': 'Elixir', '.erl': 'Erlang', '.hrl': 'Erlang',
            '.elm': 'Elm', '.hs': 'Haskell', '.lhs': 'Haskell', '.purs': 'Purescript',
            '.v': 'V', '.zig': 'Zig', '.f90': 'Fortran', '.f95': 'Fortran', '.f03': 'Fortran',
            '.f08': 'Fortran',
        }
        counts = {}
        for root, dirs, files in os.walk(self.path):
            if '.git' in dirs:
                dirs.remove('.git')
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                lang = ext_map.get(ext)
                if lang:
                    counts[lang] = counts.get(lang, 0) + 1
        if not counts:
            return None
        return max(counts, key=counts.get)

    def get_contents(self, path: str):
        """Return a ContentFile-like object for a file, or a list of them for a directory."""
        full_path = os.path.join(self.path, path)
        if not os.path.exists(full_path):
            raise Exception(f"Path does not exist: {path}")
        if os.path.isfile(full_path):
            with open(full_path, 'rb') as f:
                content = f.read()
            return self._make_content_file(full_path, content)
        elif os.path.isdir(full_path):
            entries = []
            try:
                for entry in os.listdir(full_path):
                    entry_path = os.path.join(full_path, entry)
                    if os.path.isfile(entry_path):
                        with open(entry_path, 'rb') as f:
                            content = f.read()
                        entries.append(self._make_content_file(entry_path, content))
            except OSError:
                pass
            return entries
        else:
            raise Exception(f"Not a regular file or directory: {path}")

    def _make_content_file(self, path: str, content: bytes):
        class ContentFile:
            def __init__(self, path, content):
                self.path = path
                self.name = os.path.basename(path)
                self.decoded_content = content
        return ContentFile(path, content)

    def get_topics(self) -> List[str]:
        return self.topics


class LocalDependencyAnalyzer:
    """Analyze dependencies from a local repository's manifest files."""
    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(repo_path)
        self.dependencies = {
            'languages': {},
            'manifest_count': 0,
            'manifests': {},
            'total_dependencies': 0,
            'vulnerabilities_count': 0,
            'vulnerabilities': [],
            'cicd_aware': False,
        }

    def analyze(self) -> Dict[str, Any]:
        self._detect_languages()
        self._parse_manifests()
        self._detect_cicd_awareness()
        return self.dependencies

    def _detect_languages(self):
        self.dependencies['languages'] = self._count_languages()

    def _count_languages(self) -> Dict[str, int]:
        ext_map = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript', '.jsx': 'JavaScript', '.tsx': 'TypeScript',
            '.java': 'Java', '.go': 'Go', '.rs': 'Rust', '.c': 'C', '.h': 'C/C++', '.cpp': 'C++', '.cc': 'C++',
            '.cxx': 'C++', '.hpp': 'C++', '.cs': 'C#', '.php': 'PHP', '.rb': 'Ruby', '.swift': 'Swift',
            '.kt': 'Kotlin', '.scala': 'Scala', '.m': 'Objective-C', '.sh': 'Shell', '.bash': 'Shell',
            '.html': 'HTML', '.htm': 'HTML', '.css': 'CSS', '.scss': 'SCSS', '.less': 'Less',
            '.json': 'JSON', '.xml': 'XML', '.yml': 'YAML', '.yaml': 'YAML', '.toml': 'TOML',
            '.md': 'Markdown', '.rst': 'reStructuredText', '.gradle': 'Gradle', '.groovy': 'Groovy',
            '.ps1': 'PowerShell', '.sql': 'SQL', '.lua': 'Lua', '.pl': 'Perl', '.pm': 'Perl',
            '.r': 'R', '.dart': 'Dart', '.d': 'D', '.jl': 'Julia', '.clj': 'Clojure',
            '.ex': 'Elixir', '.exs': 'Elixir', '.erl': 'Erlang', '.hrl': 'Erlang',
            '.elm': 'Elm', '.hs': 'Haskell', '.lhs': 'Haskell', '.purs': 'Purescript',
            '.v': 'V', '.zig': 'Zig', '.f90': 'Fortran', '.f95': 'Fortran', '.f03': 'Fortran',
            '.f08': 'Fortran',
        }
        counts = {}
        for root, dirs, files in os.walk(self.repo_path):
            if '.git' in dirs:
                dirs.remove('.git')
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                lang = ext_map.get(ext)
                if lang:
                    counts[lang] = counts.get(lang, 0) + 1
        return counts

    def _parse_manifests(self):
        manifest_parsers = {
            'package.json': self._parse_package_json,
            'requirements.txt': self._parse_requirements_txt,
            'pyproject.toml': self._parse_pyproject_toml,
            'Cargo.toml': self._parse_cargo_toml,
            'go.mod': self._parse_go_mod,
            'pom.xml': self._parse_pom_xml,
            'build.gradle': self._parse_gradle,
            'build.gradle.kts': self._parse_gradle,
            'Gemfile': self._parse_gemfile,
            'composer.json': self._parse_composer_json,
            'Package.swift': self._parse_package_swift,
        }
        for filename, parser in manifest_parsers.items():
            filepath = os.path.join(self.repo_path, filename)
            if os.path.isfile(filepath):
                try:
                    parser(filepath)
                    self.dependencies['manifest_count'] += 1
                except Exception:
                    pass

    def _parse_package_json(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            deps = data.get('dependencies', {})
            dev_deps = data.get('devDependencies', {})
            all_deps = {**deps, **dev_deps}
            self.dependencies['manifests'][os.path.basename(path)] = {
                'dependencies': deps,
                'devDependencies': dev_deps,
                'version': data.get('version')
            }
            self.dependencies['total_dependencies'] += len(all_deps)
        except Exception:
            pass

    def _parse_requirements_txt(self, path):
        deps = {}
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    line = line.split(';')[0].strip()
                    parts = re.split(r'[<>=!~]', line, maxsplit=1)
                    pkg_name = parts[0].strip()
                    if '[' in pkg_name:
                        pkg_name = pkg_name.split('[')[0].strip()
                    deps[pkg_name] = line
        except Exception:
            pass
        if deps:
            self.dependencies['manifests'][os.path.basename(path)] = {
                'dependencies': deps,
                'devDependencies': {},
                'version': None
            }
            self.dependencies['total_dependencies'] += len(deps)

    def _parse_pyproject_toml(self, path):
        try:
            try:
                import tomllib
            except ImportError:
                try:
                    import toml as tomllib
                except ImportError:
                    return
            with open(path, 'rb') as f:
                data = tomllib.load(f)
        except Exception:
            return
        deps = {}
        version = None
        if 'tool' in data and 'poetry' in data['tool']:
            poetry = data['tool']['poetry']
            for k, v in poetry.get('dependencies', {}).items():
                if isinstance(v, dict):
                    version = v.get('version', '')
                else:
                    version = str(v)
                deps[k] = version
            for k, v in poetry.get('dev-dependencies', {}).items():
                if isinstance(v, dict):
                    version = v.get('version', '')
                else:
                    version = str(v)
                deps[k] = version
            version = poetry.get('version')
        elif 'project' in data and 'dependencies' in data['project']:
            for dep in data['project']['dependencies']:
                if isinstance(dep, str):
                    deps[dep] = None
        if deps:
            self.dependencies['manifests'][os.path.basename(path)] = {
                'dependencies': deps,
                'devDependencies': {},
                'version': version
            }
            self.dependencies['total_dependencies'] += len(deps)

    def _parse_cargo_toml(self, path):
        try:
            try:
                import tomllib
            except ImportError:
                try:
                    import toml as tomllib
                except ImportError:
                    return
            with open(path, 'rb') as f:
                data = tomllib.load(f)
        except Exception:
            return
        deps = data.get('dependencies', {})
        dev_deps = data.get('dev-dependencies', {})
        all_deps = {**deps, **dev_deps}
        self.dependencies['manifests'][os.path.basename(path)] = {
            'dependencies': deps,
            'devDependencies': dev_deps,
            'version': data.get('package', {}).get('version') if 'package' in data else None
        }
        self.dependencies['total_dependencies'] += len(all_deps)

    def _parse_go_mod(self, path):
        deps = {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            in_require = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('require'):
                    if '(' in stripped:
                        in_require = True
                        continue
                    else:
                        parts = stripped.split()
                        if len(parts) >= 3:
                            pkg = parts[1]
                            version = parts[2]
                            deps[pkg] = version
                elif stripped == ')' and in_require:
                    in_require = False
                elif in_require and stripped and not stripped.startswith('//'):
                    parts = stripped.split()
                    if len(parts) >= 2:
                        pkg = parts[0]
                        version = parts[1]
                        deps[pkg] = version
        except Exception:
            pass
        if deps:
            self.dependencies['manifests'][os.path.basename(path)] = {
                'dependencies': deps,
                'devDependencies': {},
                'version': None
            }
            self.dependencies['total_dependencies'] += len(deps)

    def _parse_pom_xml(self, path):
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            ns = ''
            if root.tag.startswith('{'):
                ns = root.tag.split('}')[0] + '}'
            deps = {}
            for dep in root.findall(f'.//{ns}dependencies/{ns}dependency') or root.findall('.//dependencies/dependency'):
                group_id_elem = dep.find(f'{ns}groupId')
                artifact_id_elem = dep.find(f'{ns}artifactId')
                version_elem = dep.find(f'{ns}version')
                group_id = group_id_elem.text if group_id_elem is not None else ''
                artifact_id = artifact_id_elem.text if artifact_id_elem is not None else ''
                version = version_elem.text if version_elem is not None else ''
                if group_id and artifact_id:
                    key = f"{group_id}:{artifact_id}"
                    deps[key] = version
            if deps:
                version_elem = root.find(f'{ns}version')
                version = version_elem.text if version_elem is not None else None
                self.dependencies['manifests'][os.path.basename(path)] = {
                    'dependencies': deps,
                    'devDependencies': {},
                    'version': version
                }
                self.dependencies['total_dependencies'] += len(deps)
        except Exception:
            pass

    def _parse_gradle(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            pattern = r'(?:implementation|api|compile|classpath|testImplementation|androidTestImplementation)\s+[\'"]([^\'"]+)[\'"]'
            matches = re.findall(pattern, content)
            deps = {}
            for m in matches:
                parts = m.split(':')
                if len(parts) >= 2:
                    if len(parts) == 3:
                        group, name, version = parts
                        key = f"{group}:{name}"
                        deps[key] = version
                    elif len(parts) == 2:
                        group, name = parts
                        key = f"{group}:{name}"
                        deps[key] = None
            if deps:
                self.dependencies['manifests'][os.path.basename(path)] = {
                    'dependencies': deps,
                    'devDependencies': {},
                    'version': None
                }
                self.dependencies['total_dependencies'] += len(deps)
        except Exception:
            pass

    def _parse_gemfile(self, path):
        deps = {}
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('gem'):
                        content = line[3:].strip()
                        parts = [p.strip().strip("'\"") for p in content.split(',')]
                        if parts:
                            gem_name = parts[0]
                            version = parts[1] if len(parts) > 1 else ''
                            deps[gem_name] = version
        except Exception:
            pass
        if deps:
            self.dependencies['manifests'][os.path.basename(path)] = {
                'dependencies': deps,
                'devDependencies': {},
                'version': None
            }
            self.dependencies['total_dependencies'] += len(deps)

    def _parse_composer_json(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            deps = data.get('require', {})
            dev_deps = data.get('require-dev', {})
            all_deps = {**deps, **dev_deps}
            self.dependencies['manifests'][os.path.basename(path)] = {
                'dependencies': deps,
                'devDependencies': dev_deps,
                'version': data.get('version')
            }
            self.dependencies['total_dependencies'] += len(all_deps)
        except Exception:
            pass

    def _parse_package_swift(self, path):
        deps = {}
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            pattern = r'\.package\s*\(\s*url:\s*"([^"]+)"\s*,\s*from:\s*"([^"]+)"\s*\)'
            matches = re.findall(pattern, content)
            for url, version in matches:
                name = url.rstrip('/').split('/')[-1].replace('.git', '')
                deps[name] = version
        except Exception:
            pass
        if deps:
            self.dependencies['manifests'][os.path.basename(path)] = {
                'dependencies': deps,
                'devDependencies': {},
                'version': None
            }
            self.dependencies['total_dependencies'] += len(deps)

    def _detect_cicd_awareness(self):
        ci_files = [
            '.travis.yml',
            os.path.join('.github', 'workflows'),
            os.path.join('.circleci', 'config.yml'),
            '.gitlab-ci.yml',
            'Jenkinsfile',
            'azure-pipelines.yml',
            'appveyor.yml',
        ]
        for ci in ci_files:
            full = os.path.join(self.repo_path, ci)
            if os.path.isfile(full) or os.path.isdir(full):
                self.dependencies['cicd_aware'] = True
                break
