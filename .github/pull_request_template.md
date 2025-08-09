---
name: Pull Request
about: Template for all pull requests to maintain consistency and quality
---

## 📋 Pull Request Summary

<!-- Provide a brief, clear description of what this PR accomplishes -->

### 🎯 Type of Change

<!-- Check all that apply -->

- [ ] 🐛 **Bug fix** (non-breaking change which fixes an issue)
- [ ] ✨ **New feature** (non-breaking change which adds functionality)
- [ ] 💥 **Breaking change** (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 **Documentation update** (changes to documentation only)
- [ ] 🏗️ **Infrastructure change** (Terraform, AWS services, deployment)
- [ ] 🔧 **Refactor** (code changes that neither fix a bug nor add a feature)
- [ ] ⚡ **Performance improvement** (changes that improve performance)
- [ ] 🔒 **Security enhancement** (changes that improve security)

## 🔗 Related Issues

<!-- Link to related issues -->

- Fixes #(issue number)
- Related to #(issue number)

## 📝 Description

### What Changed

<!-- Describe the changes in detail -->

### Why These Changes

<!-- Explain the motivation and context for these changes -->

### How It Works

<!-- Explain how the solution works, if not obvious -->

## 🧪 Testing

### Testing Completed

- [ ] **Local testing** completed successfully
- [ ] **Unit tests** added/updated and passing (if applicable)
- [ ] **Integration tests** added/updated and passing (if applicable)
- [ ] **Deployed and tested** in dev environment
- [ ] **Manual testing** of key user journeys
- [ ] **Performance testing** (if applicable)
- [ ] **Security testing** (if applicable)

## ✅ Quality Checklist

### Code Quality

- [ ] **Code follows** project style guidelines (Black, isort, PEP 8)
- [ ] **No linting errors** or warnings
- [ ] **Type hints** added where appropriate
- [ ] **Complex logic** is well-commented
- [ ] **Error handling** implemented properly
- [ ] **Logging** added for debugging and monitoring

### Documentation

- [ ] **README.md** updated for user-facing changes
- [ ] **API documentation** updated (Swagger/Postman)
- [ ] **Inline code documentation** added/updated
- [ ] **Comments** explain complex business logic

### Infrastructure & Security

- [ ] **Terraform configurations** validated with `terraform plan`
- [ ] **Infrastructure changes** tested in dev environment
- [ ] **Security implications** considered and documented
- [ ] **Rate limiting impacts** assessed
- [ ] **IAM permissions** reviewed and minimal
- [ ] **Secrets management** follows best practices

### Deployment

- [ ] **Changes tested** with `make deploy-dev`
- [ ] **No breaking changes** to existing APIs
- [ ] **Database migrations** handled properly (if applicable)
- [ ] **Environment variables** documented
- [ ] **Rollback plan** considered and documented

## 🔒 Security Considerations

<!-- Describe any security implications -->

- **Authentication/Authorization**: [impact on auth systems]
- **Data Privacy**: [impact on user data handling]
- **API Security**: [impact on API endpoints]
- **Infrastructure Security**: [impact on AWS resources]
- **Dependencies**: [new dependencies and their security implications]

**Security Review Required**: <!-- Yes/No and why -->

## 🚀 Deployment Notes

### Pre-deployment Steps

<!-- List any steps needed before deploying -->

1. Step 1
2. Step 2

### Deployment Process

<!-- Any special deployment considerations -->

- **Order of deployment**: [if multiple services affected]
- **Configuration changes**: [environment variables, etc.]
- **Database changes**: [migrations, schema updates]

### Post-deployment Verification

<!-- How to verify the deployment was successful -->

1. Verification step 1
2. Verification step 2

### Rollback Plan

<!-- How to rollback if issues are discovered -->

- **Rollback steps**: [specific steps to revert changes]
- **Rollback time**: [estimated time to rollback]
- **Data considerations**: [any data migration rollback needs]

## 📊 Performance Impact

### Performance Metrics

<!-- If applicable, include performance measurements -->

- **Response time**: Before [X ms] → After [Y ms]
- **Memory usage**: Before [X MB] → After [Y MB]
- **Throughput**: Before [X req/sec] → After [Y req/sec]
- **Cost**: Before [$X/month] → After [$Y/month]

### Load Testing

<!-- If load testing was performed -->

- **Test scenarios**: [describe load test scenarios]
- **Results**: [key findings from load testing]
- **Recommendations**: [any recommendations from testing]

## 🔄 Breaking Changes

<!-- If this PR introduces breaking changes -->

### API Changes

- [ ] **New required fields** in request/response
- [ ] **Changed field types** or formats
- [ ] **Removed endpoints** or fields
- [ ] **Changed error responses**

### Migration Guide

<!-- Provide guidance for users to adapt to breaking changes -->

1. Migration step 1
2. Migration step 2

### Compatibility

- **Backward compatibility**: [Yes/No and explanation]
- **Version strategy**: [how versions are handled]

## 📸 Screenshots/Evidence

<!-- Include visual evidence if applicable -->

### Before

[Screenshots or evidence of current state]

### After

[Screenshots or evidence of new state]

### Logs/Metrics

```
[Relevant log entries, CloudWatch metrics, or monitoring data]
```

## 🤝 Review Guidance

### Focus Areas for Reviewers

<!-- Guide reviewers on what to focus on -->

- **Key files to review**: [list important files]
- **Business logic**: [areas requiring careful review]
- **Security concerns**: [specific security aspects to check]
- **Performance**: [performance-critical code paths]

### Questions for Reviewers

<!-- Specific questions you'd like reviewers to consider -->

1. Question 1
2. Question 2

## 📚 Additional Context (Optional)

### Implementation Decisions

<!-- Explain key implementation decisions -->

- **Why this approach**: [reasoning for chosen solution]
- **Alternatives considered**: [other approaches that were considered]
- **Trade-offs**: [trade-offs made in this implementation]

### Future Considerations

<!-- Note any future improvements or considerations -->

- **Technical debt**: [any technical debt introduced]
- **Future enhancements**: [potential future improvements]
- **Dependencies**: [external dependencies or blockers]

### Learning Resources

<!-- Include links to relevant documentation or resources -->

- [Link to relevant documentation]
- [Link to design documents]
- [Link to external resources]

---

## 📋 Pre-merge Checklist

<!-- Final checklist before merge -->

- [ ] All CI/CD checks are passing
- [ ] Code review approved by required reviewers
- [ ] All feedback addressed or acknowledged
- [ ] Documentation updated and reviewed
- [ ] Security review completed (if required)
- [ ] Performance testing completed (if applicable)
- [ ] Ready for production deployment

### Merge Strategy

- [ ] **Squash and merge** (recommended for feature branches)
- [ ] **Merge commit** (for release branches)
- [ ] **Rebase and merge** (for clean history)

---

**✅ By submitting this PR, I confirm that:**

- I have read and followed the [Contributing Guidelines](CONTRIBUTING.md)
- I have tested my changes thoroughly
- I understand the security and performance implications
- I am ready to support this change post-deployment
