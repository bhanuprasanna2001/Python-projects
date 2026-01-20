# Project 15: JWT Authentication

A comprehensive mini-project demonstrating **JSON Web Tokens (JWT)** for authentication.

## What You'll Learn

- JWT structure (header, payload, signature)
- Token generation and validation
- Access tokens vs refresh tokens
- Token revocation strategies
- FastAPI integration
- Security best practices

## Project Structure

```
15-jwt-auth/
├── README.md
├── requirements.txt
├── jwt_basics.py           # JWT fundamentals
├── token_service.py        # Token generation/validation
├── fastapi_jwt.py          # FastAPI integration
├── refresh_tokens.py       # Refresh token pattern
└── revocation.py           # Token revocation strategies
```

## Setup

```bash
pip install -r requirements.txt
python jwt_basics.py
python fastapi_jwt.py
```

## JWT Structure

```
header.payload.signature

Header:
{
  "alg": "HS256",
  "typ": "JWT"
}

Payload (Claims):
{
  "sub": "user_id",
  "exp": 1234567890,
  "iat": 1234567890,
  ...
}

Signature:
HMACSHA256(base64Url(header) + "." + base64Url(payload), secret)
```

## Token Types

### Access Token
- Short-lived (15-60 minutes)
- Used for API authorization
- Stateless verification

### Refresh Token
- Long-lived (days/weeks)
- Used to obtain new access tokens
- Should be stored securely

## Security Best Practices

1. Use strong secrets (256+ bits)
2. Set appropriate expiration times
3. Use HTTPS only
4. Store tokens securely (HttpOnly cookies)
5. Implement token rotation
6. Have a revocation strategy
7. Validate all claims
8. Use asymmetric keys for distributed systems
