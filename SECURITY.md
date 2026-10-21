# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public GitHub issue.

Instead, report it privately by:
1. Navigating to the **Security** tab of this repository
2. Selecting **Report a vulnerability**
3. Providing a clear description of the issue, steps to reproduce, and potential impact

You can expect an acknowledgement within **5 business days** and a resolution or mitigation plan within **30 days**, depending on severity.

## Security Best Practices

- Keep dependencies up to date (see Dependabot alerts)
- Never commit secrets, credentials, or API keys to the repository
- Use environment variables via `.env` files (excluded from version control via `.gitignore`)
- Review Dependabot and code scanning alerts regularly
