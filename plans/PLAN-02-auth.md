# PLAN-02: Authentication, Sessions, TOTP 2FA, Rate Limiting, WS Tickets

Goal: the complete SPEC 2.1 AUTH block plus the WebSocket ticket endpoint. RS256 access tokens (15 min), rotating refresh tokens in an httpOnly SameSite=Strict cookie (30 days), TOTP 2FA with QR provisioning and lockout, per-IP rate limiting on auth routes, password reset, and a CLI seed script (there is no public registration; single-user system).

Prerequisites: PLAN-01 complete. Spec references: SPEC 2.1 (AUTH-01 to AUTH-08), 3.2, 6.1, 6.2 (ticket), 13.1.

## Files to create or touch

```
backend\app\security\__init__.py
backend\app\security\jwt.py
backend\app\security\passwords.py
backend\app\security\totp.py
backend\app\security\ratelimit.py
backend\app\deps.py
backend\app\services\__init__.py
backend\app\services\auth_service.py
backend\app\services\audit.py
backend\app\routers\auth.py
backend\scripts\generate_keys.py
backend\scripts\create_user.py
backend\tests\test_auth.py
backend\app\main.py            (include router)
```

## Steps in order

### Step 1: generate the RS256 keypair

`backend\scripts\generate_keys.py`: uses the `cryptography` package (already installed via PyJWT[crypto]) to generate a 2048-bit RSA keypair and write `keys\jwt_private.pem` and `keys\jwt_public.pem` under the Odin root. Refuse to overwrite existing files.

Run: `docker compose -f docker-compose.dev.yml run --rm -v ./keys:/keys gateway-api python scripts/generate_keys.py /keys`

If the keys mount is read-only in the gateway service, run the script on any writable mount then move the files; the API only ever needs read access.

### Step 2: passwords.py

Wrap passlib `CryptContext(schemes=["bcrypt"])` with `hash_password` and `verify_password`. Nothing else touches passlib.

### Step 3: jwt.py

- `create_access_token(user_id, scope="access") -> str`: RS256, claims `sub`, `scope`, `iat`, `exp` (now + 15 min), signed with the private key file.
- `create_preauth_token(user_id) -> str`: same but `scope="preauth"`, exp 5 minutes. Issued after password success when 2FA is enabled; grants access ONLY to the TOTP verification endpoint.
- `decode_token(token, required_scope) -> dict`: verify with the public key, check `scope` equals `required_scope`, raise on mismatch or expiry.

### Step 4: auth_service.py and sessions

- `login(email, password)`: verify user; if `two_factor_enabled` return `{"requires_totp": True, "pre_auth_token": ...}`; else issue tokens (Step 6 shape).
- Refresh tokens: generate with `secrets.token_urlsafe(48)`. Store only `hashlib.sha256(raw).hexdigest()` in `sessions.refresh_token_hash` with `expires_at = now + 30 days`. Lookup on refresh is by hash, which is inherently timing-safe as a DB equality on a digest.
- `rotate_refresh(raw_token)`: find session by hash; if missing or expired raise 401; delete that session row, create a new one, return new access + new raw refresh. Rotation is mandatory (SPEC 13.1).
- `logout(raw_token)`: delete session row.
- Every auth event (login success, login failure, refresh, logout, lockout, reset) writes an `activity_log` row via `services\audit.py` helper `log_event(user_id, event_type, source, description, ...)` with `source='web'`.

### Step 5: totp.py with lockout (AUTH-03, AUTH-07)

- Setup: `POST /api/v1/auth/totp/setup` (requires full access token): generate `pyotp.random_base32()`, store on user (encrypt with ENCRYPTION_KEY using AESGCM before storing; never store the raw secret), return the `provisioning_uri(name=email, issuer_name="ODIN")` for the frontend to render as QR. A follow-up `POST /api/v1/auth/totp/enable` with a valid current code flips `two_factor_enabled`.
- Verify: `POST /api/v1/auth/totp/verify` with the preauth token plus `{"code": "123456"}`:
  1. FIRST check `totp_locked_until`: if in the future, return 423 with seconds remaining. Do this before touching the code.
  2. Verify with `pyotp.TOTP(secret).verify(code, valid_window=1)` (one step of clock skew).
  3. On failure: increment `totp_failed_attempts`; if it reaches 5, set `totp_locked_until = now + 15 minutes`, reset the counter, and log a `totp_lockout` audit event. Return 401.
  4. On success: zero the counter, clear `totp_locked_until`, issue the full token pair.

### Step 6: token delivery shape

Successful auth (password-only, or TOTP verify) returns JSON `{"access_token": ..., "token_type": "bearer", "expires_in": 900}` AND sets the refresh cookie:

```python
response.set_cookie(
    key="odin_refresh",
    value=raw_refresh,
    httponly=True,
    secure=settings.ENVIRONMENT != "dev",
    samesite="strict",
    max_age=60 * 60 * 24 * 30,
    path="/api/v1/auth",
)
```

`POST /api/v1/auth/refresh` reads the cookie (no body), rotates, sets the new cookie, returns a new access token. `POST /api/v1/auth/logout` deletes the session and clears the cookie.

### Step 7: deps.py

`get_current_user`: FastAPI dependency reading `Authorization: Bearer` header, `decode_token(..., required_scope="access")`, load user, bind `user_id` into the structlog context, return the user. All protected routers depend on it. A missing or bad token returns 401 with `WWW-Authenticate: Bearer` (AUTH-06; the SPA handles the redirect).

### Step 8: ratelimit.py (AUTH rate limit, SPEC 3.2)

Redis fixed-window limiter: key `rl:auth:{ip}`, `INCR` then `EXPIRE 60` when the value is 1; deny with 429 when the count exceeds 5. Apply as a dependency on `/auth/login`, `/auth/totp/verify`, `/auth/forgot`, `/auth/reset`. Resolve the client IP as: if the direct peer is a private/loopback address (the nginx or docker proxy), trust the FIRST entry of `X-Forwarded-For`; otherwise use the peer address and ignore the header entirely.

### Step 9: WS tickets (SPEC 6.2)

`POST /api/v1/ws-ticket` (full access token required): insert a `ws_tickets` row with `expires_at = now + 30 seconds`, return `{"ticket": id, "expires_in_seconds": 30}`. Consumption happens in PLAN-03; this plan only issues.

### Step 10: password reset (AUTH-05)

- `POST /api/v1/auth/forgot` with `{"email"}`: always return 202 regardless of whether the email matches (no user enumeration). If it matches, create a single-use reset token (random, sha256-stored, 30 min expiry; reuse the sessions table pattern with a dedicated in-Redis key `reset:{hash}` to avoid a schema change). If SMTP settings are filled, email the link; if SMTP is blank (dev), log the reset URL at INFO level instead.
- `POST /api/v1/auth/reset` with `{"token", "new_password"}`: validate, set password, delete ALL sessions for that user (forced global logout), audit-log it.

### Step 11: seed script

`backend\scripts\create_user.py` taking `--email`, `--name`, `--password` args (non-interactive), creating the single user. Run:

`docker compose -f docker-compose.dev.yml exec gateway-api python scripts/create_user.py --email alimoyo58@gmail.com --name Ali --password CHANGE_ME_NOW`

### Step 12: tests

`tests\test_auth.py` covering: login happy path, wrong password 401, refresh rotates (old cookie now 401), TOTP wrong code increments counter, 5th failure locks and 423 is returned even with the CORRECT code during lockout, rate limit returns 429 on the 6th login attempt in a minute, preauth token rejected on a normal protected route.

## Edge cases a weaker model would miss

1. **passlib 1.7.4 crashes with bcrypt >= 4.1** (`AttributeError: module 'bcrypt' has no attribute '__about__'`). PLAN-01 pins `bcrypt==4.0.1`. Do not "upgrade" it.
2. **bcrypt silently truncates at 72 bytes.** Reject passwords longer than 72 bytes at the schema level with a clear message.
3. **The preauth token must not open any protected route.** Scope checking in `decode_token` is the enforcement point; a weaker model often issues a normal access token before TOTP, which defeats 2FA entirely.
4. **Lockout check comes before code verification**, and the lockout response must be identical whether the submitted code was right or wrong, otherwise the lockout leaks code validity.
5. **`secure=True` cookies are not sent over plain http.** In dev (`ENVIRONMENT=dev`) set `secure=False` or login breaks on localhost; in prod it must be True. The conditional in Step 6 handles it; do not hardcode either way.
6. **SameSite=Strict requires same-origin.** The SPA must reach the API through the Vite proxy (dev) or same nginx origin (prod). If someone tests with the SPA on :5173 calling :8000 directly, the cookie will never be stored. This is a PLAN-08 contract, noted here because auth is where it visibly breaks.
7. **Cookie `path=/api/v1/auth`** keeps the refresh token off every other request, shrinking exposure. Logout and refresh both live under that path, so it works; do not set `path=/`.
8. **Store the TOTP secret encrypted** (AES-256-GCM with ENCRYPTION_KEY, 12-byte nonce prepended to ciphertext, base64 the blob). SPEC 13.2 requires credentials encrypted at rest; the TOTP secret is a credential.
9. **Timing:** compare nothing with `==` that is secret-derived except sha256 digests fetched by DB equality. For the WhatsApp-style raw comparisons later, `hmac.compare_digest` is the pattern; here the hash-lookup pattern avoids the issue.
10. **Do not add a /register endpoint.** Registration is the seed script only. An exposed register endpoint on a single-user system is pure attack surface.
11. **X-Forwarded-For spoofing:** only trust the header when the direct peer is the known proxy, else anyone can rotate fake IPs to bypass the rate limit.

## Acceptance criteria (verify each)

1. `pytest backend/tests/test_auth.py` passes inside the container: `docker compose -f docker-compose.dev.yml exec gateway-api pytest tests/test_auth.py -q`
2. curl login with wrong password returns 401 and an `activity_log` row with event_type `login_failed` exists.
3. curl login with correct password (2FA off) returns an access token and a `Set-Cookie: odin_refresh=...; HttpOnly; ...; SameSite=strict` header with `Path=/api/v1/auth`.
4. With 2FA enabled via the setup+enable flow, login returns `requires_totp: true`, and the code from an authenticator app (or `python -c` with pyotp using the secret) completes it.
5. Five consecutive wrong TOTP codes return 401 then the sixth attempt returns 423, including with the correct code, until 15 minutes pass.
6. Six login POSTs inside one minute from the same IP: the sixth returns 429.
7. `POST /api/v1/ws-ticket` with a bearer token returns a ticket; the row appears in `ws_tickets`.
8. Refresh flow: calling refresh twice with the same old cookie fails the second time (rotation proof).
