from setuptools import setup, find_packages

setup(
    name="github-repo-analyzer",
    version="1.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Analyze GitHub repository health, metrics, and generate comprehensive reports",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/unn-Known1/github-repo-analyzer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PyGithub>=1.58",
        "python-dateutil>=2.8.0",
    ],
    entry_points={
        "console_scripts": [
            "repo-analyzer=github_repo_analyzer:main",
        ],
    },
    include_package_data=True,
)