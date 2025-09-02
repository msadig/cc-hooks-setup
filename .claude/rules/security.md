# Security Standards

## Critical Rules
- NEVER commit secrets, passwords, or API keys
- Use environment variables for sensitive data
- Validate and sanitize all user inputs
- Use parameterized queries for database operations

## Authentication
- Use secure session management
- Implement proper password hashing (bcrypt, argon2)
- Add rate limiting to prevent brute force
- Use HTTPS for all sensitive operations

## Before Committing
- Scan for hardcoded secrets
- Review authentication logic
- Check for SQL injection vulnerabilities
- Ensure proper error handling (don't expose stack traces)