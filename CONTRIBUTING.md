# Contributing to Expender

Thank you for considering contributing to Expender! Please read the following guidelines to help maintain a collaborative and effective workflow.

## Table of Contents

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Question or Problem?](#question-or-problem)
- [Issues and Bugs](#issues-and-bugs)
- [Feature Requests](#feature-requests)
- [Development Setup](#development-setup)
- [Code Style and Standards](#code-style-and-standards)
- [Testing](#testing)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Additional Resources](#additional-resources)

## Code of Conduct

Help to keep Expender open and inclusive. Please read and follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Question or Problem?

If you have a question or are experiencing a problem with the project, please use our structured issue templates to provide all the necessary information:

### 📋 Issue Templates Available

- **🐛 [Bug Report](.github/ISSUE_TEMPLATE/bug_report.yml)**: For reporting bugs or unexpected behavior
- **✨ [Feature Request](.github/ISSUE_TEMPLATE/feature_request.yml)**: For suggesting new features or enhancements
- **🏗️ [Infrastructure Issue](.github/ISSUE_TEMPLATE/infrastructure_issue.yml)**: For deployment, DevOps, or AWS service issues
- **🔒 [Security Issue](.github/ISSUE_TEMPLATE/security_issue.yml)**: For non-critical security improvements (use email for critical issues)
- **⚡ [Performance Issue](.github/ISSUE_TEMPLATE/performance_issue.yml)**: For performance problems or optimization requests
- **❓ [Question/Documentation](.github/ISSUE_TEMPLATE/question.yml)**: For usage questions or documentation improvements

### 🔍 Before Creating an Issue

1. **Search Existing Issues**: Check the issue tracker to see if your issue has already been reported
2. **Check Documentation**: Review the README.md and inline documentation
3. **Community Discussions**: Check GitHub Discussions for similar questions
4. **Choose the Right Template**: Select the most appropriate issue template for your situation

### 🚨 Critical Security Issues

For critical security vulnerabilities, please report them privately via email to **security@expender.app** instead of using public issue templates.

## Issues and Bugs

Structured issue templates are used to ensure consistent and comprehensive bug reporting:

### 🐛 Bug Reporting Process

1. **Use the Bug Report Template**: Click [here](.github/ISSUE_TEMPLATE/bug_report.yml) or select "Bug Report" when creating a new issue
2. **Provide Complete Information**: Fill out all relevant sections including:
   - Clear reproduction steps
   - Environment details (dev/staging/prod)
   - Affected API endpoints
   - Error messages and logs
   - Screenshots if applicable
3. **Include Context**: Describe the impact, frequency, and any workarounds
4. **Security Considerations**: Note if the bug has security implications

### 🔍 Bug Report Requirements

- **Environment Information**: Specify deployment environment and affected components
- **Reproduction Steps**: Provide clear, step-by-step instructions
- **Expected vs Actual Behavior**: Clearly describe what should happen vs what actually happens
- **Error Details**: Include HTTP status codes, error responses, and CloudWatch logs
- **Performance Impact**: Note any performance degradation or resource issues

## Feature Requests

Suggestions that improve the Expender platform are totally welcome! Use the structured feature request process:

### ✨ Feature Request Process

1. **Use the Feature Request Template**: Click [here](.github/ISSUE_TEMPLATE/feature_request.yml) or select "Feature Request" when creating a new issue
2. **Check for Existing Requests**: Search existing issues to avoid duplicates
3. **Provide Comprehensive Details**: Include:
   - Clear problem statement and motivation
   - Proposed solution and user flow
   - Technical considerations and complexity
   - Business value and success metrics
   - Acceptance criteria

### 🎯 Feature Categories

- **💰 Expense Management**: CRUD operations and data handling
- **🤖 SmartScan**: Receipt processing and categorization
- **📈 Data Export & Reporting**: CSV generation and analytics
- **👥 User Management**: Authentication, quotas, and profiles
- **🔒 Security**: Authentication, authorization, and data protection
- **🏗️ Infrastructure**: Performance, scalability, and monitoring
- **📱 API & Integration**: New endpoints and external integrations

### 📊 Evaluation Criteria

Features are evaluated based on:

- **User Value**: How many users benefit and impact on user experience
- **Technical Feasibility**: Implementation complexity and resource requirements
- **Alignment**: Strategic fit with product roadmap
- **Maintenance Overhead**: Long-term support and operational impact

## Development Setup

### Prerequisites

Before you begin development, ensure you have the following installed:

- **Python 3.12+**: Required for AWS Chalice and application code
- **AWS CLI**: Configured with appropriate IAM permissions
- **Terraform**: Version 1.0.0+ for infrastructure provisioning
- **Git**: For version control

### Local Development Environment

1. **Fork and Clone the Repository**

   ```bash
   git clone https://github.com/george-swift/expender-backend.git
   cd expender-backend
   ```

2. **Set Up Python Virtual Environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Configure AWS CLI**

   ```bash
   aws configure
   # Provide your AWS Access Key ID, Secret, and default region
   ```

5. **Set Up Environment Variables**
   ```bash
   # Edit vars_<environment>.tfvars with your configuration
   ```

### Development Workflow

1. **Create a Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**

   - Follow the coding standards outlined below
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Your Changes Locally**

   ```bash
   # Format code
   make format

   # Run tests
   make test

   # Deploy to dev environment for testing
   make deploy-dev
   ```

4. **Commit and Push**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   git push origin feature/your-feature-name
   ```

## Code Style and Standards

### Python Code Style

Follow [PEP 8](https://peps.python.org/pep-0008/) guidelines and use type hints for function parameters and return values where appropriate

### Infrastructure Code Style

- **Terraform**: Follow [Terraform best practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)
- **Comments**: Add meaningful comments explaining complex infrastructure decisions
- **Naming**: Use consistent, descriptive naming for resources
- **Modules**: Keep Terraform modules focused and reusable

### Documentation Standards

- **Docstrings**: Use [reStructuredText (reST)](https://peps.python.org/pep-0287/) docstrings for Python functions
- **README Updates**: Update README.md for any user-facing changes
- **API Documentation**: Update Swagger/Postman collections for API changes
- **Inline Comments**: Explain complex business logic with clear comments

## Testing

### Test Categories

1. **Unit Tests**: Test individual functions and classes in isolation
2. **Integration Tests**: Test component interactions and API endpoints
3. **Infrastructure Tests**: Validate Terraform configurations

### Writing Tests

- Write tests for all new functionality
- Use descriptive test names that explain the scenario
- Mock external dependencies (AWS services, OpenAI API, etc.)
- Include both positive and negative test cases

## Commit Message Guidelines

[Commitlint](https://pypi.org/project/commitlint/) is used to enforce the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standard. Please follow these rules for your commit messages:

- **Format:**

  ```
  <type>(<optional scope>): <subject>
    <BLANK LINE>
    <optional body>
    <BLANK LINE>
    <optional footer>
  ```

- **Type:** Indicates the type of change, such as `build`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `style`, `test`, `chore`, `revert`, or `bump`.
- **Scope:** (Optional) Additional contextual information, e.g., `feat(parser): add JSON parser`.
- **Subject:** Brief summary of the change (max 100 characters).
- **Body:** (Optional) More detailed description of the change.

Any line of the commit message cannot be longer than 100 characters. This allows the message to be easier to read on GitHub as well as in various git tools.

**Examples:**

- `feat: add user authentication`
- `fix(router): handle missing user ID error`
- `docs: update README with deployment instructions`

> **Note:** Avoid using commit messages that start with `#` as this may cause issues with commitlint.

For more details, see the [commitlint documentation](https://pypi.org/project/commitlint/) and the [Conventional Commits specification](https://www.conventionalcommits.org/en/v1.0.0/).

## Pull Request Process

### Overview

Pull requests are the primary way to contribute code changes to the Expender project. We use a structured PR template to ensure consistency and quality across all contributions.

### Before Submitting a Pull Request

1. **Search Existing PRs**: Check for open or closed PRs that relate to your submission
2. **Create an Issue**: For significant changes, create an issue first to discuss the approach
3. **Fork the Repository**: Work from your own fork of the repository
4. **Create Feature Branch**: Always work from a feature branch, never directly on master

### Pull Request Template

When creating a PR, GitHub will automatically populate our comprehensive [Pull Request Template](.github/pull_request_template.md) which includes:

- **📋 Summary & Type of Change**: Clear categorization and description
- **🧪 Testing**: Comprehensive testing checklist and evidence
- **✅ Quality Checklist**: Code quality, documentation, and infrastructure checks
- **🔒 Security Considerations**: Security impact assessment
- **🚀 Deployment Notes**: Deployment and rollback planning
- **📊 Performance Impact**: Performance metrics and testing results

### Key Requirements

**Code Quality:**

- Follow project style guidelines
- Include comprehensive tests coverage
- Add proper documentation and comments
- Ensure no linting errors or warnings

**Infrastructure:**

- Validate Terraform configurations
- Test infrastructure changes in dev environment
- Consider security and performance implications
- Document any breaking changes

### Review Process

1. **Automated Checks**: All CI workflows must pass
2. **Code Review**: At least one approved review required
3. **Testing**: Reviewers will test functionality in dev environment
4. **Security Review**: Security-sensitive changes require additional review
5. **Infrastructure Review**: Infrastructure changes require infrastructure team review

### After PR Approval

1. **Squash and Merge**: Use squash and merge for clean commit history
2. **Delete Branch**: Delete feature branch after merge
3. **Monitor Deployment**: Watch for any issues after deployment
4. **Update Documentation**: Ensure all documentation is current

## Additional Resources

### Documentation & Learning

- **[README.md](README.md)**: Project overview, setup, and usage
- **[AWS Chalice Documentation](https://aws.github.io/chalice/)**: Serverless framework reference
- **[Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)**: Infrastructure as code
- **[DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)**: Database optimization
- **[Conventional Commits](https://www.conventionalcommits.org/)**: Commit message standards

### Getting Help

- **🐛 Bug Reports**: Use our [issue templates](.github/ISSUE_TEMPLATE/)
- **💬 Discussions**: [GitHub Discussions](../../discussions) for questions
- **📧 Contact**: [support@expender.app](mailto:support@expender.app) for direct support
- **🔒 Security**: [security@expender.app](mailto:security@expender.app) for vulnerabilities

### Community Guidelines

- **📜 [Code of Conduct](CODE_OF_CONDUCT.md)**: Community standards and expectations
- **🎯 [Issue Templates](.github/ISSUE_TEMPLATE/)**: Structured reporting for bugs, features, and questions
- **📋 [Pull Request Template](.github/pull_request_template.md)**: Comprehensive PR submission guide

---

**🚀 Thank you for contributing to Expender!**
