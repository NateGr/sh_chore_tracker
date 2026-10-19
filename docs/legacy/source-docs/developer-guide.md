# sh-chore-tracker Developer Guide

## Overview

This guide provides comprehensive information for developers working on the sh-chore-tracker Home Assistant integration. It covers development environment setup, coding standards, testing practices, and contribution guidelines.

## Development Environment Setup

### Prerequisites

- **Python**: 3.11+
- **Home Assistant**: Core 2024.1+
- **Git**: Latest version
- **VS Code**: Recommended editor

### Repository Structure

```
ha-chore-tracker/
├── .bmad-core/               # Development methodology
├── custom_components/
│   └── sh_chore_tracker/        # Integration source code
├── docs/                     # Documentation
├── tests/                    # Unit tests
├── .vscode/                 # VS Code settings
└── README.md
```

### Development Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/NateGr/ha-chore-tracker.git
   cd ha-chore-tracker
   ```

2. **Open in VS Code**
   ```bash
   code .
   ```

### Manual Setup

1. **Create virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or
   .venv\Scripts\activate     # Windows
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements_dev.txt
   pip install -e .
   ```

3. **Set up Home Assistant**
   ```bash
   hass --config ./config
   ```

## Development Workflow

### Dev Container Rebuild Strategy

If container rebuilds are part of your workflow, avoid keeping active changes in ephemeral paths only.

- Use a sibling repo + symlink workflow for daily development.
- Prefer persistent mounts when possible.
- Use WIP commit/stash snapshots as a fallback before rebuilds.

See `docs/DEBUG_SAFETY.md` for command examples and a full decision guide.

### Branching Strategy

- **main**: Production-ready code
- **feature/**: New features (e.g., `feature/calendar-integration`)
- **bugfix/**: Bug fixes
- **hotfix/**: Critical production fixes

### Daily Development Process

1. **Pull latest changes**

   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create feature branch**

   ```bash
   git checkout -b feature/new-feature-name
   ```

3. **Make changes with hot reload**
   - Edit code in VS Code
   - Changes reflect immediately in running HA

4. **Test changes**

   ```bash
   # Run unit tests
   pytest

   # Run integration tests
   pytest tests/test_integration.py

   # Manual testing in HA UI
   ```

5. **Commit changes**

   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

6. **Push and create PR**
   ```bash
   git push origin feature/new-feature-name
   # Create pull request on GitHub
   ```

### Debugging Workflow

#### Breakpoint Debugging

1. **Set breakpoints** in VS Code (F9)
2. **Launch HA debugger** (F5)
3. **Trigger functionality** in HA UI
4. **Debug hits breakpoints** with full variable access

#### Hot Code Reloading

- **Save file** → Changes apply immediately
- **No restart required** for most changes
- **Full debugging support** during development

## Coding Standards

### Python Style Guide

Follow PEP 8 with these additions:

- **Line length**: 88 characters (Black default)
- **Imports**: Group by standard library, third-party, local
- **Type hints**: Required for all public functions
- **Docstrings**: Google style for all classes and functions

### Code Formatting

```bash
# Auto-format code
black custom_components/sh_chore_tracker/

# Sort imports
isort custom_components/sh_chore_tracker/

# Lint code
pylint custom_components/sh_chore_tracker/

# Type checking
mypy custom_components/sh_chore_tracker/
```

### Naming Conventions

- **Classes**: PascalCase (e.g., `RecurrenceEngine`)
- **Functions**: snake_case (e.g., `calculate_next_due_date`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DOMAIN`)
- **Private methods**: Leading underscore (e.g., `_calculate_interval`)

### Documentation Standards

#### Docstring Format

```python
def calculate_next_due_date(config: Dict[str, Any], completion_date: datetime) -> datetime:
    """Calculate the next due date based on recurrence configuration.

    Args:
        config: Recurrence configuration dictionary
        completion_date: Date when chore was completed

    Returns:
        Next due date as datetime object

    Raises:
        ValueError: If configuration is invalid
    """
```

#### Code Comments

- **Inline comments**: For complex logic
- **Block comments**: For algorithm explanations
- **TODO comments**: For future improvements

### Error Handling

- **Custom exceptions**: Inherit from `HomeAssistantError`
- **Logging levels**: DEBUG, INFO, WARNING, ERROR
- **User-friendly messages**: Clear error descriptions

## Testing Practices

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── test_recurrence.py       # Recurrence engine tests
├── test_config_flow.py      # Configuration flow tests
├── test_services.py         # Service call tests
├── test_sensor.py           # Entity tests
├── fixtures/
│   └── sample_configs.json  # Test data
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_recurrence.py

# Run with coverage
pytest --cov=custom_components/sh_chore_tracker

# Run integration tests
pytest -m integration
```

### Test Categories

#### Unit Tests

- **Coverage**: 100% for core logic
- **Isolation**: Mock external dependencies
- **Fast execution**: < 1 second per test

#### Integration Tests

- **HA integration**: Test with HA test framework
- **Service calls**: End-to-end service testing
- **Entity states**: Verify attribute updates

#### Manual Testing

- **Config flow**: Test in HA UI
- **Service calls**: Test via Developer Tools
- **Edge cases**: Unusual configurations

### Test Data

Use fixtures for consistent test data:

```python
@pytest.fixture
def sample_chore_config():
    return {
        "chore_name": "Test Chore",
        "recurrence_type": "interval",
        "pattern_interval": 7,
        "interval_unit": "days"
    }
```

## Architecture Guidelines

### Home Assistant Integration Patterns

- **Hub Integration**: One household config entry with one chore subentry per chore
- **Entity Coordinator**: Centralized state management
- **DataUpdateCoordinator**: Automatic refresh handling
- **Config Flow**: User-friendly setup process

### Core Components

#### RecurrenceEngine

- **Pure functions**: No side effects
- **Strategy pattern**: Extensible recurrence types
- **DateCalculator**: Complex date arithmetic

#### ChoreCoordinator

- **State management**: Single source of truth
- **Event firing**: Automation integration
- **Persistence**: HA storage API

#### ChoreEntity

- **Sensor platform**: Standard HA entity
- **Rich attributes**: Automation-friendly data
- **Status icons**: Visual status indication

### Design Principles

- **Single Responsibility**: Each class has one purpose
- **Dependency Injection**: Pass dependencies explicitly
- **Immutable Config**: Configuration doesn't change at runtime
- **Event-Driven**: State changes fire events

## Release Process

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features
- **PATCH**: Bug fixes

### Release Checklist

#### Pre-Release

- [ ] All tests passing
- [ ] Code review completed
- [ ] Documentation updated
- [ ] Changelog written

#### Release Steps

1. **Create release branch**

   ```bash
   git checkout -b release/v1.2.0
   ```

2. **Update version numbers**

   ```python
   # manifest.json
   "version": "1.2.0"
   ```

3. **Update changelog**

   ```markdown
   ## [1.2.0] - 2025-01-15

   ### Added

   - New calendar integration feature

   ### Fixed

   - Bug in recurrence calculation
   ```

4. **Create GitHub release**
   - Tag: `v1.2.0`
   - Title: "Release v1.2.0"
   - Description: Changelog content

5. **Merge to main**
   ```bash
   git checkout main
   git merge release/v1.2.0
   git push origin main
   ```

### HACS Integration

1. **Update manifest.json**

   ```json
   {
     "name": "sh-chore-tracker",
     "version": "1.2.0",
     "homeassistant": "2024.1.0"
   }
   ```

2. **Test HACS installation**
   - Clear HACS cache
   - Verify download works
   - Test installation process

## Contributing Guidelines

### Pull Request Process

1. **Fork the repository**
2. **Create feature branch**
3. **Make changes**
4. **Add tests**
5. **Update documentation**
6. **Submit pull request**

### PR Requirements

- [ ] Tests included
- [ ] Documentation updated
- [ ] Code style checks pass
- [ ] Type hints added
- [ ] Changelog updated

### Code Review Checklist

- [ ] Architecture follows guidelines
- [ ] No breaking changes without discussion
- [ ] Performance considerations addressed
- [ ] Security implications reviewed
- [ ] Error handling appropriate

## Troubleshooting

### Common Development Issues

#### Import Errors

- Check Python path
- Verify dependencies installed
- Restart language server in VS Code

#### Test Failures

```bash
# Run with verbose output
pytest -v

# Debug specific test
pytest --pdb tests/test_recurrence.py::test_weekly_pattern
```

#### HA Not Starting

- Check configuration syntax
- Verify integration loaded
- Check logs: `tail -f config/home-assistant.log`

### Getting Help

- **Issues**: GitHub Issues for bugs/features
- **Discussions**: GitHub Discussions for questions
- **Documentation**: Check existing docs first
- **Code**: Read existing implementations

## Performance Optimization

### Profiling

```python
import cProfile
cProfile.run('test_function()')
```

### Memory Usage

- Monitor entity count
- Use lazy loading for attributes
- Cache expensive calculations

### Database Performance

- Minimize storage writes
- Use atomic operations
- Batch state updates

## Security Considerations

### Input Validation

- Validate all user inputs
- Sanitize entity IDs
- Check parameter ranges

### Authentication

- Rely on HA authentication
- No external API calls
- Local data only

### Data Privacy

- No telemetry collection
- Local storage only
- Respect HA privacy settings

## Future Development

### Roadmap

- Calendar integration
- Analytics dashboard
- Mobile app companion
- Multi-user support

### Contributing Areas

- Performance optimization
- Additional recurrence patterns
- UI/UX improvements
- Internationalization

---

This guide will be updated as the project evolves. Check regularly for new information and best practices.
