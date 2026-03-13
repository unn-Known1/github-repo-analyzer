from setuptools import setup, find_packages

setup(
    name="github-repo-analyzer",
    version="1.1.0",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "PyGithub>=1.58",
        "python-dateutil>=2.8.0",
    ],
    entry_points={
        "console_scripts": [
            "repo-analyzer=github_repo_analyzer.analyzer:main",
        ],
    },
    include_package_data=True,
)