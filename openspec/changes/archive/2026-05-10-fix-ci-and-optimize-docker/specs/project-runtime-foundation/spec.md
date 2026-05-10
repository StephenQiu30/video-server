## ADDED Requirements

### Requirement: Optimized Docker build
The Docker image build process SHALL be optimized for speed and size by using multi-stage builds and consolidating layers.

#### Scenario: Build stages are efficient
- **WHEN** the Docker image is built
- **THEN** it uses specific stages for API, Worker, and Web
- **AND** it minimizes the number of layers by chaining commands
- **AND** it only copies necessary files for each stage

### Requirement: CI pipeline stability
The CI pipeline SHALL be stable and correctly configured to run backend and frontend tests in an isolated environment.

#### Scenario: CI runs tests successfully
- **WHEN** a push or pull request is made to the main branch
- **THEN** the CI pipeline sets the correct `PYTHONPATH`
- **AND** it installs all necessary dependencies
- **AND** it runs backend and frontend tests to completion
