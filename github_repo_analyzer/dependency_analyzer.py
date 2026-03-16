"""
Dependency analysis for GitHub repositories.
Parses common manifest files to extract dependency information.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class DependencyInfo:
    name: str
    version_spec: Optional[str]
    source: str  # pypi, npm, go, crates, etc.
    is_dev: bool = False
    is_optional: bool = False


class DependencyAnalyzer:
    """Analyze project dependencies from manifest files."""

    # Manifest file patterns and their parsers
    MANIFEST_FILES = {
        'requirements.txt': ('python', _parse_requirements),
        'Pipfile': ('python', _parse_pipfile),
        'pyproject.toml': ('python', _parse_pyproject_toml),
        'setup.py': ('python', _parse_setup_py),  # limited
        'package.json': ('javascript', _parse_package_json),
        'yarn.lock': ('javascript', None),  # presence indicates lock file
        'package-lock.json': ('javascript', None),
        'Gemfile': ('ruby', _parse_gemfile),
        'Gemfile.lock': ('ruby', None),
        'pom.xml': ('java', _parse_pom_xml),
        'build.gradle': ('java', _parse_gradle),
        'build.gradle.kts': ('java', _parse_gradle),
        'go.mod': ('go', _parse_go_mod),
        'Cargo.toml': ('rust', _parse_cargo_toml),
        'Cargo.lock': ('rust', None),
        'composer.json': ('php', _parse_composer_json),
        'composer.lock': ('php', None),
        'Paket.dependencies': ('dotnet', _parse_paket),
        'packages.config': ('dotnet', _parse_packages_config),
        '*.csproj': ('dotnet', _parse_csproj),  # pattern may need special handling
        'vcpkg.json': ('c++', _parse_vcpkg),
    }

    def __init__(self, repo):
        self.repo = repo
        self.manifests_found = []
        self.dependencies = []
        self.lock_files = []
        self.ecosystem_counts = {}

    def analyze(self) -> Dict[str, Any]:
        """
        Perform full dependency analysis.

        Returns:
            Dictionary with dependency metrics
        """
        try:
            self._detect_manifests()
            self._parse_dependencies()
            self._summarize()
            return self._build_result()
        except Exception as e:
            return {
                'error': str(e),
                'manifests_found': [],
                'total_dependencies': 0,
                'ecosystem_counts': {}
            }

    def _detect_manifests(self):
        """Check which manifest files exist in the repository root."""
        self.manifests_found = []
        self.lock_files = []
        for filename, (ecosystem, parser) in self.MANIFEST_FILES.items():
            try:
                if filename.startswith('*'):
                    # Pattern matching not implemented directly; skip for now
                    continue
                content = self.repo.get_contents(filename)
                if parser is None:
                    self.lock_files.append(filename)
                else:
                    self.manifests_found.append((filename, ecosystem))
            except:
                continue

    def _parse_dependencies(self):
        """Parse each detected manifest file."""
        for filename, ecosystem in self.manifests_found:
            try:
                parser = self.MANIFEST_FILES[filename][1]
                content = self.repo.get_contents(filename).decoded_content.decode('utf-8', errors='ignore')
                deps = parser(content, filename)
                for dep in deps:
                    dep_obj = DependencyInfo(
                        name=dep['name'],
                        version_spec=dep.get('version_spec'),
                        source=ecosystem,
                        is_dev=dep.get('is_dev', False),
                        is_optional=dep.get('is_optional', False)
                    )
                    self.dependencies.append(dep_obj)
            except Exception as e:
                # Log but continue
                continue

    def _summarize(self):
        """Compute summary statistics."""
        self.ecosystem_counts = {}
        for dep in self.dependencies:
            self.ecosystem_counts[dep.source] = self.ecosystem_counts.get(dep.source, 0) + 1

    def _build_result(self) -> Dict[str, Any]:
        """Build result dictionary."""
        dep_dicts = [asdict(d) for d in self.dependencies]
        return {
            'manifests_found': [m[0] for m in self.manifests_found],
            'lock_files': self.lock_files,
            'total_dependencies': len(self.dependencies),
            'ecosystem_counts': self.ecosystem_counts,
            'dependencies': dep_dicts,
        }


# Parsing functions for each file type

def _parse_requirements(content: str, filename: str) -> List[Dict]:
    """Parse requirements.txt."""
    deps = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Handle -e, -r, etc.
        if line.startswith('-e') or line.startswith('-r'):
            continue
        # Strip comments
        if '#' in line:
            line = line.split('#', 1)[0].strip()
        # Version spec: ==, >=, <=, ~=, !=, etc.
        parts = re.split(r'\s*([<>=!~]=?|===)\s*', line, maxsplit=1)
        name = parts[0].strip()
        version_spec = parts[1].strip() if len(parts) > 1 else None
        if name:
            deps.append({'name': name, 'version_spec': version_spec})
    return deps


def _parse_pipfile(content: str, filename: str) -> List[Dict]:
    """Parse Pipfile (TOML not trivial, but we can use simple regex or toml library)."""
    # We'll try to parse with toml if available; otherwise skip or use regex.
    try:
        import toml
        data = toml.loads(content)
        deps = []
        for section in ['packages', 'dev-packages']:
            if section in data:
                for name, spec in data[section].items():
                    if isinstance(spec, str):
                        version_spec = spec
                    elif isinstance(spec, dict):
                        version_spec = spec.get('version')
                    else:
                        version_spec = None
                    deps.append({
                        'name': name,
                        'version_spec': version_spec,
                        'is_dev': section == 'dev-packages'
                    })
        return deps
    except ImportError:
        # Fallback: nothing, too complex without toml
        return []


def _parse_pyproject_toml(content: str, filename: str) -> List[Dict]:
    """Parse pyproject.toml (supports Poetry, Flit, etc.)."""
    try:
        import toml
        data = toml.loads(content)
        deps = []
        # Poetry: [tool.poetry.dependencies] and [tool.poetry.group.*.dependencies]
        if 'tool' in data and 'poetry' in data['tool']:
            poetry = data['tool']['poetry']
            # Main dependencies
            if 'dependencies' in poetry:
                for name, spec in poetry['dependencies'].items():
                    if name == 'python':
                        continue
                    version_spec = _extract_poetry_version(spec)
                    deps.append({'name': name, 'version_spec': version_spec})
            # Groups (dev, etc.)
            if 'group' in poetry:
                for group_name, group_data in poetry['group'].items():
                    if 'dependencies' in group_data:
                        for name, spec in group_data['dependencies'].items():
                            version_spec = _extract_poetry_version(spec)
                            deps.append({'name': name, 'version_spec': version_spec, 'is_dev': group_name == 'dev'})
        # Flit: [tool.flit.metadata] requires?
        # Other: just return top-level project.dependencies if present
        return deps
    except ImportError:
        return []


def _extract_poetry_version(spec) -> Optional[str]:
    """Extract version string from Poetry dependency spec."""
    if isinstance(spec, str):
        return spec
    elif isinstance(spec, dict):
        if 'version' in spec:
            return spec['version']
        # Could have more complex constraints; try to combine
        parts = []
        if 'git' in spec:
            parts.append(f"git:{spec['git']}")
        if 'branch' in spec:
            parts.append(f"branch:{spec['branch']}")
        if 'tag' in spec:
            parts.append(f"tag:{spec['tag']}")
        if 'rev' in spec:
            parts.append(f"rev:{spec['rev']}")
        if parts:
            return ','.join(parts)
    return None


def _parse_setup_py(content: str, filename: str) -> List[Dict]:
    """Parse setup.py for install_requires. This is a very basic safe parse."""
    # We'll avoid executing code; use regex to find install_requires list.
    deps = []
    # Look for install_requires = [...]
    match = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if match:
        inner = match.group(1)
        # Split by commas, but strings may contain commas within quotes? handle roughly
        # Extract strings
        strings = re.findall(r'[\'"]([^\'"]+)[\'"]', inner)
        for s in strings:
            parts = re.split(r'\s*([<>=!~]=?|===)\s*', s, maxsplit=1)
            name = parts[0].strip()
            version_spec = parts[1].strip() if len(parts) > 1 else None
            deps.append({'name': name, 'version_spec': version_spec})
    return deps


def _parse_package_json(content: str, filename: str) -> List[Dict]:
    """Parse package.json."""
    try:
        data = json.loads(content)
        deps = []
        for section in ['dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies']:
            if section in data:
                is_dev = section == 'devDependencies'
                is_optional = section == 'optionalDependencies'
                for name, version in data[section].items():
                    deps.append({
                        'name': name,
                        'version_spec': version,
                        'is_dev': is_dev,
                        'is_optional': is_optional
                    })
        return deps
    except json.JSONDecodeError:
        return []


def _parse_gemfile(content: str, filename: str) -> List[Dict]:
    """Parse Ruby Gemfile."""
    deps = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Match gem 'name', 'version' or gem "name"
        match = re.match(r'''(?:gem|github|path|git)\s+['"]([^'"]+)['"]''', line, re.IGNORECASE)
        if match:
            name = match.group(1)
            # Version spec?
            version_match = re.search(r',\s*[\'"]?([>=~><!=\s\w\.]+)[\'"]?', line)
            version_spec = version_match.group(1).strip() if version_match else None
            deps.append({'name': name, 'version_spec': version_spec})
    return deps


def _parse_pom_xml(content: str, filename: str) -> List[Dict]:
    """Parse Maven pom.xml (very basic)."""
    # We'll avoid full XML parsing; use regex to extract <dependency> <groupId> + <artifactId>
    deps = []
    # Pattern: <dependency> ... <groupId>group</groupId> <artifactId>artifact</artifactId> ... </dependency>
    pattern = r'<dependency>\s*<groupId>[^<]*</groupId>\s*<artifactId>([^<]+)</artifactId>'
    for match in re.finditer(pattern, content, re.DOTALL):
        artifact_id = match.group(1).strip()
        deps.append({'name': artifact_id})
    return deps


def _parse_gradle(content: str, filename: str) -> List[Dict]:
    """Parse Gradle build file (Groovy or Kotlin)."""
    deps = []
    # Look for implementation 'group:name:version' or similar
    # Pattern: (implementation|api|testImplementation|classpath)\s+['"]([^'"]+)['"]
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        match = re.search(r'''(implementation|api|testImplementation|classpath|compileOnly|runtimeOnly)\s+['"]([^'"]+)['"]''', line, re.IGNORECASE)
        if match:
            dep_str = match.group(2)
            # Split by colon if using notation
            parts = dep_str.split(':')
            if len(parts) >= 2:
                group = parts[0]
                name = parts[1]
                version = parts[2] if len(parts) > 2 else None
                full_name = f"{group}:{name}"
                deps.append({'name': full_name, 'version_spec': version})
    return deps


def _parse_go_mod(content: str, filename: str) -> List[Dict]:
    """Parse Go mod file."""
    deps = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('require '):
            # Single or multiple?
            remainder = line[len('require '):].strip()
            if remainder.startswith('('):
                # Multi-line block - not handled simply
                continue
            else:
                # Format: module/path v1.2.3
                parts = remainder.split()
                if len(parts) >= 2:
                    name = parts[0]
                    version = parts[1]
                    deps.append({'name': name, 'version_spec': version})
        # Also parse require block with parentheses? Could iterate but skip for simplicity.
    return deps


def _parse_cargo_toml(content: str, filename: str) -> List[Dict]:
    """Parse Cargo.toml."""
    try:
        import toml
        data = toml.loads(content)
        deps = []
        if 'dependencies' in data:
            for name, spec in data['dependencies'].items():
                if isinstance(spec, str):
                    version_spec = spec
                elif isinstance(spec, dict):
                    version_spec = spec.get('version')
                else:
                    version_spec = None
                deps.append({'name': name, 'version_spec': version_spec})
        if 'dev-dependencies' in data:
            for name, spec in data['dev-dependencies'].items():
                version_spec = spec if isinstance(spec, str) else spec.get('version')
                deps.append({'name': name, 'version_spec': version_spec, 'is_dev': True})
        return deps
    except ImportError:
        return []


def _parse_composer_json(content: str, filename: str) -> List[Dict]:
    """Parse PHP composer.json."""
    try:
        data = json.loads(content)
        deps = []
        for section in ['require', 'require-dev']:
            if section in data:
                is_dev = section == 'require-dev'
                for name, version in data[section].items():
                    if name == 'php':
                        continue
                    deps.append({'name': name, 'version_spec': version, 'is_dev': is_dev})
        return deps
    except json.JSONDecodeError:
        return []


def _parse_paket(content: str, filename: str) -> List[Dict]:
    """Parse Paket dependencies."""
    deps = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Format: nuget Newtonsoft.Json ~> 13.0
        parts = line.split()
        if len(parts) >= 2:
            source = parts[0]  # nuget, github, etc.
            name = parts[1]
            version = parts[2] if len(parts) > 2 else None
            deps.append({'name': f"{source}:{name}", 'version_spec': version})
    return deps


def _parse_packages_config(content: str, filename: str) -> List[Dict]:
    """Parse packages.config (XML like)."""
    deps = []
    # Simple regex: <package id="Id" version="Version" ... />
    matches = re.findall(r'<package\s+id="([^"]+)"\s+version="([^"]+)"', content, re.IGNORECASE)
    for name, version in matches:
        deps.append({'name': name, 'version_spec': version})
    return deps


def _parse_csproj(content: str, filename: str) -> List[Dict]:
    """Parse .csproj (PackageReference)."""
    deps = []
    # Look for <PackageReference Include="PackageId" Version="Version" />
    matches = re.findall(r'<PackageReference\s+Include="([^"]+)"\s+Version="([^"]+)"', content, re.IGNORECASE)
    for name, version in matches:
        deps.append({'name': name, 'version_spec': version})
    return deps


def _parse_vcpkg(content: str, filename: str) -> List[Dict]:
    """Parse vcpkg.json."""
    try:
        data = json.loads(content)
        deps = []
        if 'dependencies' in data:
            for dep in data['dependencies']:
                if isinstance(dep, str):
                    name = dep
                    version_spec = None
                elif isinstance(dep, dict):
                    name = dep.get('name')
                    version_spec = dep.get('version')
                else:
                    continue
                deps.append({'name': name, 'version_spec': version_spec})
        return deps
    except json.JSONDecodeError:
        return []
