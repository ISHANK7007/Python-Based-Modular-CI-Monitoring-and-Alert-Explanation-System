[build-system]
requires = ["setuptools>=45", "wheel", "setuptools_scm>=6.2"]
build-backend = "setuptools.build_meta"

[project]
name = "ci-log-analysis"
description = "CI Log Analysis System for automated root cause identification"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
dynamic = ["version"]
authors = [
    {name = "CI Log Analysis Team", email = "team@example.com"},
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Quality Assurance",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
]
dependencies = [
    "fastapi>=0.95.0",
    "pydantic>=1.10.0",
    "click>=8.1.0", 
    "rich>=13.0.0",  # For pretty CLI output
    "pyyaml>=6.0",   # For config handling
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "mypy>=1.0.0",
]
docs = [
    "mkdocs>=1.4.0",
    "mkdocs-material>=8.5.0",
]

[project.scripts]
ci-log-analysis = "ci_log_analysis.cli.main:main"

[tool.setuptools_scm]
# Use git tags for versioning

[tool.setuptools]
packages = ["ci_log_analysis"]

[tool.black]
line-length = 88
target-version = ["py310", "py311"]

[tool.isort]
profile = "black"
line_length = 88

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
python_classes = "Test*"
addopts = "--cov=ci_log_analysis"