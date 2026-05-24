# Contributing to MOKA AI

## Overview

Thank you for your interest in contributing to MOKA AI! This document provides guidelines and procedures for contributing to the MOKA AI project.

## Code of Conduct

All contributors are expected to:
- Be respectful and professional
- Follow coding standards
- Write clear, maintainable code
- Document code appropriately
- Write and maintain tests
- Follow security best practices

## Development Setup

### Prerequisites
- Python 3.9+
- Git
- Visual Studio Code or preferred IDE
- Basic understanding of AI/ML concepts

### Setup Process
1. Fork the repository
2. Clone your fork
3. Set up Python virtual environment
4. Install dependencies
5. Run initial tests

## Development Process

### Branching Strategy
- Main branch: Production code
- Development branches: Feature development
- Release branches: Version releases

### Code Standards
- Follow PEP 8 Python style guide
- Use type hints
- Write comprehensive docstrings
- Include unit tests
- Maintain code documentation

### Testing Requirements
All code contributions must include:
- Unit tests
- Integration tests (when applicable)
- Performance tests (for core components)

## Plugin Development

### Plugin Structure
1. Follow the plugin specification
2. Implement all required interfaces
3. Include comprehensive error handling
4. Provide rollback mechanisms
5. Include health check methods

### Plugin Testing
1. Unit tests for all functions
2. Integration tests with core system
3. Performance benchmarks
4. Security validation

## Code Review Process

### Review Criteria
- Code quality and standards
- Security considerations
- Performance implications
- Documentation completeness
- Test coverage

### Review Timeline
Code reviews should be completed within 48 hours of submission.

## Commit Guidelines

### Commit Message Format

MOKA AI follows the Conventional Commits specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation changes
- `style` — Formatting, no code change
- `refactor` — Code restructuring
- `test` — Adding/updating tests
- `chore` — Maintenance tasks
- `perf` — Performance improvements
- `ci` — CI/CD changes
- `revert` — Reverting a previous commit

**Scopes:**
- `core` — Core runtime modules
- `safety` — Safety/permission system
- `memory` — Memory modules
- `personality` — Personality system
- `localization` — Localization/Tagalog
- `config` — Configuration changes
- `tests` — Test additions/fixes

**Examples:**
```bash
# Good commits
git commit -m "feat(localization): add emotional support phrases"
git commit -m "fix(safety): correct approval queue timeout handling"
git commit -m "docs(core): clarify ModuleRegistry factory pattern"
git commit -m "test(memory): add integration tests for BehaviorMemory"

# Bad commits (avoid)
git commit -m "fixed stuff"
git commit -m "WIP"
git commit -m "update"
```

### Commit Best Practices

1. **One logical change per commit** — Don't mix unrelated changes
2. **Write meaningful descriptions** — Describe *what* and *why*, not just *what*
3. **Reference issues** — Include issue numbers in footer: `Closes #123`
4. **Keep commits atomic** — Each commit should be self-contained and testable
5. **Test before commit** — Run `scripts/test.ps1` to verify before committing

### Commit Workflow

```powershell
# 1. Create a feature branch
git checkout -b feature/my-feature

# 2. Make changes and commit
git add .
git commit -m "feat(scope): description"

# 3. Run tests before pushing
.\scripts\test.ps1

# 4. Push and create PR
git push origin feature/my-feature
```

### Pre-commit Checklist

Before every commit, verify:
- [ ] Code follows PEP 8 style guidelines
- [ ] All tests pass (`python -m pytest tests/ -v`)
- [ ] New modules include docstrings
- [ ] Logger integration added to new modules
- [ ] No placeholder or prototype code included
- [ ] Commit message follows Conventional Commits format
- [ ] Documentation updated if needed

## Pull Request Process

### PR Requirements
1. Clear description of changes
2. Related issue references
3. Test results (run `scripts/test.ps1`)
4. Documentation updates
5. Code review checklist completion

### PR Review Process
1. Automated testing validation
2. Manual code review
3. Security review
4. Performance review
5. Documentation review

## Reporting Issues

### Issue Types
- Bugs
- Feature requests
- Security vulnerabilities
- Performance issues
- Documentation improvements

### Issue Reporting
1. Clear title
2. Detailed description
3. Steps to reproduce
4. Expected vs actual behavior
5. System information
6. Screenshots (when applicable)

## Security Considerations

### Security Process
All code changes must consider:
- Input validation
- Error handling
- Permission validation
- Data protection
- Network security

### Vulnerability Reporting
Security vulnerabilities should be:
1. Reported through private channels
2. Given priority handling
3. Patched quickly
4. Disclosed responsibly

## Documentation

### Required Documentation
1. Code documentation
2. API documentation
3. User guides
4. Configuration guides
5. Deployment guides

## Testing

### Test Requirements
- All new modules require unit tests
- Safety-critical modules require 90%+ coverage
- Integration tests for service interactions
- Performance benchmarks for core components (optional)
- Security testing for permission-related code

## Release Process

### Versioning
MOKA AI follows semantic versioning:
- MAJOR version for incompatible changes
- MINOR version for feature additions
- PATCH version for bug fixes

### Release Criteria
- All tests passing
- Code review completed
- Security review completed
- Documentation updated
- Performance benchmarks met

## Community

### Communication
- GitHub issues for bug reports
- GitHub discussions for general questions
- Email for security vulnerabilities
- Community meetings for major decisions

### Recognition
Contributors will be recognized in:
- Release notes
- Contributor list
- GitHub contributors graph

## License

All contributions are licensed under the project license. By contributing, you agree to the licensing terms.