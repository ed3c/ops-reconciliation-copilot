# Google owner sign-in and public showcase

The public home page is a static synthetic result. It never fetches private runs or calls OpenRouter. Publish another result by curating and anonymizing it, then updating app/static/index.html and showcase.csv through a reviewed commit. Uploads and review notes are never published automatically.

## Google setup

1. Open [Google Auth Platform Clients](https://console.cloud.google.com/auth/clients), select or create a project, and configure the app branding/consent screen. This app only needs basic Google identity, not Gmail mailbox access.
2. Create an OAuth client of type **Web application**. If the consent configuration uses a test-user list, add your own Google account.
3. Add this exact **Authorized JavaScript origin**: https://ops-reconciliation-copilot.vercel.app . Add each other stable domain on which you intend to sign in separately. Use the public production domain, not a Vercel login-protected generated preview URL, for the initial live check.
4. Copy the client ID ending in .apps.googleusercontent.com. This implementation uses the GIS popup JavaScript callback; it does not need a client secret or an Authorized redirect URI. For local Google testing, authorize http://localhost and http://localhost:8000 and open the app using localhost.

## Vercel configuration

In [Vercel Environment Variables](https://vercel.com/noodles8/ops-reconciliation-copilot/settings/environment-variables), set:

| Variable | Value |
|---|---|
| GOOGLE_CLIENT_ID | Your Web application client ID; public identifier |
| OWNER_GOOGLE_EMAIL | One exact Gmail address you control, such as the Gmail used for your Vercel account |
| AUTH_SESSION_SECRET | A unique random server secret of at least 32 characters; generate with a password manager |
| OWNER_GOOGLE_SUB | Optional stable Google account ID pin; see below |

Keep DATABASE_URL and optional OpenRouter settings. Apply the intended Production/Preview scope and redeploy. GitHub Actions secrets do not configure Vercel. RECON_OWNER_PASSWORD is no longer a login method; remove the obsolete variable. Never reuse the OpenRouter key as the signing secret.

Vercel account ownership is not automatically checked. The configured Google identity is the explicit allowlist. This implementation intentionally accepts an exact verified @gmail.com address; arbitrary third-party email domains and Google Workspace accounts are outside this milestone. It does not equate dotted or plus-address aliases.

After your first successful owner login, open /auth/me on the same origin and copy your sub into OWNER_GOOGLE_SUB, then redeploy to pin the stable account ID too. Do not use a token-decoding website. Only a successfully verified allowlisted owner can access /auth/me; the client cannot select or replace the allowlist.

## Authentication flow

1. GET /workspace shows the sign-in page unless an owner session is present.
2. GET /auth/config provides the public client ID and random nonce, and sets a signed HttpOnly challenge cookie (10-minute validity). It does not reveal the owner email or secret.
3. The official Google button returns an ID token to JavaScript. JavaScript POSTs it to /auth/google with X-Recon-Request: 1. The server enforces same-origin checks and compares the verified token nonce with the signed challenge.
4. google-auth verifies the Google signature, audience, issuer and expiry. The server additionally requires email_verified, the exact allowed Gmail and optional sub pin. A valid Google token from another account receives 403 and creates no owner session.
5. An accepted identity is stored in an HttpOnly, SameSite=Lax signed session cookie. On HTTPS/Vercel it is Secure, uses the __Host- prefix, has Path=/ and no Domain. It expires at the earlier of the Google token expiry or one hour. Raw Google tokens are not stored in localStorage, the database or the session cookie.
6. Every private request checks the signed session, expiry, current Client ID and current owner allowlist before database/provider access. There is no Basic password fallback. Private responses use no-store. Writes require the custom header and reject cross-site origins.
7. Sign out clears the browser session and challenge cookies. Session cookies are stateless: logout does not revoke a previously copied cookie server-side. Rotate AUTH_SESSION_SECRET and redeploy to invalidate sessions on the new deployment; protect or retire older deployments retaining old configuration. There is no refresh token or automatic session renewal.

| Situation | Result |
|---|---|
| Public home page | 200; no AI calls |
| Anonymous /workspace | Sign-in page; no private data |
| Missing/invalid Google configuration | Login page explains setup; private APIs and /auth/config return 503 |
| No session, invalid signature or expired session | Private APIs return 401 |
| Valid identity outside the owner allowlist | 403 |
| Valid owner session | Private API access, with CSRF checks on writes |

## Verification and limits

scripts/verify_owner.py uses real HTTP and temporary RSA keys with Google's actual verifier. Only certificate retrieval is replaced in a test-only server factory. It checks invalid signatures, audience/issuer/expiry, nonce, other-account denial, CSRF, session access and logout. tests/test_google_access.py checks cookie flags and tampering, allowlist changes and secret rotation.

scripts/verify_browser.py replaces the Google UI script with a clearly labeled local test button and runs login, upload, review, export and logout. scripts/verify_mapping.py additionally uses a local fake model. These prove integration behavior, not a successful live Google login. Production imports app.main:app and has no test-issuer switch; the test factory and keys are excluded from the file-upload deployment.

Live verification remains: configure your Google client, sign in as the allowed owner, check another Google account is refused, complete a real model suggestion/review/export, then sign out and confirm private APIs reject access. Save only sanitized evidence; never publish ID tokens, cookies, keys or complete HAR files.

The public showcase remains free of model calls. This does not provide global request-rate limits, immediate token revocation, multi-tenant access control or a total provider spending cap. Keep old/generated deployment URLs protected; rotate model keys retained by older unprotected deployments.

Sources: [Google setup](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid), [ID token verification](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token).
