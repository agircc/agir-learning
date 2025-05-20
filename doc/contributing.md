# Contributing to AGIR Learning

Thank you for your interest in contributing to AGIR Learning! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) to foster an inclusive and respectful community.

## How to Contribute

There are many ways to contribute to the project:

1. **Report bugs**: Submit issues for any bugs you encounter
2. **Suggest features**: Submit issues for new features you'd like to see
3. **Improve documentation**: Help make our documentation more clear and comprehensive
4. **Write code**: Contribute new features or fix bugs
5. **Create examples**: Build new example scenarios to demonstrate the system's capabilities
6. **Share feedback**: Let us know how you're using the system and what could be improved

## Development Process

### Setting Up Your Development Environment

1. **Fork the repository**: Create your own fork of the repository
2. **Clone your fork**: `git clone https://github.com/your-username/agir-learning.git`
3. **Install dependencies**: Follow the [Installation Guide](installation.md)
4. **Set up pre-commit hooks**: We use pre-commit to ensure code quality
   ```bash
   pip install pre-commit
   pre-commit install
   ```

### Making Changes

1. **Create a branch**: Create a branch for your changes
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Make your changes**: Implement your changes, following the code style guidelines
3. **Add tests**: Add tests for your changes when applicable
4. **Run tests**: Ensure all tests pass
   ```bash
   pytest
   ```
5. **Commit your changes**: Write clear commit messages
   ```bash
   git commit -m "Add feature: your feature description"
   ```
6. **Push to your fork**: Push your changes to your fork
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Submit a Pull Request**: Create a pull request from your fork to the main repository

### Pull Request Guidelines

When submitting a pull request, please:

1. **Link to the issue**: Reference any related issues
2. **Describe your changes**: Provide a clear description of what your pull request does
3. **Include screenshots**: If applicable, include screenshots to demonstrate visual changes
4. **Update documentation**: Update the relevant documentation for your changes
5. **Keep PRs focused**: Each PR should address a single concern
6. **Be responsive**: Respond to feedback and questions

## Code Style Guidelines

We follow these code style guidelines:

- **Python**: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- **Documentation**: Use Markdown for documentation
- **Commit messages**: Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification
- **Type hints**: Use Python type hints where appropriate
- **Comments**: Write clear comments for complex code sections
- **Tests**: Write tests for new features and bug fixes

## Adding New Features

### Adding a New LLM Provider

1. Create a new provider file in `src/llm/providers/`
2. Implement the provider interface defined in `src/llm/base.py`
3. Register your provider in `src/llm/__init__.py`
4. Add tests for your provider in `tests/llm/providers/`
5. Update documentation to mention the new provider

### Creating New Scenario Types

1. Ensure your scenario follows the YAML format specification
2. Add example scenarios in the `scenarios/` directory
3. Update documentation to include your new scenario type
4. Consider adding tests to verify that the scenario works correctly

## Testing

We use pytest for testing. To run tests:

```bash
# Run all tests
pytest

# Run specific tests
pytest tests/path/to/test_file.py

# Run tests with coverage
pytest --cov=src
```

## Documentation

We value clear and comprehensive documentation. When contributing:

1. Update the README.md if your changes affect the main workflow
2. Update or create specific documentation files in the `doc/` directory
3. Add code comments for complex logic
4. Include docstrings for functions and classes

## Releasing

The release process is managed by maintainers. If you're a maintainer:

1. Update CHANGELOG.md with the changes
2. Update version numbers in relevant files
3. Create a new release on GitHub with release notes
4. Update documentation to reflect the new release

## Getting Help

If you need help, you can:

- **Open an issue**: For questions related to the code
- **Join our community**: Details are in the README
- **Contact maintainers**: Directly if needed for sensitive issues

## Recognition

Contributors will be recognized in the following ways:

- **CONTRIBUTORS.md**: Your name will be added to our contributors list
- **Release notes**: Significant contributions will be mentioned in release notes
- **Commit history**: Your commits will be part of the project's history

Thank you for contributing to AGIR Learning! 