const fs = require('fs');
const path = require('path');
const { chromium, webkit } = require('playwright');

const baseUrl = process.env.SITE_URL || 'http://127.0.0.1:8766/';
const baseOrigin = new URL(baseUrl).origin;
const outputDir = path.resolve(process.env.QA_DIR || 'qa');
fs.mkdirSync(outputDir, { recursive: true });

const viewports = [
  [1920, 1080], [1440, 900], [1024, 768], [768, 1024],
  [430, 932], [390, 844], [375, 812], [844, 390],
];
const screenshotWidths = new Set(['1920x1080', '1440x900', '768x1024', '430x932', '390x844', '375x812', '844x390']);
const failures = [];

function check(condition, message) {
  if (!condition) failures.push(message);
}

async function inspectViewport(browser, width, height, options = {}) {
  const key = `${width}x${height}${options.suffix || ''}`;
  const context = await browser.newContext({
    viewport: { width, height },
    reducedMotion: options.reducedMotion || 'no-preference',
    forcedColors: options.forcedColors || 'none',
    isMobile: Boolean(options.isMobile),
    hasTouch: Boolean(options.hasTouch),
  });
  await context.route('**/*', async route => {
    const requestUrl = route.request().url();
    const url = new URL(requestUrl);
    if (/^https?:$/.test(url.protocol) && url.origin !== baseOrigin) await route.abort('blockedbyclient');
    else await route.continue();
  });
  const page = await context.newPage();
  const runtimeErrors = [];
  page.on('console', message => { if (message.type() === 'error') runtimeErrors.push(`console: ${message.text()}`); });
  page.on('pageerror', error => runtimeErrors.push(`pageerror: ${error.message}`));
  page.on('requestfailed', request => {
    const requestUrl = new URL(request.url());
    if (requestUrl.origin === baseOrigin) runtimeErrors.push(`requestfailed: ${request.url()} ${request.failure()?.errorText || ''}`);
  });

  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  await page.evaluate(() => document.querySelectorAll('img[loading="lazy"]').forEach(image => { image.loading = 'eager'; }));
  await page.evaluate(async () => {
    for (let y = 0; y < document.documentElement.scrollHeight; y += Math.max(320, window.innerHeight * .8)) {
      window.scrollTo(0, y);
      await new Promise(resolve => setTimeout(resolve, 18));
    }
    await Promise.all(Array.from(document.images, image => image.decode().catch(() => undefined)));
    window.scrollTo(0, 0);
  });
  await page.waitForFunction(() => Array.from(document.images).every(image => image.complete && image.naturalWidth > 0));

  const result = await page.evaluate(() => {
    const visible = element => {
      if (!element) return false;
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    };
    const doc = document.documentElement;
    const heroCard = document.querySelector('.hero-card').getBoundingClientRect();
    const kpiRail = document.querySelector('.hero-kpi-rail').getBoundingClientRect();
    const heroCollision = Math.max(0, Math.min(heroCard.bottom, kpiRail.bottom) - Math.max(heroCard.top, kpiRail.top));
    const controlSelector = '.button,.source-links a,.menu-toggle,#primary-nav a,.mobile-cta a,.gallery-item a,.lightbox button,.map-toolbar button,.map-toolbar a,.basis-tabs button,.comp-view-tabs button,.comp-summary,.map-pin,.comp-map-toolbar button,.comp-stepper button,.comparison-metric-tabs button,.comparison-bar:not(.subject-row),.subject-map-action,.subject-baseline-strip>a,.selected-actions a,.comp-profile-disclosures summary,.rent-evidence-details summary,.agent-actions a,.row-note summary';
    const controls = Array.from(document.querySelectorAll(controlSelector)).filter(visible).map(element => ({
      text: element.getAttribute('aria-label') || element.textContent.trim().replace(/\s+/g, ' '),
      width: Math.round(element.getBoundingClientRect().width * 10) / 10,
      height: Math.round(element.getBoundingClientRect().height * 10) / 10,
    }));
    const clipped = Array.from(document.querySelectorAll('h1,h2,h3,h4,p,a,button,b,strong,span'))
      .filter(visible)
      .filter(element => !element.classList.contains('sr-only'))
      .filter(element => !element.closest('.table-shell,.gallery-item,.comp-thumb,.comp-map-canvas,.lightbox'))
      .filter(element => {
        const style = getComputedStyle(element);
        return /(hidden|clip)/.test(style.overflow + style.overflowX + style.overflowY) &&
          (element.scrollWidth > element.clientWidth + 1 || element.scrollHeight > element.clientHeight + 1);
      })
      .map(element => `${element.tagName.toLowerCase()}.${element.className || ''}:${element.textContent.trim().slice(0, 45)}`);
    const tables = Array.from(document.querySelectorAll('.table-shell')).filter(visible).map(region => ({
      tabindex: region.getAttribute('tabindex'),
      role: region.getAttribute('role'),
      label: region.getAttribute('aria-label'),
      overflows: region.scrollWidth > region.clientWidth + 1,
      hasVisibleCue: (() => {
        const cue = region.closest('.table-region')?.querySelector('.table-scroll-cue');
        return Boolean(cue && visible(cue));
      })(),
    }));
    const rentRoll = document.querySelector('.rent-roll-table');
    const rentRows = Array.from(rentRoll.querySelectorAll('tbody tr'));
    const images = Array.from(document.images).map(img => ({ src: img.getAttribute('src'), alt: img.getAttribute('alt'), complete: img.complete, naturalWidth: img.naturalWidth }));
    const hashLinks = Array.from(document.querySelectorAll('a[href^="#"]')).map(link => link.getAttribute('href')).filter(href => href !== '#');
    return {
      documentOverflow: doc.scrollWidth - doc.clientWidth,
      heroCollision,
      controls,
      clipped,
      tables,
      rentRoll: {
        overflows: rentRoll.scrollWidth > rentRoll.clientWidth + 1,
        headerVisible: visible(rentRoll.querySelector('thead')),
        rowCount: rentRows.length,
        distinctRowTops: new Set(rentRows.map(row => Math.round(row.getBoundingClientRect().top))).size,
      },
      images,
      compCount: document.querySelectorAll('[data-comp-card]').length,
      compSummaryCount: document.querySelectorAll('.comp-summary').length,
      compPinCount: document.querySelectorAll('.map-pin').length,
      compSelectedCount: document.querySelectorAll('[data-comp-preview]').length,
      compMetricPanelCount: document.querySelectorAll('[data-comp-metric-panel]').length,
      subjectBaselineCount: document.querySelectorAll('.subject-baseline').length,
      rentBenchmarkCount: document.querySelectorAll('.rent-benchmark-card').length,
      rentMapFallback: Boolean(document.querySelector('[data-map-fallback="rents"]')),
      mobileProfileDetailsClosed: Array.from(document.querySelectorAll('[data-profile-detail]')).every(detail => !detail.open),
      galleryCount: document.querySelectorAll('[data-gallery-link]').length,
      agentCount: document.querySelectorAll('.agent-card').length,
      overviewParagraphs: document.querySelectorAll('#overview .narrative-paragraph').length,
      locationParagraphs: document.querySelectorAll('#location .narrative-paragraph').length,
      highlightCount: document.querySelectorAll('.highlight-ledger article').length,
      forbiddenFocus: document.body.textContent.includes('FOCUS THE EVIDENCE') || document.body.textContent.includes('Focus the evidence'),
      hasGalleryDialog: Boolean(document.querySelector('[data-gallery-dialog]')),
      hasHeadshots: Boolean(document.querySelector('img[src="assets/images/glen-scher.jpg"]')) && Boolean(document.querySelector('img[src="assets/images/filip-niculete.jpg"]')),
      hasMapFallbacks: document.querySelectorAll('.map-frame img').length >= 4 &&
        Boolean(document.querySelector('.comp-map-canvas img')) &&
        Boolean(document.querySelector('[data-map-fallback="rents"]')),
      h1Count: document.querySelectorAll('h1').length,
      landmarks: { main: Boolean(document.querySelector('main')), nav: Boolean(document.querySelector('nav')), footer: Boolean(document.querySelector('footer')) },
      brokenAnchors: hashLinks.filter(href => !document.querySelector(href)),
      unresolved: /{{|}}|TODO|PLACEHOLDER/i.test(document.documentElement.innerHTML),
      noindex: document.querySelector('meta[name="robots"]')?.content.includes('noindex') || false,
      scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
    };
  });

  check(result.documentOverflow <= 1, `${key}: document overflow ${result.documentOverflow}px`);
  check(result.heroCollision <= 1, `${key}: hero card overlaps KPI rail by ${result.heroCollision}px`);
  result.controls.forEach(control => check(control.height >= 44 && control.width >= 44, `${key}: undersized control "${control.text}" ${control.width}x${control.height}`));
  check(result.clipped.length === 0, `${key}: clipped text ${result.clipped.join(', ')}`);
  check(result.h1Count === 1, `${key}: expected one H1, found ${result.h1Count}`);
  check(Object.values(result.landmarks).every(Boolean), `${key}: missing landmark ${JSON.stringify(result.landmarks)}`);
  check(result.brokenAnchors.length === 0, `${key}: broken anchors ${result.brokenAnchors.join(', ')}`);
  check(!result.unresolved, `${key}: unresolved template or placeholder text`);
  check(result.noindex, `${key}: privacy noindex missing`);
  check(result.compCount === 6 && result.compSummaryCount === 6 && result.compPinCount === 6, `${key}: comp explorer counts cards=${result.compCount} summaries=${result.compSummaryCount} pins=${result.compPinCount}`);
  check(result.compSelectedCount === 6 && result.compMetricPanelCount === 3 && result.subjectBaselineCount === 1, `${key}: redesigned sale-comp structures missing selected=${result.compSelectedCount} metrics=${result.compMetricPanelCount} subject=${result.subjectBaselineCount}`);
  check(result.rentBenchmarkCount === 2 && result.rentMapFallback, `${key}: redesigned rent evidence missing cards=${result.rentBenchmarkCount} fallback=${result.rentMapFallback}`);
  check(result.galleryCount === 12 && result.hasGalleryDialog, `${key}: gallery incomplete count=${result.galleryCount}`);
  check(result.agentCount === 2 && result.hasHeadshots, `${key}: Glen/Filip profiles or headshots missing`);
  check(result.overviewParagraphs === 3 && result.locationParagraphs === 3, `${key}: narrative paragraph contract failed`);
  check(result.highlightCount === 6, `${key}: expected six investment highlights, found ${result.highlightCount}`);
  check(!result.forbiddenFocus, `${key}: removed Focus the evidence language is still present`);
  check(result.hasMapFallbacks, `${key}: accessible local map fallbacks missing`);
  result.images.forEach(image => {
    check(Boolean(image.alt), `${key}: missing alt text on ${image.src}`);
    check(image.complete && image.naturalWidth > 0, `${key}: broken image ${image.src}`);
  });
  result.tables.forEach((table, index) => {
    check(table.tabindex === '0' && table.role === 'region' && Boolean(table.label), `${key}: table ${index + 1} lacks keyboard region semantics`);
    if (width <= 760) check(!table.overflows, `${key}: mobile table ${index + 1} still scrolls horizontally`);
    else if (table.overflows) check(table.hasVisibleCue, `${key}: table ${index + 1} overflow cue is not visible`);
  });
  if (width <= 760) {
    check(!result.rentRoll.overflows, `${key}: mobile rent roll still scrolls horizontally`);
    check(result.rentRoll.headerVisible, `${key}: mobile rent roll header is hidden`);
    check(result.rentRoll.rowCount === 3 && result.rentRoll.distinctRowTops === 3, `${key}: mobile rent roll is not one continuous three-row table`);
    check(result.mobileProfileDetailsClosed, `${key}: comp profile details should begin collapsed on mobile`);
  }
  if (options.reducedMotion === 'reduce') check(result.scrollBehavior === 'auto', `${key}: reduced-motion scroll behavior is ${result.scrollBehavior}`);
  check(runtimeErrors.length === 0, `${key}: runtime errors ${runtimeErrors.join('; ')}`);

  if (screenshotWidths.has(`${width}x${height}`) && !options.suffix) {
    await page.screenshot({ path: path.join(outputDir, `walnut-${width}x${height}.png`), fullPage: true });
  }

  if (width <= 900 && !options.skipMenu) {
    const toggle = page.locator('.menu-toggle');
    if (width === 375) await page.locator('.preview-band').evaluate(element => { element.textContent += ' — approved recipients only'; });
    await toggle.click();
    check(await toggle.getAttribute('aria-expanded') === 'true', `${key}: menu did not open`);
    check((await toggle.textContent()).includes('Close navigation'), `${key}: open menu lacks Close accessible name`);
    check(await page.evaluate(() => document.activeElement === document.querySelector('#primary-nav a')), `${key}: first menu link was not focused`);
    const menuGeometry = await page.evaluate(() => ({
      headerBottom: document.querySelector('.site-header').getBoundingClientRect().bottom,
      navTop: document.querySelector('#primary-nav').getBoundingClientRect().top,
      backdropTop: document.querySelector('.menu-backdrop').getBoundingClientRect().top,
    }));
    check(Math.abs(menuGeometry.navTop - menuGeometry.headerBottom) <= 1, `${key}: menu top ${menuGeometry.navTop} does not match header bottom ${menuGeometry.headerBottom}`);
    check(Math.abs(menuGeometry.backdropTop - menuGeometry.headerBottom) <= 1, `${key}: backdrop top ${menuGeometry.backdropTop} does not match header bottom ${menuGeometry.headerBottom}`);
    const firstMenuLink = page.locator('#primary-nav a').first();
    const firstTargetId = (await firstMenuLink.getAttribute('href')).slice(1);
    await firstMenuLink.click();
    await page.waitForFunction(targetId => document.activeElement?.id === targetId, firstTargetId);
    check(await toggle.getAttribute('aria-expanded') === 'false', `${key}: selecting a destination did not close the menu`);
    check(await page.evaluate(targetId => document.activeElement?.id === targetId, firstTargetId), `${key}: menu destination did not receive focus`);
    await toggle.click();
    check(await page.evaluate(() => document.activeElement === document.querySelector('#primary-nav a')), `${key}: first menu link was not refocused`);
    await page.keyboard.press('Escape');
    check(await toggle.getAttribute('aria-expanded') === 'false', `${key}: Escape did not close menu`);
    check(await page.evaluate(() => document.activeElement === document.querySelector('.menu-toggle')), `${key}: focus was not restored after Escape`);
  }

  if (width === 390 && !options.suffix) {
    const gsrRow = page.locator('.mobile-financial-table tbody tr').filter({ hasText: 'Gross Scheduled Rent' }).first();
    const before = await gsrRow.locator('td').first().textContent();
    await page.locator('[data-fin-basis="unit"]').click();
    const after = await gsrRow.locator('td').first().textContent();
    check(before.trim() === '$68,400' && after.trim() === '$22,800', `${key}: financial basis tabs did not recalculate current GSR (${before} -> ${after})`);
    await page.locator('[data-fin-basis="sf"]').click();
    check((await gsrRow.locator('td').first().textContent()).trim() === '$28.93', `${key}: per-SF basis did not render expected current GSR`);

    await page.locator('[data-location-view="transit"]').click();
    check(await page.locator('[data-location-panel="transit"]').isVisible(), `${key}: transit map fallback did not activate`);

    await page.locator('[data-comp-view="map"]').click();
    check(await page.locator('.comp-map-panel').isVisible(), `${key}: mobile comp map mode did not activate`);
    await page.locator('.comp-map-panel').scrollIntoViewIfNeeded();
    await page.locator('.map-pin[data-comp-select="coronel"]').click();
    check(await page.locator('[data-comp-preview="coronel"]').isVisible(), `${key}: selecting pin 2 did not update the preview`);
    check(await page.locator('.comp-summary[data-comp-select="coronel"]').getAttribute('aria-pressed') === 'true', `${key}: pin/list selection did not synchronize`);
    await page.locator('[data-comp-next]').click();
    check(await page.locator('[data-comp-preview="oro-vista"]').isVisible(), `${key}: comp next control did not advance`);
    const orderedComps = ['atwood', 'coronel', 'oro-vista', 'pinewood', 'santol', 'harding'];
    await page.locator('.map-pin[data-comp-select="atwood"]').click();
    for (let index = 0; index < orderedComps.length; index += 1) {
      const expected = orderedComps[index];
      check(await page.locator(`[data-comp-preview="${expected}"]`).isVisible(), `${key}: previous/next sequence did not show ${expected}`);
      check(await page.locator(`.comp-summary[data-comp-select="${expected}"]`).getAttribute('aria-pressed') === 'true', `${key}: previous/next sequence did not synchronize ${expected}`);
      if (index < orderedComps.length - 1) await page.locator('[data-comp-next]').click();
    }
    await page.locator('[data-comp-metric="ppu"]').click();
    check(await page.locator('[data-comp-metric-panel="ppu"]').isVisible(), `${key}: price-per-unit comparison did not activate`);
    await page.locator('[data-comp-map-type="satellite"]').click();
    const firstProfileDetail = page.locator('.comp-profile').first().locator('[data-profile-detail]').first();
    await firstProfileDetail.locator('summary').click();
    check(await firstProfileDetail.getAttribute('open') !== null, `${key}: mobile comp disclosure did not open`);

    const firstGalleryLink = page.locator('[data-gallery-link]').first();
    await firstGalleryLink.click();
    check(await page.locator('[data-gallery-dialog]').getAttribute('open') !== null, `${key}: gallery dialog did not open`);
    const firstGallerySource = await page.locator('[data-gallery-image]').getAttribute('src');
    await page.locator('[data-gallery-next]').click();
    const secondGallerySource = await page.locator('[data-gallery-image]').getAttribute('src');
    check(firstGallerySource !== secondGallerySource, `${key}: gallery next control did not change the image`);
    await page.keyboard.press('Escape');
    check(await page.locator('[data-gallery-dialog]').getAttribute('open') === null, `${key}: Escape did not close gallery dialog`);
  }

  await context.close();
}

async function inspectDelayedMapsKey(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  let mapsRequests = 0;
  const fakeMapsApi = `
    (() => {
      class FakeStreetView {
        setVisible(value) { this.visible = value; }
        setPosition(value) { this.position = value; }
        setPov(value) { this.pov = value; }
      }
      class FakeMap {
        constructor(element, options) {
          if (element.hidden) throw new Error('Map canvas was hidden during construction');
          this.element = element;
          this.options = options;
          this.mapTypeId = 'roadmap';
          this.streetView = new FakeStreetView();
          window.__fakeMaps.push(this);
        }
        getStreetView() { return this.streetView; }
        setMapTypeId(value) { this.mapTypeId = value; }
        setZoom(value) { this.zoom = value; }
        panTo(value) { this.center = value; }
        fitBounds() {}
      }
      class FakeTransitLayer { setMap(value) { this.map = value; } }
      class FakeBounds { extend() {} }
      class FakeCircle { constructor(options) { Object.assign(this, options); window.__fakeCircles.push(this); } }
      class FakeMarker {
        constructor(options) { Object.assign(this, options); }
        addListener() {}
      }
      window.__fakeMaps = [];
      window.__fakeCircles = [];
      window.google = {
        maps: {
          importLibrary: async name => name === 'maps' ? { Map: FakeMap } : { AdvancedMarkerElement: FakeMarker },
          TransitLayer: FakeTransitLayer,
          LatLngBounds: FakeBounds,
          Circle: FakeCircle,
          event: { trigger() {} }
        }
      };
      window.LAAAInitGoogleMaps();
    })();
  `;
  await context.route('**/*', async route => {
    const requestUrl = new URL(route.request().url());
    if (requestUrl.hostname === 'maps.googleapis.com') {
      mapsRequests += 1;
      if (mapsRequests === 1) {
        await route.abort('failed');
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 250));
      await route.fulfill({ status: 200, contentType: 'application/javascript', body: fakeMapsApi });
    } else if (/^https?:$/.test(requestUrl.protocol) && requestUrl.origin !== baseOrigin) {
      await route.abort('blockedbyclient');
    } else {
      await route.continue();
    }
  });

  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });
  await page.locator('[data-location-map]').scrollIntoViewIfNeeded();
  await page.waitForTimeout(100);
  check(mapsRequests === 0, `delayed-maps-key: map requested before a browser key existed`);

  await page.evaluate(() => { window.LAAA_GOOGLE_MAPS_BROWSER_KEY = 'test-browser-key'; });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(100);
  await page.locator('[data-location-map]').scrollIntoViewIfNeeded();
  await page.locator('[data-location-view="satellite"]').click();
  await page.waitForFunction(() => document.querySelector('[data-map-status="location"]')?.textContent.includes('Google map data'));
  const fallbackState = await page.evaluate(() => ({
    visiblePanels: Array.from(document.querySelectorAll('[data-location-panel]')).filter(panel => !panel.hidden).map(panel => panel.dataset.locationPanel),
    activeView: document.querySelector('[data-location-view][aria-pressed="true"]')?.dataset.locationView,
  }));
  check(fallbackState.activeView === 'satellite' && fallbackState.visiblePanels.length === 1 && fallbackState.visiblePanels[0] === 'satellite', `delayed-maps-key: failure fallback desynced ${JSON.stringify(fallbackState)}`);
  await page.waitForFunction(() => window.__fakeMaps?.some(map => map.element.dataset.googleMap === 'location'));
  check(await page.evaluate(() => !window.__fakeMaps.some(map => map.element.dataset.googleMap === 'comps')), 'delayed-maps-key: hidden mobile comparable map initialized before becoming visible');
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.waitForFunction(() => window.__fakeMaps?.some(map => map.element.dataset.googleMap === 'comps'));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('[data-comp-view="map"]').click();
  await page.waitForFunction(() => window.__fakeMaps?.some(map => map.element.dataset.googleMap === 'comps'));
  await page.locator('[data-comp-map-type="satellite"]').click();
  await page.evaluate(selector => {
    const panel = document.querySelector(selector);
    const start = new Event('touchstart', { bubbles: true });
    const end = new Event('touchend', { bubbles: true });
    Object.defineProperty(start, 'changedTouches', { value: [{ clientX: 300 }] });
    Object.defineProperty(end, 'changedTouches', { value: [{ clientX: 180 }] });
    panel.dispatchEvent(start);
    panel.dispatchEvent(end);
  }, '[data-google-map="comps"]');
  check(await page.locator('.comp-summary[aria-pressed="true"]').getAttribute('data-comp-select') === 'atwood', 'delayed-maps-key: panning the map changed the selected comp');
  await page.evaluate(selector => {
    const panel = document.querySelector(selector);
    const start = new Event('touchstart', { bubbles: true });
    const end = new Event('touchend', { bubbles: true });
    Object.defineProperty(start, 'changedTouches', { value: [{ clientX: 300 }] });
    Object.defineProperty(end, 'changedTouches', { value: [{ clientX: 180 }] });
    panel.dispatchEvent(start);
    panel.dispatchEvent(end);
  }, '.comp-selected-stack');

  const result = await page.evaluate(() => ({
    activeView: document.querySelector('[data-location-view][aria-pressed="true"]')?.dataset.locationView,
    mapTypeId: window.__fakeMaps.find(map => map.element.dataset.googleMap === 'location')?.mapTypeId,
    zoom: window.__fakeMaps.find(map => map.element.dataset.googleMap === 'location')?.zoom,
    selectedComp: document.querySelector('.comp-summary[aria-pressed="true"]')?.dataset.compSelect,
    compCenter: window.__fakeMaps.find(map => map.element.dataset.googleMap === 'comps')?.center,
    compMapTypeId: window.__fakeMaps.find(map => map.element.dataset.googleMap === 'comps')?.mapTypeId,
    rentCircleCount: window.__fakeCircles.length,
  }));
  check(mapsRequests === 2, `delayed-maps-key: expected one failed request and one automatic retry, found ${mapsRequests}`);
  check(result.activeView === 'satellite', `delayed-maps-key: active view reset to ${result.activeView}`);
  check(result.mapTypeId === 'satellite' && result.zoom === 19, `delayed-maps-key: Google map did not preserve Satellite (${result.mapTypeId}, zoom ${result.zoom})`);
  check(result.selectedComp === 'coronel', `delayed-maps-key: swipe selected ${result.selectedComp} instead of Coronel`);
  check(result.compCenter?.lat === 34.2837309 && result.compCenter?.lng === -118.4456534, `delayed-maps-key: swipe did not pan the live comp map`);
  check(result.compMapTypeId === 'satellite', `delayed-maps-key: live comparable map did not switch to Satellite`);
  check(result.rentCircleCount === 2, `delayed-maps-key: expected two rent-survey radii, found ${result.rentCircleCount}`);
  await context.close();
}

(async () => {
  const chrome = await chromium.launch({ headless: true });
  for (const [width, height] of viewports) await inspectViewport(chrome, width, height);
  await inspectViewport(chrome, 390, 844, { reducedMotion: 'reduce', suffix: '-reduced-motion', skipMenu: true });
  await inspectViewport(chrome, 390, 844, { forcedColors: 'active', suffix: '-forced-colors', skipMenu: true });
  await inspectViewport(chrome, 390, 844, { isMobile: true, hasTouch: true, suffix: '-android-chrome' });
  await inspectDelayedMapsKey(chrome);
  await chrome.close();

  const safari = await webkit.launch({ headless: true });
  await inspectViewport(safari, 390, 844, { isMobile: true, hasTouch: true, suffix: '-ios-safari' });
  await safari.close();

  if (failures.length) {
    console.error(`UI REGRESSION FAILED (${failures.length})`);
    failures.forEach(failure => console.error(`- ${failure}`));
    process.exit(1);
  }
  console.log(`UI REGRESSION PASSED (${viewports.length + 4} browser/viewport runs + delayed Maps-key race)`);
  console.log(`Artifacts: ${outputDir}`);
})().catch(error => {
  console.error(error);
  process.exit(1);
});
