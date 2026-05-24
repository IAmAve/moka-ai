# CI/CD Pipeline Configuration for MOKA AI

## Overview

This directory contains CI/CD pipeline definitions and configurations for MOKA AI.

## Directory Structure

```
CI/
├── github-actions.yml    # GitHub Actions workflow
├── azure-pipelines.yml   # Azure DevOps pipeline (future)
└── jenkinsfile           # Jenkins pipeline (future)
```

## GitHub Actions Workflow

The GitHub Actions workflow runs on every push and pull request:

### Test Job
- Runs on Windows latest
- Installs dependencies from `requirements.txt`
- Executes full test suite with `pytest -v`
- Uploads test results as artifacts on failure

### Lint Job
- Runs `flake8` for code quality
- Runs `mypy` for type checking on core modules

### Security Job
- Runs `safety` package vulnerability scanner

## Local CI Testing

To run CI checks locally before pushing:

```powershell
# Run all tests
python -m pytest tests/ -v

# Run linting
python -m flake8 . --count --select=E9,F63,F7,F82

# Run type checking
python -m mypy core/ safety/ --ignore-missing-imports

# Run security check
pip install safety
python -m safety check
```

## Pipeline Status

[![MOKA AI CI](https://github.com/IAmAve/moka-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/IAmAve/moka-ai/actions)