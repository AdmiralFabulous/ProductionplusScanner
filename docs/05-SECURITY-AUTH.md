# 05 - Security & Authentication

**Document Version:** 1.0  
**Last Updated:** 2026-02-01  
**Reference:** SUIT_AI_Master_Operations_Manual_v6_7_1.md Section 2.5 - Security Layer

---

## Table of Contents

1. [Overview](#overview)
2. [JWT Authentication Flow](#jwt-authentication-flow)
3. [Token Refresh Sequence](#token-refresh-sequence)
4. [CORS Configuration](#cors-configuration)
5. [TLS 1.3 Requirements](#tls-13-requirements)
6. [Rate Limiting](#rate-limiting)
7. [API Key Security](#api-key-security)
8. [Security Checklist for Production](#security-checklist-for-production)

---

## Overview

The PRODUCTION-SCANNER system implements a comprehensive security layer protecting customer measurement data, pattern IP, and production systems. This document describes the security architecture based on Ops Manual Section 2.5.

### Security Architecture Summary

| Layer | Technology | Standard |
|-------|------------|----------|
| Authentication | JWT (JSON Web Tokens) | RFC 7519 |
| Transport | TLS 1.3 | RFC 8446 |
| CORS | Configured Origins | W3C Spec |
| Rate Limiting | Token Bucket | 100 req/min |
| Secrets | Environment Variables | 12-Factor App |

---

## JWT Authentication Flow

### Token Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    JWT TOKEN STRUCTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   HEADER    │    │   PAYLOAD   │    │      SIGNATURE      │ │
│  │             │    │             │    │                     │ │
│  │ {           │    │ {           │    │ HMACSHA256(         │ │
│  │   "alg":    │ +  │   "sub":    │ +  │   base64(header) +  │ │
│  │   "HS256",  │    │   "user@...",│    │   base64(payload),  │ │
│  │   "typ":    │    │   "exp":    │    │   secret_key        │ │
│  │   "JWT"     │    │   170678...,│    │ )                   │ │
│  │ }           │    │   "iat":    │    │                     │ │
│  │             │    │   170678...,│    │                     │ │
│  │             │    │   "scope": [│    │                     │ │
│  │             │    │     "orders"│    │                     │ │
│  │             │    │   ]         │    │                     │ │
│  │             │    │ }           │    │                     │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│                                                                 │
│  Base64Url encoded → eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### JWT Payload Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `sub` | string | Subject (user email) | "user@example.com" |
| `exp` | number | Expiration time (Unix timestamp) | 1706784000 |
| `iat` | number | Issued at (Unix timestamp) | 1706780400 |
| `iss` | string | Issuer | "pattern-factory" |
| `aud` | string | Audience | "eyeson-client" |
| `scope` | array | Permissions | ["orders:read", "orders:write"] |
| `jti` | string | JWT ID (unique token ID) | "550e8400-e29b-41d4" |

### Authentication Flow Diagram

```
┌──────────────┐                                    ┌──────────────────┐
│   EYESON     │                                    │  PATTERN FACTORY │
│   FRONTEND   │                                    │     BACKEND      │
└──────┬───────┘                                    └────────┬─────────┘
       │                                                     │
       │  1. POST /auth/login                                │
       │  {                                                │
       │    "email": "user@example.com",                   │
       │    "password": "********"                         │
       │  }                                                │
       │────────────────────────────────────────────────────▶│
       │                                                     │
       │                        2. Validate credentials      │
       │                        against PostgreSQL           │
       │                        (bcrypt hash check)          │
       │                                                     │
       │  3. 200 OK                                          │
       │  {                                                │
       │    "access_token": "eyJhbGciOiJIUzI1...",          │
       │    "refresh_token": "eyJhbGciOiJIUzI1...",         │
       │    "token_type": "Bearer",                        │
       │    "expires_in": 3600,  // 1 hour                 │
       │    "scope": ["orders:read", "orders:write"]       │
       │  }                                                │
       │◀────────────────────────────────────────────────────│
       │                                                     │
       │  4. Store tokens in memory (NOT localStorage)       │
       │     (Secure, httpOnly cookie or memory store)       │
       │                                                     │
       │═══════════ SUBSEQUENT REQUESTS ═══════════════════  │
       │                                                     │
       │  5. GET /orders                                     │
       │     Authorization: Bearer eyJhbGciOiJIUzI1...       │
       │────────────────────────────────────────────────────▶│
       │                                                     │
       │                        6. Verify JWT signature      │
       │                        Check exp (not expired)      │
       │                        Check scope (has permission) │
       │                                                     │
       │  7. 200 OK + Order Data                             │
       │◀────────────────────────────────────────────────────│
       │                                                     │
```

### Implementation: Pattern Factory (Python/FastAPI)

```python
# pattern-factory/src/api/auth.py

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configuration
SECRET_KEY = os.environ["JWT_SECRET_KEY"]  # 256-bit minimum
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS = 7     # 7 days

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class TokenData(BaseModel):
    sub: Optional[str] = None
    scope: List[str] = []

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token with 1-hour expiry."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": "pattern-factory",
        "jti": str(uuid.uuid4())
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """Validate JWT token from Authorization header."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        scope: list = payload.get("scope", [])
        exp: int = payload.get("exp")
        
        if sub is None:
            raise credentials_exception
            
        # Check expiration
        if datetime.utcnow().timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except JWTError:
        raise credentials_exception
    
    return TokenData(sub=sub, scope=scope)

def require_scope(required_scope: str):
    """Decorator to require specific scope in JWT."""
    def decorator(token_data: TokenData = Depends(get_current_user)):
        if required_scope not in token_data.scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_scope}"
            )
        return token_data
    return decorator

# Login endpoint
@router.post("/auth/login")
async def login(credentials: LoginRequest):
    """Authenticate user and return JWT tokens."""
    # Verify credentials against database
    user = await authenticate_user(credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create tokens
    access_token, access_exp = create_access_token(
        data={"sub": user.email, "scope": user.permissions}
    )
    refresh_token, refresh_exp = create_refresh_token(
        data={"sub": user.email}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "scope": user.permissions
    }
```

### Implementation: EYESON Frontend (TypeScript)

```typescript
// eyeson/frontend/src/services/patternFactoryApi.ts

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'Bearer';
  expires_in: number;
  scope: string[];
}

class PatternFactoryAPI {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private tokenExpiry: Date | null = null;
  private readonly baseURL: string;
  
  constructor(baseURL: string = 'http://localhost:8000') {
    this.baseURL = baseURL;
    this.loadTokens();
  }
  
  /**
   * Authenticate and store tokens
   */
  async login(email: string, password: string): Promise<void> {
    const response = await fetch(`${this.baseURL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    
    if (!response.ok) {
      throw new Error('Authentication failed');
    }
    
    const data: TokenResponse = await response.json();
    this.setTokens(data);
  }
  
  /**
   * Store tokens and calculate expiry
   */
  private setTokens(data: TokenResponse): void {
    this.accessToken = data.access_token;
    this.refreshToken = data.refresh_token;
    
    // Calculate expiry (expires_in is in seconds)
    this.tokenExpiry = new Date(Date.now() + data.expires_in * 1000);
    
    // Optionally store in secure cookie or sessionStorage
    // NEVER store in localStorage (XSS risk)
    sessionStorage.setItem('pf_access_token', data.access_token);
    sessionStorage.setItem('pf_refresh_token', data.refresh_token);
    sessionStorage.setItem('pf_token_expiry', this.tokenExpiry.toISOString());
  }
  
  /**
   * Load tokens from storage
   */
  private loadTokens(): void {
    this.accessToken = sessionStorage.getItem('pf_access_token');
    this.refreshToken = sessionStorage.getItem('pf_refresh_token');
    const expiryStr = sessionStorage.getItem('pf_token_expiry');
    if (expiryStr) {
      this.tokenExpiry = new Date(expiryStr);
    }
  }
  
  /**
   * Check if token needs refresh (within 5 minutes of expiry)
   */
  private needsRefresh(): boolean {
    if (!this.tokenExpiry) return false;
    
    const fiveMinutes = 5 * 60 * 1000;
    return Date.now() > (this.tokenExpiry.getTime() - fiveMinutes);
  }
  
  /**
   * Make authenticated API request
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    // Refresh token if needed
    if (this.needsRefresh()) {
      await this.refreshAccessToken();
    }
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }
    
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers,
    });
    
    if (response.status === 401) {
      // Token expired or invalid
      throw new Error('Session expired. Please log in again.');
    }
    
    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  /**
   * Refresh access token using refresh token
   */
  private async refreshAccessToken(): Promise<void> {
    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }
    
    try {
      const response = await fetch(`${this.baseURL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });
      
      if (!response.ok) {
        // Refresh failed, clear tokens
        this.clearTokens();
        throw new Error('Session expired. Please log in again.');
      }
      
      const data: TokenResponse = await response.json();
      this.setTokens(data);
    } catch (error) {
      this.clearTokens();
      throw error;
    }
  }
  
  /**
   * Clear all tokens
   */
  private clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;
    this.tokenExpiry = null;
    sessionStorage.removeItem('pf_access_token');
    sessionStorage.removeItem('pf_refresh_token');
    sessionStorage.removeItem('pf_token_expiry');
  }
  
  // API methods using authenticated request
  async getOrders(): Promise<Order[]> {
    return this.request<Order[]>('/orders');
  }
  
  async createOrder(orderData: CreateOrderRequest): Promise<Order> {
    return this.request<Order>('/orders', {
      method: 'POST',
      body: JSON.stringify(orderData),
    });
  }
}
```

---

## Token Refresh Sequence

### Refresh Flow Diagram

```
┌──────────────┐                                    ┌──────────────────┐
│   EYESON     │                                    │  PATTERN FACTORY │
│   FRONTEND   │                                    │     BACKEND      │
└──────┬───────┘                                    └────────┬─────────┘
       │                                                     │
       │  Token expires in 5 min                             │
       │  (detected by needsRefresh())                       │
       │                                                     │
       │  1. POST /auth/refresh                              │
       │  {                                                │
       │    "refresh_token": "eyJhbGciOiJIUzI1..."         │
       │  }                                                │
       │────────────────────────────────────────────────────▶│
       │                                                     │
       │                        2. Verify refresh token      │
       │                        (different secret, longer    │
       │                        expiry)                      │
       │                                                     │
       │  3. 200 OK                                          │
       │  {                                                │
       │    "access_token": "eyJhbGciOiJIUzI1...",          │
       │    "expires_in": 3600                             │
       │  }                                                │
       │◀────────────────────────────────────────────────────│
       │                                                     │
       │  4. Update stored access_token                      │
       │     Continue with original request                  │
       │                                                     │
```

### Refresh Token Implementation

```python
# Refresh token has longer expiry (7 days) and single-use
REFRESH_SECRET_KEY = os.environ["JWT_REFRESH_SECRET_KEY"]
REFRESH_TOKEN_EXPIRE_DAYS = 7

async def refresh_access_token(refresh_token: str):
    """Create new access token from valid refresh token."""
    try:
        payload = jwt.decode(refresh_token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        
        if sub is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Check if refresh token has been revoked
        if await is_token_revoked(payload.get("jti")):
            raise HTTPException(status_code=401, detail="Token has been revoked")
        
        # Create new access token
        access_token, _ = create_access_token(
            data={"sub": sub, "scope": await get_user_scopes(sub)}
        )
        
        # Optionally revoke old refresh token and issue new one
        await revoke_token(payload.get("jti"))
        new_refresh_token, _ = create_refresh_token(data={"sub": sub})
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
```

---

## CORS Configuration

### Allowed Origins

| Environment | Allowed Origins |
|-------------|-----------------|
| Development | `http://localhost:5173`, `http://localhost:3000` |
| Staging | `https://staging.eyeson.samedaysuits.com` |
| Production | `https://eyeson.samedaysuits.com` |

### FastAPI CORS Configuration

```python
# pattern-factory/src/main.py

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS configuration
allowed_origins = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,  # Required for cookies/auth headers
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Client-Version"
    ],
    expose_headers=["X-Request-ID"],
    max_age=600  # 10 minutes cache for preflight
)
```

### CORS Headers

| Header | Value | Description |
|--------|-------|-------------|
| `Access-Control-Allow-Origin` | `https://eyeson.samedaysuits.com` | Specific origin (no wildcard with credentials) |
| `Access-Control-Allow-Credentials` | `true` | Allow cookies/auth headers |
| `Access-Control-Allow-Methods` | `GET, POST, PUT, DELETE, OPTIONS` | Allowed HTTP methods |
| `Access-Control-Allow-Headers` | `Authorization, Content-Type` | Allowed request headers |
| `Access-Control-Max-Age` | `600` | Preflight cache duration |

---

## TLS 1.3 Requirements

### Certificate Requirements

| Requirement | Specification |
|-------------|---------------|
| Certificate Type | X.509 v3 |
| Key Algorithm | RSA-2048 or ECDSA P-256 |
| Signature Algorithm | SHA-256 minimum |
| Validity Period | Maximum 398 days |
| Subject Alternative Name | Required (DNS and IP) |

### TLS Configuration

```nginx
# nginx.conf - TLS 1.3 enforcement

server {
    listen 443 ssl http2;
    server_name api.samedaysuits.com;
    
    # Certificate paths
    ssl_certificate /etc/ssl/certs/samedaysuits.crt;
    ssl_certificate_key /etc/ssl/private/samedaysuits.key;
    
    # TLS 1.3 only
    ssl_protocols TLSv1.3;
    
    # Cipher suites (TLS 1.3)
    ssl_ciphers TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256;
    
    # Prefer server ciphers
    ssl_prefer_server_ciphers off;  # TLS 1.3 ignores this
    
    # Session settings
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    
    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/ssl/certs/chain.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    location / {
        proxy_pass http://pattern-factory:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.samedaysuits.com;
    return 301 https://$server_name$request_uri;
}
```

---

## Rate Limiting

### Rate Limit Rules

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Authentication | 5 | 1 minute |
| General API | 100 | 1 minute |
| File Downloads | 20 | 1 minute |
| Order Creation | 10 | 1 minute |
| Status Polling | 300 | 1 minute |

### Implementation

```python
# pattern-factory/src/core/rate_limiter.py

from fastapi import Request, HTTPException
from redis import Redis
import time

redis_client = Redis(host='redis', port=6379, db=0)

class RateLimiter:
    def __init__(self, requests: int, window: int):
        self.requests = requests
        self.window = window
    
    async def check(self, key: str):
        """Check if request is within rate limit."""
        now = time.time()
        window_start = now - self.window
        
        # Remove old entries
        redis_client.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        current = redis_client.zcard(key)
        
        if current >= self.requests:
            # Get time until oldest request expires
            oldest = redis_client.zrange(key, 0, 0, withscores=True)[0][1]
            retry_after = int(oldest + self.window - now)
            
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(oldest + self.window))
                }
            )
        
        # Add current request
        redis_client.zadd(key, {str(now): now})
        redis_client.expire(key, self.window)
        
        return {
            "X-RateLimit-Limit": str(self.requests),
            "X-RateLimit-Remaining": str(self.requests - current - 1),
        }

# Usage in endpoints
rate_limiter = RateLimiter(requests=100, window=60)

@router.post("/orders")
async def create_order(
    request: Request,
    current_user: TokenData = Depends(get_current_user)
):
    # Rate limit by user
    key = f"ratelimit:{current_user.sub}:orders"
    headers = await rate_limiter.check(key)
    
    # ... process order
    
    return JSONResponse(content=result, headers=headers)
```

### Rate Limit Response Headers

| Header | Description | Example |
|--------|-------------|---------|
| `X-RateLimit-Limit` | Maximum requests allowed | `100` |
| `X-RateLimit-Remaining` | Remaining requests in window | `87` |
| `X-RateLimit-Reset` | Unix timestamp when limit resets | `1706784000` |
| `Retry-After` | Seconds to wait (on 429) | `45` |

---

## API Key Security

### Environment Variable Management

```bash
# .env.example - NEVER commit actual values

# JWT Secrets (256-bit minimum, generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-jwt-secret-here
JWT_REFRESH_SECRET_KEY=your-refresh-secret-here

# Database
DATABASE_URL=postgresql://user:password@localhost/samedaysuits

# External APIs (if needed)
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN}

# Cutter
CUTTER_IP=192.168.1.100
CUTTER_PORT=9100
```

### Secret Generation

```bash
# Generate secure JWT secrets
$ openssl rand -hex 32
a1b2c3d4e5f6...  # 64 hex characters = 256 bits

# Generate API key
$ openssl rand -base64 32
AQIDBAUGBwg...  # Use for internal API keys
```

### Docker Secrets (Production)

```yaml
# docker-compose.yml
version: '3.8'

services:
  pattern-factory:
    image: samedaysuits/pattern-factory:latest
    secrets:
      - jwt_secret_key
      - jwt_refresh_secret_key
      - db_password
    environment:
      JWT_SECRET_KEY_FILE: /run/secrets/jwt_secret_key
      JWT_REFRESH_SECRET_KEY_FILE: /run/secrets/jwt_refresh_secret_key
      
secrets:
  jwt_secret_key:
    external: true
  jwt_refresh_secret_key:
    external: true
  db_password:
    external: true
```

---

## Security Checklist for Production

### Pre-Deployment Security Audit

- [ ] JWT secrets are 256-bit minimum and unique per environment
- [ ] TLS 1.3 is enforced (no TLS 1.0, 1.1, 1.2)
- [ ] HSTS header is configured
- [ ] CORS origins are explicitly defined (no wildcards)
- [ ] Rate limiting is enabled
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS protection headers
- [ ] Content Security Policy configured
- [ ] Secrets are in environment variables (not code)
- [ ] Database connections use TLS
- [ ] API keys are rotated
- [ ] Logging excludes sensitive data
- [ ] Error messages don't leak implementation details

### Security Headers Checklist

| Header | Status | Value |
|--------|--------|-------|
| Strict-Transport-Security | ✅ Required | `max-age=63072000; includeSubDomains; preload` |
| X-Frame-Options | ✅ Required | `SAMEORIGIN` or `DENY` |
| X-Content-Type-Options | ✅ Required | `nosniff` |
| X-XSS-Protection | ✅ Required | `1; mode=block` |
| Referrer-Policy | ✅ Required | `strict-origin-when-cross-origin` |
| Content-Security-Policy | ✅ Required | Defined per endpoint |
| Permissions-Policy | ✅ Recommended | `camera=(), microphone=()` |

### Penetration Testing Checklist

- [ ] JWT token manipulation (alg: none attack)
- [ ] Token expiration bypass
- [ ] CORS misconfiguration
- [ ] Rate limit bypass
- [ ] SQL injection in order IDs
- [ ] Path traversal in file downloads
- [ ] XSS in measurement data
- [ ] CSRF on state-changing operations

---

## Next Steps

1. **Review** [04-API-REFERENCE.md](./04-API-REFERENCE.md) for endpoint authentication requirements
2. **Check** [06-TROUBLESHOOTING.md](./06-TROUBLESHOOTING.md) for authentication errors
3. **Test** authentication flows before production deployment

---

*For security incidents, contact: security@samedaysuits.com*
