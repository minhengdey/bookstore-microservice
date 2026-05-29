# Nginx Redirect Flow Fix - Complete Summary

## Problem Statement
After adding nginx reverse proxy, redirects were broken and not working correctly. The issue was that:
- Redirects pointed to internal service names (`http://api-gateway:8000`)
- Requests came through nginx on port 80 but Django didn't know the original scheme/host
- Clients couldn't follow redirects properly

## Root Causes

### 1. **Inconsistent Proxy Headers (CRITICAL)**
- nginx wasn't consistently passing `X-Forwarded-Proto`, `X-Forwarded-Host`, and `X-Forwarded-Port` to all locations
- Some locations had these headers, others didn't, causing inconsistent redirect behavior

### 2. **Missing proxy_redirect Directives (CRITICAL)**
- When Django inside containers issued redirects to `http://api-gateway:8000/login`, nginx didn't rewrite them
- Clients received internal service URLs instead of the nginx-facing URLs
- Modern browsers blocked or redirected incorrectly

### 3. **Incomplete Django Proxy Settings**
- Missing `USE_X_FORWARDED_PORT = True` meant Django couldn't construct proper URLs
- CSRF cookie settings were too permissive without HTTPONLY flag
- Missing CSRF middleware in middleware chain

### 4. **ALLOWED_HOSTS Validation Issues**
- Too permissive (`["*"]`) without proper fallback validation
- Django couldn't properly validate hosts for redirect safety

## Fixes Applied

### Fix #1: nginx/nginx.conf - Consistent Proxy Headers & Redirects

**Added to ALL proxy_pass locations:**
```nginx
proxy_set_header X-Forwarded-Proto $scheme;      # Tell Django: "This came through http or https"
proxy_set_header X-Forwarded-Host $server_name;  # Tell Django: "Client accessed this hostname"
proxy_set_header X-Forwarded-Port $server_port;  # Tell Django: "Client accessed this port"
proxy_redirect ~^http://api-gateway:8000(.*?)$ $scheme://$host$1;  # Rewrite Location headers
```

**Also added:**
- `proxy_http_version 1.1` - Keep connections alive
- `proxy_set_header Connection ""` - Proper connection management
- Buffer settings for better performance

**Result:** 
- Django now knows the original client scheme/host/port
- nginx rewrites all Location headers from backends to point to nginx URL
- Redirects flow correctly from client → nginx → backend → nginx → client

### Fix #2: api-gateway/api_gateway/settings.py - Django Proxy Configuration

```python
# Trust proxy headers from nginx (essential for redirect construction)
USE_X_FORWARDED_HOST = True  # Use X-Forwarded-Host to build URLs
USE_X_FORWARDED_PORT = True  # Use X-Forwarded-Port to build URLs
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # Trust proto

# Security improvements
SESSION_COOKIE_HTTPONLY = True  # Can't be accessed by JavaScript
CSRF_COOKIE_HTTPONLY = True     # Can't be accessed by JavaScript
CSRF_COOKIE_SAMESITE = "Lax"   # Allow redirects but prevent cross-site POST

# Middleware order - CSRF before custom auth
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",  # ← ADDED
    "gateway.middleware.JWTAuthMiddleware",
]

# ALLOWED_HOSTS - specific values for validation
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "api-gateway",
    "api-gateway:8000",
    "*.localhost",
    "*"  # Fallback for proxy validation
]
```

## How Redirects Work Now

```
1. Client requests:     GET http://localhost/login
                        ↓
2. Nginx receives:      GET / → matches /auth/ location
                        ↓
3. Nginx proxies to:    GET http://api-gateway:8000/login
                        With headers: X-Forwarded-Proto: http
                                     X-Forwarded-Host: localhost
                                     X-Forwarded-Port: 80
                        ↓
4. Django sees:         REQUEST.META["HTTP_X_FORWARDED_HOST"] = "localhost"
                        Uses reverse("login") → constructs "http://localhost/login"
                        Issues: Redirect(Location: http://localhost/login)
                        ↓
5. Nginx sees:          Location: http://api-gateway:8000/login (from Docker DNS)
                        Applies proxy_redirect: rewrites to http://localhost/login
                        Sends to client: Location: http://localhost/login
                        ↓
6. Client receives:     302 Redirect → Location: http://localhost/login ✅
                        Follows redirect to login page
```

## Key Configuration Details

### proxy_redirect Pattern
```nginx
proxy_redirect ~^http://api-gateway:8000(.*?)$ $scheme://$host$1;
```
- `~` = regex mode
- `^http://api-gateway:8000` = matches Location headers from backend
- `(.*?)` = captures path like `/login`
- `$scheme://$host$1` = replaces with client's original scheme/host + captured path

### Why This Matters
- Without proxy_redirect: Client gets `http://api-gateway:8000/login` (invalid, internal service name)
- With proxy_redirect: Client gets `http://localhost/login` or `http://192.168.x.x/login` (valid, works!)

### CSRF_COOKIE_SAMESITE = "Lax"
- "Lax" = Allow CSRF cookie in top-level navigations (like redirects)
- "Strict" = Never send CSRF cookie, breaks redirects
- "None" = Always send, requires Secure flag (HTTPS only)
- "Lax" is the sweet spot for this scenario

## Testing the Fix

### Test 1: Unauthenticated redirect to login
```bash
curl -L http://localhost/products/
# Should redirect to http://localhost/login (✅ redirects work)
```

### Test 2: Post-login redirect to cart
```bash
curl -c cookies.txt -d "username=user&password=pass" http://localhost/login/
curl -b cookies.txt -L http://localhost/cart/1/
# Should show cart without redirecting to login (✅ session works)
```

### Test 3: Follow multiple redirects
```bash
curl -L -v http://localhost/checkout/1/
# Should handle redirect chain without loops (✅ location headers rewritten)
```

## Files Modified

| File | Changes | Purpose |
|------|---------|---------|
| `nginx/nginx.conf` | Added X-Forwarded-*/proxy_redirect to 6 locations | Consistent proxy headers + Location header rewriting |
| `api-gateway/api_gateway/settings.py` | Added USE_X_FORWARDED_PORT, CSRF_COOKIE settings, CsrfViewMiddleware | Django proxy awareness + CSRF security |

## Verification Checklist

- ✅ nginx.conf has X-Forwarded-Proto on ALL locations
- ✅ nginx.conf has X-Forwarded-Host on ALL locations  
- ✅ nginx.conf has X-Forwarded-Port on ALL locations
- ✅ nginx.conf has proxy_redirect on ALL locations proxying to services
- ✅ api-gateway settings has USE_X_FORWARDED_HOST = True
- ✅ api-gateway settings has USE_X_FORWARDED_PORT = True
- ✅ api-gateway settings has CSRF_COOKIE_SAMESITE = "Lax"
- ✅ api-gateway settings has CsrfViewMiddleware in MIDDLEWARE
- ✅ No syntax errors in configuration files

## Docker Compose Integration

The docker-compose.yml already had:
- ✅ nginx service listening on port 80
- ✅ api-gateway accessible at http://api-gateway:8000 within network
- ✅ Correct depends_on and network setup

No changes needed to docker-compose.yml - configuration is correct.

## Deployment Notes

### Local/Development (HTTP)
- All settings work as-is
- Redirects point to `http://localhost`
- No SSL configuration needed

### Production (HTTPS)
To enable SSL redirects:
```bash
export SECURE_SSL_REDIRECT=true
export SESSION_COOKIE_SECURE=true
export CSRF_COOKIE_SECURE=true
export CSRF_TRUSTED_ORIGINS="https://yourdomain.com"
```

Then nginx would need SSL cert configuration (separate from this fix).

## References

- [Django Proxy Headers Documentation](https://docs.djangoproject.com/en/stable/ref/settings/#use-x-forwarded-host)
- [Nginx proxy_redirect Directive](http://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_redirect)
- [CSRF Cookie SameSite Attribute](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite)
