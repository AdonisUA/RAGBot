# Contributing to AI ChatBot

Thank you for your interest in contributing to AI ChatBot! We welcome all contributions from the community. Please follow these guidelines to help us maintain a high-quality, stable, and open project.

## How to Contribute
- **Fork the repository** and create your branch from `main` or `develop`.
- **Describe your changes** clearly in the pull request (PR) description.
- **Reference related issues** if applicable (e.g., `Fixes #123`).
- **Keep PRs focused**: one feature or fix per PR is preferred.

## Code Style and Standards
- **Backend (Python):**
  - Use [black](https://black.readthedocs.io/en/stable/), [isort](https://pycqa.github.io/isort/), and [flake8](https://flake8.pycqa.org/en/latest/) for formatting and linting.
  - Type annotations are required for all public functions and methods.
  - Follow PEP8 and project conventions.
- **Frontend (TypeScript/React):**
  - Use [prettier](https://prettier.io/) and [eslint](https://eslint.org/).
  - Use functional components and hooks where possible.

## Testing
- All new features and bugfixes **must be covered by tests** (unit or integration).
- Run all tests before submitting a PR:
  ```bash
  cd backend && pytest
  cd frontend && npm test
  ```
- Tests must pass in CI for the PR to be merged.

## Pull Request Checklist
- [ ] Code is formatted and linted.
- [ ] Tests are added/updated and pass.
- [ ] Documentation is updated if needed.
- [ ] PR description is clear and references issues if relevant.

## Documentation
- See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md), and [README.md](README.md) for project structure, setup, and standards.

## Communication
- For major changes, please open an issue first to discuss what you would like to change.
- Be respectful and constructive in all interactions.

---
Thank you for helping make AI ChatBot better! 