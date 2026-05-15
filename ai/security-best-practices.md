# Security Best Practices

## Code Security
- Never hardcode secrets, API keys, or passwords
- Use environment variables for configuration
- Validate all user inputs
- Use parameterized queries to prevent SQL injection
- Implement proper authentication and authorization

## Error Response Sanitization
- NEVER return `str(e)` or raw exception messages in API responses — they can leak database schema, file paths, or internal details
- Always return generic, user-safe error messages (e.g., "A conflicting resource already exists", "An internal error occurred")
- Log the original exception server-side at ERROR level with `exc_info=True` for debugging
- All view methods that call service layer code should have a catch-all `except Exception` handler returning a generic 500 response
- Separate internal diagnostic messages (for logs) from client-facing messages (for responses)

### Service Layer Error Handling Pattern
When implementing error handling in service methods that use `TaskReportingService`:
- Use `self.fail_task(generic_message, exception=e)` to pass the exception for automatic logging
- The `fail_task()` method will automatically log the exception with `exc_info=True`
- Never call `logger.error()` manually before `fail_task()` — it's redundant and creates maintenance burden
- Example:
  ```python
  try:
      # service operation
  except Exception as e:
      self.fail_task("Operation failed", exception=e)  # Logs automatically
      raise
  ```

## Dependency Management
- Keep dependencies updated
- Use dependency scanning tools
- Review third-party packages before adding
- Use lock files (package-lock.json, poetry.lock)
- Remove unused dependencies

## Data Protection
- Encrypt sensitive data at rest and in transit
- Use HTTPS for all web communications
- Implement proper session management
- Use secure headers (HSTS, CSP, etc.)
- Follow OWASP guidelines

## Infrastructure Security
- Use least privilege principle for IAM
- Enable logging and monitoring
- Use network segmentation
- Implement proper backup strategies
- Regular security audits and penetration testing

## Development Practices
- Use static code analysis tools
- Implement security testing in CI/CD
- Code reviews for security issues
- Security training for developers
- Incident response procedures
