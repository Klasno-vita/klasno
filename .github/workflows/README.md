# CI/CD workflows

- `ci.yml`: repository, Python, and Compose checks on pull requests and `main`.
- `deploy-staging.yml`: added when the first service and Terraform stack can deploy.
- `deploy-production.yml`: added with version tags and environment approval after staging.

Deployment workflows must not be placeholders that report success without
deploying anything.
