# 24513 Walnut Street — Buyer Offering Memorandum

Static buyer-facing Offering Memorandum website for 24513–24519 Walnut Street, Newhall, California.

## Build and validate

```powershell
python scripts/build_site.py
python scripts/validate_site.py
npm ci --ignore-scripts
npx playwright install chromium webkit
npm run test:ui
```

The UI regression suite expects the local server (`python scripts/serve_local.py`) on port 8766. The pinned package/lock files install the Playwright runtime reproducibly; the browser-install command installs its Chromium and WebKit executables. The suite covers the required viewport matrix, responsive overflow and collision checks, 44-pixel controls, dynamic wrapped-banner menu placement, menu keyboard behavior, table access, reduced motion, forced colors, and Chromium/WebKit mobile emulation. Review screenshots are written to the ignored `qa/` directory.

The public repository intentionally excludes leases, tenant information, seller communications, internal underwriting, review workbooks, MLS source PDFs, and other confidential deal materials.

