# Public showcase and owner workspace

The public home page is a static, synthetic result derived from the independent test fixtures. It never fetches runs, queries the database or calls OpenRouter. To publish another result, curate and anonymize it, then update app/static/index.html and showcase.csv through a reviewed commit. Private uploads and review notes are never published automatically.

Set RECON_OWNER_PASSWORD in Vercel Project Settings → Environment Variables for Production and Preview, then redeploy. Use a password manager to generate a unique random password of at least 32 characters. Keep DATABASE_URL and OPENROUTER_API_KEY server-side. GitHub Actions secrets do not configure Vercel.

Open /workspace and sign in with username owner and that password. The browser's HTTPS Basic authentication dialog retains the credentials; use a private browser window and close it when finished. Do not put credentials in URLs or source files.

All non-public HTTP routes, including private reads, exports, API docs, readiness and model calls, require authentication. Authenticated mutations additionally require X-Recon-Request: 1 and reject cross-site origins. The workspace sends this header automatically. Private responses use Cache-Control: private, no-store.

On Vercel, a missing or short owner password blocks private requests with 503. With a valid configured password, unauthenticated requests return 401. Public showcase and health remain available. An OpenRouter key also enables mandatory protection outside Vercel; unconfigured local development without a provider remains accessible.

Runtime verification: scripts/verify_owner.py tests real HTTP requests and blocked calls before database/provider access. scripts/verify_browser.py exercises the authenticated workflow, and verify_mapping.py uses a local fake provider to validate authenticated suggestions without paid calls.

This protects this deployment. Older Vercel deployment URLs running unprotected code must also be protected or deleted. Rotate the OpenRouter API key after retiring those deployments so old copies cannot spend with the previous key. Use the new key only in protected deployments. An OpenRouter key spending limit can additionally bound owner mistakes or credential compromise.
