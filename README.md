# 24513 Walnut Street — Buyer Offering Memorandum

Static buyer-facing Offering Memorandum website for 24513–24519 Walnut Street, Newhall, California.

The buyer experience includes a 12-image subject gallery, sourced investment and location narratives, current and pro forma financial analysis, two photo-backed listing-agent profiles, and six source-backed sale-comparable profiles synchronized with the comparable map.

All substantive content and page assets load locally. The location and comparable sections support lazy-loaded Google Maps JavaScript API maps, including roadmap, satellite, transit, Street View, and synchronized comparable markers. A restricted browser key may be supplied through `window.LAAA_GOOGLE_MAPS_BROWSER_KEY` or the blank `google-maps-browser-key` meta value. High-resolution committed Google maps remain available when the API is blocked or unavailable. No server credential is included in the public site.

## Build and validate

```powershell
python scripts/build_site.py
python scripts/validate_site.py
npm ci --ignore-scripts
npx playwright install chromium webkit
npm run test:ui
```

The UI regression suite expects the local server (`python scripts/serve_local.py`) on port 8766. The pinned package/lock files install the Playwright runtime reproducibly; the browser-install command installs its Chromium and WebKit executables. The suite covers the required viewport matrix, zero-scroll mobile tables, financial basis tabs, synchronized list/map selection, gallery behavior, map fallbacks, agent rendering, responsive overflow and collision checks, 44-pixel controls, dynamic wrapped-banner menu placement, menu keyboard behavior, reduced motion, forced colors, and Chromium/WebKit mobile emulation. Review screenshots are written to the ignored `qa/` directory.

The public repository intentionally excludes leases, tenant information, seller communications, internal underwriting, review workbooks, MLS source PDFs, and other confidential deal materials.

Selected subject and comparable images are extracted from the archived MLS evidence authorized for this offering. Their visible MLS attribution is preserved.
