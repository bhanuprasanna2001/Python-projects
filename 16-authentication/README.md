# Project 16: Authentication Patterns
# OAuth2, Session Management, Password Hashing

## Overview

This project covers comprehensive authentication patterns including:
- Password hashing with bcrypt/argon2
- OAuth2 flows (Authorization Code, PKCE)
- Session management
- Multi-factor authentication basics
- Social login integration patterns

## Project Structure

```
16-authentication/
├── README.md
├── requirements.txt
├── password_hashing.py    # Secure password handling
├── oauth2_flows.py        # OAuth2 implementation
├── session_auth.py        # Session-based authentication
├── mfa_basics.py          # Multi-factor authentication
└── social_login.py        # Social login patterns
```

## Key Concepts

### Password Hashing

```python
from passlib.context import CryptContext
from argon2 import PasswordHasher

# Using passlib (recommended)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash password
hashed = pwd_context.hash("my_password")

# Verify password
is_valid = pwd_context.verify("my_password", hashed)
```

### OAuth2 Flows

1. **Authorization Code Flow**: For server-side apps
2. **Authorization Code + PKCE**: For mobile/SPA apps
3. **Client Credentials**: For service-to-service
4. **Implicit Flow**: Deprecated, avoid use

### Session Management Best Practices

1. Use secure, httpOnly cookies
2. Implement session timeout
3. Regenerate session ID on login
4. Invalidate session on logout
5. Store minimal data in session

## Running Examples

```bash
# Install dependencies
pip install -r requirements.txt

# Run password hashing examples
python password_hashing.py

# Run session auth FastAPI example
uvicorn session_auth:app --reload

# Run OAuth2 example
uvicorn oauth2_flows:app --reload
```

## Security Checklist

- [ ] Hash passwords with bcrypt/argon2
- [ ] Use constant-time comparison for secrets
- [ ] Implement rate limiting on auth endpoints
- [ ] Use HTTPS in production
- [ ] Implement CSRF protection for sessions
- [ ] Set secure cookie flags
- [ ] Log authentication events
- [ ] Implement account lockout
